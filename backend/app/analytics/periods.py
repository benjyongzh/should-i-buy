"""Read-only analysis of persisted continuous equity; never reruns or mutates a simulation."""

from datetime import date, datetime
from decimal import Decimal, localcontext
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


def period_report(
    result: dict,
    profile: dict,
    frequency: str = "year",
    start: date | None = None,
    end: date | None = None,
) -> list[dict]:
    if frequency not in {"year", "quarter", "month"}:
        raise ValueError("Unsupported period frequency")
    if start and end and start > end:
        raise ValueError("Period start must not follow end")
    previous = Decimal(profile["starting_capital"])
    previous_performance = previous
    previous_benchmark = previous
    benchmark = {
        r["date"]: Decimal(r.get("performance_equity", r["equity"]))
        for r in result.get("benchmark", {}).get("equity", [])
    }
    groups = {}
    with localcontext() as context:
        context.prec = 34
        for row in result["equity"]:
            day = date.fromisoformat(row["date"])
            equity = Decimal(row["equity"])
            performance = Decimal(row.get("performance_equity", row["equity"]))
            reference = benchmark.get(row["date"])
            if (start is None or day >= start) and (end is None or day <= end):
                label = (
                    str(day.year)
                    if frequency == "year"
                    else f"{day.year}-Q{(day.month - 1) // 3 + 1}"
                    if frequency == "quarter"
                    else day.strftime("%Y-%m")
                )
                if label not in groups:
                    groups[label] = {
                        "period": label,
                        "start": str(day),
                        "end": str(day),
                        "sessions": 0,
                        "starting_equity": str(previous),
                        "ending_equity": str(equity),
                        "peak": previous_performance,
                        "performance_start": previous_performance,
                        "performance_end": performance,
                        "contributions": Decimal(0),
                        "max_drawdown": Decimal(0),
                        "benchmark_start": previous_benchmark,
                        "benchmark_end": reference,
                        "executed_orders": 0,
                        "commissions": Decimal(0),
                        "fx_costs": Decimal(0),
                    }
                group = groups[label]
                group["end"] = str(day)
                group["sessions"] += 1
                group["ending_equity"] = str(equity)
                group["benchmark_end"] = reference
                group["performance_end"] = performance
                group["contributions"] += Decimal(row.get("external_flow", "0"))
                group["peak"] = max(group["peak"], performance)
                if group["peak"] > 0:
                    group["max_drawdown"] = min(
                        group["max_drawdown"], performance / group["peak"] - 1
                    )
            previous = equity
            previous_performance = performance
            if reference is not None:
                previous_benchmark = reference
        # UTC evening decision times can fall on the next date; use the market-local date.
        for event in result.get("ledger", []):
            if event.get("kind") not in {"buy", "sell"}:
                continue
            day = datetime.fromisoformat(event["timestamp"]).astimezone(NY).date()
            for group in groups.values():
                if group["start"] <= str(day) <= group["end"]:
                    group["executed_orders"] += 1
                    group["commissions"] += Decimal(event["fees"])
                    group["fx_costs"] += Decimal(event["fx_cost"])
        output = []
        for group in groups.values():
            initial = Decimal(group["starting_equity"])
            final = Decimal(group["ending_equity"])
            contributions = group.pop("contributions")
            pstart, pend = group.pop("performance_start"), group.pop("performance_end")
            group["pnl"] = str(final - initial - contributions)
            group["return"] = str(pend / pstart - 1) if pstart else None
            if profile.get("monthly_contribution") and Decimal(profile["monthly_contribution"]):
                group["contributions"] = str(contributions)
            bstart, bend = group.pop("benchmark_start"), group.pop("benchmark_end")
            group["benchmark_return"] = (
                str(bend / bstart - 1) if bend is not None and bstart else None
            )
            group.pop("peak")
            for key in ("max_drawdown", "commissions", "fx_costs"):
                group[key] = str(group[key])
            output.append(group)
        return output
