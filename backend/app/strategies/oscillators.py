"""Decimal oscillators with explicit SMA seeds, completed-bar inputs and no I/O."""

from collections.abc import Sequence
from decimal import Decimal

from app.schemas.domain import MACD, Bar, Stochastic

D = Decimal


def ema_series(values: Sequence[Decimal], period: int) -> list[Decimal]:
    if len(values) < period:
        return []
    output = [sum(values[:period], D(0)) / period]
    alpha = D(2) / (period + 1)
    for value in values[period:]:
        # Delta form avoids cancellation/drift on flat or exactly linear inputs.
        output.append(output[-1] + alpha * (value - output[-1]))
    return output


def macd(node: MACD, bars: Sequence[Bar]) -> Decimal | None:
    if len(bars) < node.slow_period:
        return None
    values = [getattr(bar, node.field) for bar in bars]
    fast = ema_series(values, node.fast_period)[node.slow_period - node.fast_period :]
    slow = ema_series(values, node.slow_period)
    line = [a - b for a, b in zip(fast, slow, strict=True)]
    if node.component == "line":
        return line[-1]
    signal = ema_series(line, node.signal_period)
    if not signal:
        return None
    return signal[-1] if node.component == "signal" else line[-1] - signal[-1]


def stochastic(node: Stochastic, bars: Sequence[Bar]) -> Decimal | None:
    required = node.period + node.smooth_k - 1
    if node.component == "d":
        required += node.smooth_d - 1
    if len(bars) < required:
        return None
    # Only the trailing windows needed for the requested smoothed value are used.
    raw = []
    for end in range(len(bars) - required + node.period, len(bars) + 1):
        window = bars[end - node.period : end]
        low = min(bar.low for bar in window)
        high = max(bar.high for bar in window)
        raw.append(D(50) if high == low else 100 * (window[-1].close - low) / (high - low))
    k = [
        sum(raw[i - node.smooth_k : i], D(0)) / node.smooth_k
        for i in range(node.smooth_k, len(raw) + 1)
    ]
    return k[-1] if node.component == "k" else sum(k[-node.smooth_d :], D(0)) / node.smooth_d
