from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.domain import Compare, Group, Indicator, Negate, StrategyConfig, default_strategy
from app.strategies.interpreter import condition, numeric


@pytest.mark.parametrize(
    "name,expected",
    [
        ("sma", 2),
        ("ema", 2),
        ("rsi", 100),
        ("momentum", 200),
        ("avg_volume", 10000),
        ("rolling_high", 5),
        ("rolling_low", -1),
    ],
)
def test_all_indicators(data, name, expected):
    bars = [
        b.model_copy(
            update={"close": Decimal(i + 1), "high": Decimal(i + 3), "low": Decimal(i - 1)}
        )
        for i, b in enumerate(data.bars[:3])
    ]
    node = Indicator(type="indicator", name=name, period=2 if name in ("rsi", "momentum") else 3)
    assert numeric(node, bars) == Decimal(expected)


@pytest.mark.parametrize(
    "op,value", [("gt", True), ("lt", False), ("gte", True), ("lte", False), ("eq", False)]
)
def test_all_comparisons(data, op, value):
    node = Compare(
        type="compare",
        op=op,
        left={"type": "constant", "value": 2},
        right={"type": "constant", "value": 1},
    )
    assert condition(node, data.bars) is value


@pytest.mark.parametrize("op,values", [("crosses_above", [1, 3]), ("crosses_below", [3, 1])])
def test_crossovers_are_events(data, op, values):
    bars = [
        b.model_copy(update={"close": Decimal(value)})
        for b, value in zip(data.bars, values, strict=False)
    ]
    rule = Compare(
        type="compare", op=op, left={"type": "price"}, right={"type": "constant", "value": 2}
    )
    assert condition(rule, bars) is True
    assert condition(rule, bars + [bars[-1]]) is False


def test_logical_warmup_and_multiply(data):
    rule = Compare(
        type="compare",
        op="gt",
        left={"type": "indicator", "name": "sma", "period": 20},
        right={"type": "constant", "value": 1},
    )
    assert condition(rule, data.bars[:5]) is None
    assert condition(Negate(type="not", condition=rule), data.bars[:5]) is None
    assert (
        condition(
            Group(type="all", conditions=[rule, {"type": "always", "value": False}]), data.bars[:5]
        )
        is False
    )
    assert (
        condition(
            Group(type="any", conditions=[rule, {"type": "always", "value": True}]), data.bars[:5]
        )
        is True
    )
    from pydantic import TypeAdapter

    from app.schemas.domain import Numeric

    assert (
        numeric(
            TypeAdapter(Numeric).validate_python(
                {
                    "type": "multiply",
                    "left": {"type": "constant", "value": 2},
                    "right": {"type": "constant", "value": 3},
                }
            ),
            [],
        )
        == 6
    )


def test_strict_schema_and_bounds():
    config = default_strategy().model_dump(mode="json")
    config["entry"] = {
        "type": "compare",
        "op": "eval",
        "left": {"type": "constant", "value": 1},
        "right": {"type": "constant", "value": 0},
    }
    with pytest.raises(ValidationError):
        StrategyConfig.model_validate(config)
    config["entry"] = {"type": "always", "value": True}
    for _ in range(25):
        config["entry"] = {"type": "not", "condition": config["entry"]}
    with pytest.raises(ValidationError, match="depth"):
        StrategyConfig.model_validate(config)
