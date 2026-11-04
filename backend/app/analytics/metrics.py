import math
import statistics
from decimal import Decimal

from app.portfolio.ledger import Ledger
from app.schemas.domain import ProfileConfig


def metrics(curve: list[dict], ledger: Ledger, profile: ProfileConfig) -> dict:
    start = float(profile.starting_capital)
    values = [start] + [float(row["equity"]) for row in curve]
    decimal_values = [profile.starting_capital] + [Decimal(row["equity"]) for row in curve]
    returns = []
    for previous, current in zip(decimal_values, decimal_values[1:], strict=False):
        if previous < 0 or current < 0:
            raise ValueError("negative equity is invalid for an unlevered portfolio")
        if previous == 0:
            if current != 0:
                raise ValueError("equity cannot recover from zero without a modeled capital flow")
            returns.append(0.0)  # zero equity is absorbing: no capital injections in the MVP
        else:
            returns.append(float(current / previous - 1))
    peak = start
    max_dd = 0.0
    duration = longest = 0
    for row, value in zip(curve, values[1:], strict=True):
        peak = max(peak, value)
        dd = value / peak - 1
        row["drawdown"] = dd
        duration = duration + 1 if dd < -1e-12 else 0
        longest = max(longest, duration)
        max_dd = min(max_dd, dd)
    vol = statistics.stdev(returns) if len(returns) > 1 else 0
    net = values[-1] / start - 1
    wins = [Decimal(t["realized_pnl"]) for t in ledger.trades if Decimal(t["realized_pnl"]) > 0]
    losses = [Decimal(t["realized_pnl"]) for t in ledger.trades if Decimal(t["realized_pnl"]) < 0]
    total_costs = ledger.fees + ledger.fx_costs + ledger.slippage_costs
    return {
        "starting_equity": str(profile.starting_capital),
        "ending_equity": curve[-1]["equity"],
        "absolute_pnl": str(Decimal(curve[-1]["equity"]) - profile.starting_capital),
        "total_return": net,
        "net_return": net,
        "cost_addback_return": (values[-1] + float(total_costs)) / start - 1,
        "annualized_return": (1 + net) ** (252 / len(returns)) - 1
        if len(returns) >= 252 and net >= -1
        else None,
        "daily_returns": returns,
        "max_drawdown": max_dd,
        "drawdown_duration_sessions": longest,
        "annualized_volatility": vol * math.sqrt(252),
        "sharpe_ratio": (statistics.mean(returns) - float(profile.risk_free_rate) / 252)
        / vol
        * math.sqrt(252)
        if vol > 1e-12
        else None,
        "completed_trades": len(ledger.trades),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": len(wins) / len(ledger.trades) if ledger.trades else None,
        "average_win": str(sum(wins) / len(wins)) if wins else None,
        "average_loss": str(sum(losses) / len(losses)) if losses else None,
        "profit_factor": float(sum(wins) / abs(sum(losses))) if losses else None,
        "average_holding_sessions": statistics.mean(t["holding_sessions"] for t in ledger.trades)
        if ledger.trades
        else None,
        "executed_orders": sum(e["kind"] in ("buy", "sell") for e in ledger.events),
        "total_commissions": str(ledger.fees),
        "total_slippage_and_spread": str(ledger.slippage_costs),
        "total_fx_costs": str(ledger.fx_costs),
        "total_costs": str(total_costs),
        "turnover": float(ledger.turnover / profile.starting_capital),
        "market_exposure": statistics.mean(float(r["exposure"]) for r in curve),
    }
