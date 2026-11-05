"""Cash-flow neutral performance and investor return for positive external deposits."""

import math
from datetime import datetime
from decimal import Decimal

from app.market_data.calendar import session_times

D = Decimal


def normalize(curve: list[dict], capital: Decimal) -> list[Decimal]:
    previous = capital
    performance = capital
    values = [capital]
    for row in curve:
        current = D(row["equity"])
        flow = D(row["external_flow"])
        if min(previous, current, flow) < 0:
            raise ValueError("negative equity or contribution")
        if flow:
            before, after = D(row["equity_before_flow"]), D(row["equity_after_flow"])
            if before < 0 or after != before + flow:
                raise ValueError("invalid opening flow valuation")
            if previous == 0 and before != 0:
                raise ValueError("unexplained recovery before contribution")
            factor = (before / previous if previous else D(1)) * current / after
        else:
            if previous == 0 and current != 0:
                raise ValueError("unexplained recovery without contribution")
            factor = current / previous if previous else D(1)
        performance *= factor
        row["performance_equity"] = str(performance)
        values.append(performance)
        previous = current
    return values


def investor_return(curve: list[dict], events: list[dict], capital: Decimal) -> float | None:
    """Annualized actual/365 MWR. Positive deposits imply a unique root; no withdrawals.

    Use a bounded log-rate search and log-sum-exp to avoid exponent overflow.
    Horizons shorter than a year are deliberately not annualized.
    """
    end = datetime.fromisoformat(curve[-1]["timestamp"])
    start = session_times(datetime.fromisoformat(curve[0]["date"]).date())[0]
    if (end - start).total_seconds() < 365 * 86400:
        return None
    final = float(curve[-1]["equity"])
    if final == 0:
        return -1.0
    flows = [(start, capital)] + [
        (datetime.fromisoformat(e["timestamp"]), D(e["cash_delta"]))
        for e in events
        if e["kind"] == "contribution"
    ]
    terms = [
        (math.log(float(amount)), (end - clock).total_seconds() / (365 * 86400))
        for clock, amount in flows
    ]

    def value(rate):
        exponents = [amount + rate * years for amount, years in terms]
        peak = max(exponents)
        return peak + math.log(sum(math.exp(x - peak) for x in exponents)) - math.log(final)

    low, high = -64.0, 64.0
    if value(low) > 0 or value(high) < 0:
        return None
    for _ in range(100):
        mid = (low + high) / 2
        if value(mid) > 0:
            high = mid
        else:
            low = mid
    return math.expm1((low + high) / 2)
