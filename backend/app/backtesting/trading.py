"""Close-clock schedules and sizing. This module never reads future execution prices."""

from datetime import date, timedelta
from decimal import ROUND_DOWN, Decimal

from app.market_data.calendar import sessions
from app.portfolio.ledger import Ledger
from app.schemas.domain import OrderRecord, ProfileConfig, StrategyConfig

D = Decimal


def scheduled(schedule: str, day: date) -> bool:
    if schedule in {"daily", "once"}:
        return True
    start = day.replace(day=1) if schedule == "monthly" else day - timedelta(days=day.weekday())
    return sessions(start, day)[0] == day


def planned_order(
    config: StrategyConfig,
    profile: ProfileConfig,
    ledger: Ledger,
    orders: list[OrderRecord],
    symbol: str,
    day: date,
    index: int,
    entry: bool | None,
    exit: bool | None,
    prices: dict[str, Decimal],
    fx: Decimal,
    equity: Decimal,
) -> tuple[str, Decimal, str] | None:
    policy = config.trading
    assert policy is not None
    position = ledger.positions.get(symbol)
    if any(o.symbol == symbol and o.status == "pending" for o in orders):
        return None
    age = (
        position.last_added_session
        if position and position.last_added_session is not None
        else position.opened_session
        if position
        else index
    )
    exit_locked = position is not None and index - age < profile.min_holding_sessions
    quantum = D("0.000001") if profile.fractional_shares else D(1)
    if position and exit is True and scheduled(policy.exit_schedule, day):
        if exit_locked:
            return None
        quantity = (
            position.quantity
            if policy.exit_fraction == 1
            else (position.quantity * policy.exit_fraction).quantize(quantum, rounding=ROUND_DOWN)
        )
        return ("sell", quantity, "scheduled partial/full exit") if quantity > 0 else None
    if entry is not True or not scheduled(policy.entry_schedule, day):
        return None
    if policy.entry_schedule == "once" and any(
        o.symbol == symbol and o.side == "buy" and o.status == "filled" for o in orders
    ):
        return None
    held = position.quantity * prices[symbol] * fx if position else D(0)
    exposure = sum((p.quantity * prices[s] * fx for s, p in ledger.positions.items()), D(0))
    if config.sizing.mode == "target_allocation":
        gap = (
            equity * min(config.sizing.value, config.risk.max_allocation, profile.max_exposure)
            - held
        )
        if gap < 0 and position:
            if exit_locked:
                return None
            quantity = (
                position.quantity
                if config.sizing.value == 0
                else min(
                    position.quantity,
                    (-gap / (prices[symbol] * fx)).quantize(quantum, rounding=ROUND_DOWN),
                )
            )
            return ("sell", quantity, "target allocation trim") if quantity > 0 else None
        budget = gap
    elif config.sizing.mode == "cash_percent":
        budget = ledger.cash * config.sizing.value
    elif config.sizing.mode == "equity_percent":
        budget = equity * config.sizing.value
    else:
        budget = config.sizing.value
    if position and not policy.allow_additions:
        return None
    budget = min(
        budget,
        ledger.cash,
        max(D(0), equity * config.risk.max_allocation - held),
        max(D(0), equity * profile.max_exposure - exposure),
    )
    quantity = ledger.quantity(budget, prices[symbol], fx)
    return ("buy", quantity, "scheduled entry/rebalance") if quantity > 0 else None
