from collections.abc import Sequence
from decimal import Decimal

from app.schemas.domain import (
    Always,
    Bar,
    Compare,
    Condition,
    Constant,
    Group,
    Indicator,
    Multiply,
    Negate,
    Numeric,
    Price,
)

D = Decimal


def numeric(node: Numeric, bars: Sequence[Bar], offset: int = 0) -> Decimal | None:
    history = bars[: len(bars) - offset] if offset else bars
    if isinstance(node, Constant):
        return node.value
    if isinstance(node, Multiply):
        a, b = numeric(node.left, bars, offset), numeric(node.right, bars, offset)
        return a * b if a is not None and b is not None else None
    if not history:
        return None
    if isinstance(node, Price):
        return getattr(history[-1], node.field)
    if not isinstance(node, Indicator):
        raise ValueError("unsupported numeric expression")
    p = node.period
    field = {"avg_volume": "volume", "rolling_high": "high", "rolling_low": "low"}.get(
        node.name, node.field
    )
    values = [getattr(b, field) for b in history]
    required = p + 1 if node.name in ("rsi", "momentum") else p
    if len(values) < required:
        return None
    if node.name in ("sma", "avg_volume"):
        return sum(values[-p:], D(0)) / p
    if node.name == "rolling_high":
        return max(values[-p:])
    if node.name == "rolling_low":
        return min(values[-p:])
    if node.name == "momentum":
        if values[-p - 1] == 0:
            return None
        return (values[-1] / values[-p - 1] - 1) * 100
    if node.name == "ema":
        value = sum(values[:p], D(0)) / p
        alpha = D(2) / (p + 1)
        for current in values[p:]:
            value = alpha * current + (1 - alpha) * value
        return value
    if node.name == "rsi":
        changes = [b - a for a, b in zip(values, values[1:], strict=False)]
        gain = sum((max(c, D(0)) for c in changes[:p]), D(0)) / p
        loss = sum((max(-c, D(0)) for c in changes[:p]), D(0)) / p
        for change in changes[p:]:
            gain = (gain * (p - 1) + max(change, D(0))) / p
            loss = (loss * (p - 1) + max(-change, D(0))) / p
        if gain == loss == 0:
            return D(50)
        return D(100) if loss == 0 else 100 - 100 / (1 + gain / loss)
    raise ValueError("unsupported indicator")


def condition(node: Condition, bars: Sequence[Bar]) -> bool | None:
    """Three-valued logic: NOT of an unwarmed indicator stays unknown, not true."""
    if isinstance(node, Always):
        return node.value
    if isinstance(node, Negate):
        value = condition(node.condition, bars)
        return None if value is None else not value
    if isinstance(node, Group):
        values = [condition(c, bars) for c in node.conditions]
        if node.type == "all":
            return False if False in values else (None if None in values else True)
        return True if True in values else (None if None in values else False)
    if not isinstance(node, Compare):
        raise ValueError("unsupported condition")
    a, b = numeric(node.left, bars), numeric(node.right, bars)
    if a is None or b is None:
        return None
    if node.op in ("crosses_above", "crosses_below"):
        pa, pb = numeric(node.left, bars, 1), numeric(node.right, bars, 1)
        if pa is None or pb is None:
            return None
        return (a > b and pa <= pb) if node.op == "crosses_above" else (a < b and pa >= pb)
    return {"gt": a > b, "lt": a < b, "gte": a >= b, "lte": a <= b, "eq": a == b}[node.op]
