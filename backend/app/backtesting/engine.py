from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal, localcontext

from app.analytics.metrics import metrics
from app.market_data.calendar import decision_timestamp, session_times, sessions
from app.market_data.validation import validate_coverage
from app.market_data.view import DataView, fx_at
from app.portfolio.ledger import Ledger
from app.schemas.domain import (
    DatasetInput,
    OrderRecord,
    ProfileConfig,
    StrategyConfig,
    default_strategy,
)
from app.strategies.interpreter import condition

ENGINE_VERSION = "1.1.0"
D = Decimal


class Cancelled(Exception):
    pass


def simulate(
    config: StrategyConfig,
    profile: ProfileConfig,
    data: DatasetInput,
    checkpoint: Callable[[int], None] | None = None,
    benchmark: bool = True,
    gross: bool = True,
) -> dict:
    with localcontext() as context:
        context.prec = 34
        return _simulate(config, profile, data, checkpoint, benchmark, gross)


def _simulate(
    config: StrategyConfig,
    profile: ProfileConfig,
    data: DatasetInput,
    checkpoint: Callable[[int], None] | None,
    benchmark: bool,
    gross: bool,
) -> dict:
    validate_coverage(data, profile)
    ledger = Ledger(profile)
    bars = sorted(data.bars, key=lambda b: (b.available_at, b.symbol))
    by_session = {(b.symbol, b.session_date): b for b in bars}
    days = sessions(profile.start_date, profile.end_date)
    orders: list[OrderRecord] = []
    signals = []
    curve = []
    history = []
    cursor = 0
    prices = {}
    for index, day in enumerate(days):
        if checkpoint:
            checkpoint(int(index / len(days) * 95))
        opening, closing = session_times(day)
        decision_time = decision_timestamp(day, data.decision_time)
        rate = (
            fx_at(data.fx, opening, profile.max_fx_age_days)
            if profile.account_currency == "SGD"
            else D(1)
        )
        executed_today = 0
        for action in sorted(
            data.actions, key=lambda a: (a.session_date, 0 if a.kind == "split" else 1, a.symbol)
        ):
            if action.session_date != day or action.available_at > opening:
                continue
            if action.kind == "split":
                ledger.split(action.symbol, action.value, opening)
                if action.symbol in prices:
                    prices[action.symbol] /= action.value
                for order in orders:
                    if (
                        order.symbol == action.symbol
                        and order.status == "pending"
                        and order.quantity
                    ):
                        order.quantity *= action.value
            else:
                ledger.dividend(action.symbol, action.value, action.payment_date, opening)
        ledger.settle_dividends(day, rate, opening)

        def fill(
            order: OrderRecord,
            raw_price: Decimal,
            timestamp: datetime,
            fx: Decimal,
            day: date = day,
            index: int = index,
        ) -> None:
            nonlocal executed_today
            try:
                if executed_today >= profile.max_orders_per_day:
                    raise ValueError("daily order frequency limit")
                if by_session[(order.symbol, day)].volume == 0:
                    raise ValueError("no reported market volume")
                if order.side == "buy":
                    if len(ledger.positions) >= config.risk.max_positions:
                        raise ValueError("strategy position limit")
                    # Use execution-time opens only for risk/affordability, never to generate signals.
                    open_prices = {s: by_session[(s, day)].open for s in ledger.positions}
                    equity = ledger.equity(open_prices, fx)
                    notional = (
                        order.quantity
                        * raw_price
                        * (1 + profile.slippage + profile.spread / 2)
                        * fx
                    )
                    existing = sum(
                        (p.quantity * open_prices[s] * fx for s, p in ledger.positions.items()),
                        D(0),
                    )
                    if notional > equity * config.risk.max_allocation:
                        raise ValueError("maximum asset allocation at execution")
                    if existing + notional > equity * profile.max_exposure:
                        raise ValueError("maximum portfolio exposure at execution")
                event = ledger.execute(
                    order.symbol, order.side, order.quantity, raw_price, fx, timestamp, index
                )
                order.status = "filled"
                order.execution_price = D(event["price_usd"])
                order.fees = D(event["fees"])
                order.executed_at = timestamp
                executed_today += 1
            except ValueError as exc:
                order.status = "rejected"
                order.rejection_reason = str(exc)

        for order in orders:
            if order.status == "pending" and order.eligible_after < opening:
                fill(order, by_session[(order.symbol, day)].open, opening, rate)

        # Already active protective exits may use this candle's range. Stop wins ambiguous bars.
        for symbol, position in list(ledger.positions.items()):
            bar = by_session[(symbol, day)]
            stop = (
                position.entry_price * (1 - config.risk.stop_loss)
                if config.risk.stop_loss is not None
                else None
            )
            take = (
                position.entry_price * (1 + config.risk.take_profit)
                if config.risk.take_profit is not None
                else None
            )
            raw = kind = None
            if stop is not None and bar.low <= stop:
                raw, kind = min(bar.open, stop), "stop_loss"
            elif take is not None and bar.high >= take:
                raw, kind = take, "take_profit"  # no favorable gap improvement
            if raw is not None:
                # Unknown intraday path is booked at close, with an available close FX quote.
                at_open = kind == "stop_loss" and bar.open <= stop
                timestamp = opening if at_open else closing
                fx = (
                    fx_at(data.fx, timestamp, profile.max_fx_age_days)
                    if profile.account_currency == "SGD"
                    else D(1)
                )
                order = OrderRecord(
                    id=len(orders) + 1,
                    symbol=symbol,
                    side="sell",
                    type=kind,
                    submitted_at=position.opened_at,
                    eligible_after=position.opened_at,
                    quantity=position.quantity,
                    reason=f"protective {kind}; stop-first daily-bar policy",
                )
                orders.append(order)
                fill(order, raw, timestamp, fx)

        while cursor < len(bars) and bars[cursor].available_at <= decision_time:
            history.append(bars[cursor])
            cursor += 1
        # Adjust historical indicator inputs only for splits effective AND known by this clock.
        adjusted = []
        for bar in history:
            ratio = D(1)
            for action in data.actions:
                if (
                    action.kind == "split"
                    and action.symbol == bar.symbol
                    and bar.session_date < action.session_date <= day
                    and action.available_at <= decision_time
                ):
                    ratio *= action.value
            adjusted.append(
                bar.model_copy(
                    update={
                        "open": bar.open / ratio,
                        "high": bar.high / ratio,
                        "low": bar.low / ratio,
                        "close": bar.close / ratio,
                        "volume": bar.volume * ratio,
                    }
                )
                if ratio != 1
                else bar
            )
        view = DataView(adjusted, decision_time)
        for symbol in sorted(set(profile.symbols + list(ledger.positions))):
            permissible = view.history(symbol)
            if permissible:
                prices[symbol] = permissible[-1].close
        close_fx = (
            fx_at(data.fx, decision_time, profile.max_fx_age_days)
            if profile.account_currency == "SGD"
            else D(1)
        )
        if any(s not in prices for s in ledger.positions):
            raise ValueError("position lacks a permissible valuation price")
        equity = ledger.equity(prices, close_fx)
        for symbol in sorted(profile.symbols):
            permissible = view.history(symbol)
            # Do not trade a stale/delayed candle twice, or before it is available.
            if not permissible or permissible[-1].session_date != day:
                continue
            position = ledger.positions.get(symbol)
            rule = config.exit if position else config.entry
            active = condition(rule, permissible)
            signals.append(
                {
                    "timestamp": decision_time.isoformat(),
                    "symbol": symbol,
                    "action": ("sell" if position else "buy") if active is True else "hold",
                    "rule": rule.model_dump(mode="json"),
                    "condition_result": active,
                }
            )
            if active is not True or any(
                o.symbol == symbol and o.status == "pending" for o in orders
            ):
                continue
            if position and index - position.opened_session < profile.min_holding_sessions:
                continue
            if position:
                quantity = position.quantity
            else:
                exposure = sum(
                    (p.quantity * prices[s] * close_fx for s, p in ledger.positions.items()), D(0)
                )
                budget = (
                    equity * config.sizing.value
                    if config.sizing.mode == "equity_percent"
                    else config.sizing.value
                )
                budget = min(
                    budget,
                    ledger.cash,
                    equity * config.risk.max_allocation,
                    max(D(0), equity * profile.max_exposure - exposure),
                )
                quantity = ledger.quantity(budget, prices[symbol], close_fx)
            orders.append(
                OrderRecord(
                    id=len(orders) + 1,
                    symbol=symbol,
                    side="sell" if position else "buy",
                    submitted_at=decision_time,
                    eligible_after=decision_time,
                    quantity=quantity,
                    reason="declarative exit" if position else "declarative entry",
                )
            )
        cost_basis = sum((p.cost_basis for p in ledger.positions.values()), D(0))
        curve.append(
            {
                "date": str(day),
                "timestamp": decision_time.isoformat(),
                "equity": str(equity),
                "cash": str(ledger.cash),
                "exposure": str(
                    sum(
                        (p.quantity * prices[s] * close_fx for s, p in ledger.positions.items()),
                        D(0),
                    )
                    / equity
                    if equity
                    else 0
                ),
                "realized_pnl": str(ledger.realized_pnl),
                "unrealized_pnl": str(equity - ledger.cash - cost_basis),
            }
        )
    stats = metrics(curve, ledger, profile)
    warnings = (
        ["Synthetic demonstration data — not historical investment performance."]
        if data.synthetic
        else []
    )
    if not data.dividends_complete:
        warnings.append(
            "Price-only research: complete dividends are unavailable; do not interpret as total returns."
        )
    warnings.extend(
        [
            "Manually selected universe may have survivorship bias.",
            f"Research designation: {profile.research_label}; repeated optimization is not unbiased out-of-sample evidence.",
            data.availability_policy,
        ]
    )
    result = {
        "metrics": stats,
        "equity": curve,
        "orders": [o.model_dump(mode="json") for o in orders],
        "trades": ledger.trades,
        "ledger": ledger.events,
        "signals": signals,
        "positions": {
            s: {
                "quantity": str(p.quantity),
                "cost_basis": str(p.cost_basis),
                "entry_price": str(p.entry_price),
            }
            for s, p in ledger.positions.items()
        },
        "warnings": warnings,
        "receivables": [
            {
                "symbol": r["symbol"],
                "amount_usd": str(r["amount_usd"]),
                "payment_date": str(r["payment_date"]),
            }
            for r in ledger.receivables
        ],
    }
    if benchmark:
        bench = default_strategy()
        bench.sizing.value = D(1)
        bp = profile.model_copy(update={"symbols": [profile.benchmark]})
        reference = simulate(bench, bp, data, checkpoint, benchmark=False, gross=False)
        result["benchmark"] = {"metrics": reference["metrics"], "equity": reference["equity"]}
        stats["benchmark_total_return"] = reference["metrics"]["total_return"]
        stats["excess_return"] = stats["total_return"] - reference["metrics"]["total_return"]
    if gross:
        zero_cost = profile.model_copy(
            update={
                "fixed_fee": D(0),
                "commission_pct": D(0),
                "slippage": D(0),
                "spread": D(0),
                "fx_markup": D(0),
            }
        )
        replay = simulate(config, zero_cost, data, checkpoint, benchmark=False, gross=False)
        stats["gross_return"] = replay["metrics"]["total_return"]
    return result
