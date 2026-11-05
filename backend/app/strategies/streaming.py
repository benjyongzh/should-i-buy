"""Causal incremental indicator cache for opt-in event-clock simulations.

Values are indexed by completed-history prefix, so a cached later value cannot
answer an earlier-clock request. A split/history generation gets its own key.
"""

from decimal import Decimal

from app.schemas.domain import MACD, Indicator, Price, Stochastic

D = Decimal


class IndicatorCache:
    def __init__(self):
        self._entries = {}

    def value(self, node, bars, key):
        if not bars:
            return None
        identity = (key, node.model_dump_json())
        values, state = self._entries.setdefault(identity, ([], {}))
        for i in range(len(values), len(bars)):
            values.append(self._append(node, bars, i, state))
        return values[len(bars) - 1]

    @staticmethod
    def _ema(state, name, period, value, delta=False):
        total, count, ema = state.get(name, (D(0), 0, None))
        count += 1
        if count <= period:
            total += value
            ema = total / period if count == period else None
        else:
            alpha = D(2) / (period + 1)
            ema = ema + alpha * (value - ema) if delta else alpha * value + (1 - alpha) * ema
        state[name] = (total, count, ema)
        return ema

    def _append(self, node, bars, i, state):
        bar = bars[i]
        if isinstance(node, Price):
            return getattr(bar, node.field)
        if isinstance(node, MACD):
            value = getattr(bar, node.field)
            fast = self._ema(state, "fast", node.fast_period, value, True)
            slow = self._ema(state, "slow", node.slow_period, value, True)
            if slow is None:
                return None
            line = fast - slow
            signal = self._ema(state, "signal", node.signal_period, line, True)
            return (
                line
                if node.component == "line"
                else signal
                if node.component == "signal"
                else line - signal
                if signal is not None
                else None
            )
        if isinstance(node, Stochastic):
            if i + 1 < node.period:
                return None
            low = min(b.low for b in bars[i - node.period + 1 : i + 1])
            high = max(b.high for b in bars[i - node.period + 1 : i + 1])
            raw = D(50) if high == low else 100 * (bar.close - low) / (high - low)
            raws = state.setdefault("raws", [])
            raws.append(raw)
            if len(raws) < node.smooth_k:
                return None
            k = sum(raws[-node.smooth_k :], D(0)) / node.smooth_k
            ks = state.setdefault("ks", [])
            ks.append(k)
            return (
                k
                if node.component == "k"
                else sum(ks[-node.smooth_d :], D(0)) / node.smooth_d
                if len(ks) >= node.smooth_d
                else None
            )
        if not isinstance(node, Indicator):
            raise ValueError("unsupported streamed market operand")
        p = node.period
        field = {"avg_volume": "volume", "rolling_high": "high", "rolling_low": "low"}.get(
            node.name, node.field
        )
        value = getattr(bar, field)
        if node.name == "ema":
            return self._ema(state, "ema", p, value)
        if node.name == "rsi":
            if i == 0:
                return None
            change = value - getattr(bars[i - 1], field)
            gain, loss = state.get("rsi", (D(0), D(0)))
            if i <= p:
                gain += max(change, D(0))
                loss += max(-change, D(0))
                if i == p:
                    gain /= p
                    loss /= p
            else:
                gain = (gain * (p - 1) + max(change, D(0))) / p
                loss = (loss * (p - 1) + max(-change, D(0))) / p
            state["rsi"] = gain, loss
            if i < p:
                return None
            return (
                D(50)
                if gain == loss == 0
                else D(100)
                if loss == 0
                else 100 - 100 / (1 + gain / loss)
            )
        if node.name == "momentum":
            if i < p or getattr(bars[i - p], field) == 0:
                return None
            return (value / getattr(bars[i - p], field) - 1) * 100
        if i + 1 < p:
            return None
        window = [getattr(b, field) for b in bars[i - p + 1 : i + 1]]
        if node.name in {"sma", "avg_volume"}:
            return sum(window, D(0)) / p
        return max(window) if node.name == "rolling_high" else min(window)
