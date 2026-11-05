"""Read-only reporting baselines; persisted simulation results are never modified."""

from datetime import datetime
from decimal import Decimal, localcontext


def _cash_curve(rows, initial, flows):
    curve = []
    deposited = Decimal(0)
    cursor = 0
    previous = None
    for row in rows:
        clock = datetime.fromisoformat(row["timestamp"])
        if clock.tzinfo is None or (previous is not None and clock < previous):
            raise ValueError("cash baseline requires chronological timezone-aware valuation clocks")
        previous = clock
        today = Decimal(0)
        while cursor < len(flows) and flows[cursor][0] <= clock:
            today += flows[cursor][1]
            cursor += 1
        deposited += today
        curve.append(
            {
                "date": row["date"],
                "timestamp": row["timestamp"],
                "equity": str(initial + deposited),
                "cash": str(initial + deposited),
                "performance_equity": str(initial),
                "drawdown": 0,
                "external_flow": str(today),
                "cumulative_contributions": str(deposited),
                "exposure": "0",
                "realized_pnl": "0",
                "unrealized_pnl": "0",
            }
        )
    return curve, deposited


def cash_benchmark(result: dict, profile: dict) -> dict:
    """Account-currency cash with the run's actual deposits, zero interest/costs.

    Replay recorded capital flows instead of inferring a schedule from today's
    profile or a calendar. This is an explicitly modeled reporting baseline.
    """
    initial = Decimal(profile["starting_capital"])
    flows = sorted(
        (
            (datetime.fromisoformat(e["timestamp"]), Decimal(e["cash_delta"]))
            for e in result.get("ledger", [])
            if e["kind"] == "contribution"
        ),
        key=lambda flow: flow[0],
    )
    if not initial.is_finite() or initial <= 0:
        raise ValueError("cash baseline requires positive initial capital")
    if any(
        clock.tzinfo is None or not amount.is_finite() or amount <= 0 for clock, amount in flows
    ):
        raise ValueError("cash baseline requires timestamped positive deposits")
    with localcontext() as context:
        context.prec = 34
        curve, deposited = _cash_curve(result["equity"], initial, flows)
        intraday, _ = _cash_curve(result.get("intraday_equity", []), initial, flows)
        return {
            "name": "Cash only · zero interest",
            "currency": profile["account_currency"],
            "assumptions": "Modeled account-currency cash; zero interest, trading costs and FX conversions. Uses only this run's recorded external deposits, not trading or dividend proceeds.",
            "equity": curve,
            **({"intraday_equity": intraday} if intraday else {}),
            "metrics": {
                "starting_equity": str(initial),
                "ending_equity": str(initial + deposited),
                "total_contributions": str(deposited),
                "total_contributed_capital": str(initial + deposited),
                "absolute_pnl": "0",
                "total_return": 0,
                "net_return": 0,
                "max_drawdown": 0,
                "sharpe_ratio": None,
                "executed_orders": 0,
                "total_commissions": "0",
            },
        }
