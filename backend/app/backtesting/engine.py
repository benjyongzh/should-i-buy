from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal, localcontext

from app.analytics.metrics import metrics
from app.backtesting.trading import planned_order, scheduled
from app.market_data.calendar import decision_timestamp, session_times, sessions
from app.market_data.features import (
    FeatureBook,
    FeatureSeries,
    decision_pair,
    requirements,
    validate_features,
)
from app.market_data.validation import validate_coverage, validate_dataset
from app.market_data.view import DataView, fx_at, split_history
from app.portfolio.ledger import Ledger, Position
from app.schemas.domain import (
    DatasetInput,
    OrderRecord,
    ProfileConfig,
    StrategyConfig,
    TradingPolicy,
    default_strategy,
)
from app.strategies.interpreter import condition

ENGINE_VERSION = "2.0.0"
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
    *,
    feature_data: list[FeatureSeries] | None = None,
    source_data: list | None = None,
) -> dict:
    from app.market_data.strategy_inputs import advanced

    if advanced(config, profile):
        from app.backtesting.event_engine import simulate_events

        return simulate_events(
            config,
            profile,
            data,
            checkpoint,
            benchmark,
            gross,
            feature_data=feature_data,
            source_data=source_data,
        )
    with localcontext() as context:
        context.prec = 34
        return _simulate(config, profile, data, checkpoint, benchmark, gross, feature_data or [])


def _simulate(
    config: StrategyConfig,
    profile: ProfileConfig,
    data: DatasetInput,
    checkpoint: Callable[[int], None] | None,
    benchmark: bool,
    gross: bool,
    feature_data: list[FeatureSeries],
) -> dict:
    validate_dataset(data)
    validate_coverage(data, profile)
    feature_book = FeatureBook(feature_data)
    validate_features(config, feature_book, data, profile)
    feature_names = {name for name, _, _ in requirements(config)}
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
        flow = D(0)
        before_flow = after_flow = None
        if profile.monthly_contribution and scheduled("monthly", day):
            before_flow = ledger.equity(
                {s: by_session[(s, day)].open for s in ledger.positions}, rate
            )
            flow = profile.monthly_contribution
            ledger.contribute(flow, opening, before_flow)
            after_flow = before_flow + flow

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
                quote = ledger.quote(order.side, order.quantity, raw_price, fx)
                if order.side == "buy":
                    if (
                        order.symbol not in ledger.positions
                        and len(ledger.positions) >= config.risk.max_positions
                    ):
                        raise ValueError("strategy position limit")
                    # Use execution-time opens only for risk/affordability, never to generate signals.
                    open_prices = {s: by_session[(s, day)].open for s in ledger.positions}
                    equity = ledger.equity(open_prices, fx)
                    notional = order.quantity * raw_price * fx
                    post_trade_equity = equity + quote.cash_delta + notional
                    existing = sum(
                        (p.quantity * open_prices[s] * fx for s, p in ledger.positions.items()),
                        D(0),
                    )
                    asset_held = (
                        ledger.positions[order.symbol].quantity * raw_price * fx
                        if order.symbol in ledger.positions
                        else D(0)
                    )
                    if asset_held + notional > post_trade_equity * config.risk.max_allocation:
                        raise ValueError("maximum asset allocation at execution")
                    if existing + notional > post_trade_equity * profile.max_exposure:
                        raise ValueError("maximum portfolio exposure at execution")
                event = ledger.execute(
                    order.symbol,
                    order.side,
                    order.quantity,
                    raw_price,
                    fx,
                    timestamp,
                    index,
                    allow_adjustments=config.trading is not None,
                )
                order.status = "filled"
                order.execution_price = D(event["price_usd"])
                order.fees = D(event["fees"])
                order.executed_at = timestamp
                executed_today += 1
                if order.side == "sell" and order.symbol not in ledger.positions:
                    for pending in orders:
                        if (
                            pending is not order
                            and pending.symbol == order.symbol
                            and (pending.side == "sell" or config.trading is not None)
                            and pending.status == "pending"
                        ):
                            pending.status = "cancelled"
                            pending.rejection_reason = "position closed by an earlier exit"
            except ValueError as exc:
                order.status = "rejected"
                order.rejection_reason = str(exc)

        def protective_levels(position: Position) -> tuple[Decimal | None, Decimal | None]:
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
            return stop, take

        def protective_exit(
            symbol: str,
            position: Position,
            kind: str,
            raw: Decimal,
            timestamp: datetime,
            fx: Decimal,
        ) -> None:
            order = OrderRecord(
                id=len(orders) + 1,
                symbol=symbol,
                side="sell",
                type=kind,
                submitted_at=position.opened_at,
                eligible_after=position.opened_at,
                quantity=position.quantity,
                reason=f"protective {kind}; chronological open/close policy",
            )
            orders.append(order)
            fill(order, raw, timestamp, fx)

        gap_attempted: set[str] = set()

        def opening_protection(
            symbol: str, day: date, opening: datetime, rate: Decimal, gap_attempted: set[str]
        ) -> None:
            position = ledger.positions[symbol]
            stop, take = protective_levels(position)
            raw_open = by_session[(symbol, day)].open
            if stop is not None and raw_open <= stop:
                gap_attempted.add(symbol)
                protective_exit(symbol, position, "stop_loss", raw_open, opening, rate)
            elif take is not None and raw_open >= take:
                gap_attempted.add(symbol)
                # The opening print establishes the event before any later range; no favorable gap improvement.
                protective_exit(symbol, position, "take_profit", take, opening, rate)

        # First handle opening gaps on carried positions using opening quotes only.
        for symbol in sorted(ledger.positions):
            opening_protection(symbol, day, opening, rate, gap_attempted)
        for order in orders:
            if order.status == "pending" and order.eligible_after < opening:
                fill(order, by_session[(order.symbol, day)].open, opening, rate)
        # Entry costs can put an immediately active protective level beyond the same opening quote.
        for symbol in sorted(ledger.positions):
            position = ledger.positions[symbol]
            if (
                position.opened_session == index or position.last_added_session == index
            ) and symbol not in gap_attempted:
                opening_protection(symbol, day, opening, rate, gap_attempted)

        # Only after every opening event may the execution simulator inspect daily ranges.
        # Book unknown intraday touches at close; stop wins genuinely ambiguous intraday bars.
        for symbol in sorted(ledger.positions):
            if symbol in gap_attempted:
                continue
            position = ledger.positions[symbol]
            bar = by_session[(symbol, day)]
            stop, take = protective_levels(position)
            raw = kind = None
            if stop is not None and bar.low <= stop:
                raw, kind = stop, "stop_loss"
            elif take is not None and bar.high >= take:
                raw, kind = take, "take_profit"
            if raw is not None:
                fx = (
                    fx_at(data.fx, closing, profile.max_fx_age_days)
                    if profile.account_currency == "SGD"
                    else D(1)
                )
                protective_exit(symbol, position, kind, raw, closing, fx)

        while cursor < len(bars) and bars[cursor].available_at <= decision_time:
            history.append(bars[cursor])
            cursor += 1
        # Adjust historical indicator inputs only for splits effective AND known by this clock.
        adjusted = split_history(history, data.actions, decision_time)
        view = DataView(adjusted, decision_time)
        feature_view = (
            feature_book.materialize(*decision_pair(day, data.decision_time))
            if feature_names
            else None
        )
        previous_view = (
            DataView(
                split_history(history, data.actions, feature_view.cutoff(1)), feature_view.cutoff(1)
            )
            if feature_view
            else None
        )
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
            if config.trading is not None:
                entry_active = condition(
                    config.entry,
                    permissible,
                    feature_view,
                    previous_view.history(symbol) if previous_view else None,
                )
                exit_active = (
                    condition(
                        config.exit,
                        permissible,
                        feature_view,
                        previous_view.history(symbol) if previous_view else None,
                    )
                    if position
                    else False
                )
                plan = planned_order(
                    config,
                    profile,
                    ledger,
                    orders,
                    symbol,
                    day,
                    index,
                    entry_active,
                    exit_active,
                    prices,
                    close_fx,
                    equity,
                )
                signals.append(
                    {
                        "timestamp": decision_time.isoformat(),
                        "symbol": symbol,
                        "action": plan[0] if plan else "hold",
                        "rule": config.entry.model_dump(mode="json"),
                        "condition_result": entry_active,
                        "exit_condition_result": exit_active,
                        "exit_rule": config.exit.model_dump(mode="json"),
                        "reason": plan[2]
                        if plan
                        else "condition, schedule, holding period, or available sizing does not permit an order",
                        **(
                            {"external_inputs": feature_view.audit(feature_names)}
                            if feature_view
                            else {}
                        ),
                    }
                )
                if plan:
                    side, quantity, reason = plan
                    orders.append(
                        OrderRecord(
                            id=len(orders) + 1,
                            symbol=symbol,
                            side=side,
                            submitted_at=decision_time,
                            eligible_after=decision_time,
                            quantity=quantity,
                            reason=reason,
                        )
                    )
                continue
            rule = config.exit if position else config.entry
            active = condition(
                rule,
                permissible,
                feature_view,
                previous_view.history(symbol) if previous_view else None,
            )
            signals.append(
                {
                    "timestamp": decision_time.isoformat(),
                    "symbol": symbol,
                    "action": ("sell" if position else "buy") if active is True else "hold",
                    "rule": rule.model_dump(mode="json"),
                    "condition_result": active,
                    **(
                        {"external_inputs": feature_view.audit(feature_names)}
                        if feature_view
                        else {}
                    ),
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
                **(
                    {
                        "external_flow": str(flow),
                        "cumulative_contributions": str(ledger.contributions),
                        "equity_before_flow": str(before_flow) if before_flow is not None else None,
                        "equity_after_flow": str(after_flow) if after_flow is not None else None,
                    }
                    if profile.monthly_contribution
                    else {}
                ),
            }
        )
    stats = metrics(curve, ledger, profile)
    warnings = (
        ["Synthetic demonstration data — not historical investment performance."]
        if data.synthetic or any(source.synthetic for source in feature_data)
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
    if feature_names:
        result["external_inputs"] = [
            {
                "series_id": source.series_id,
                "content_hash": source.content_hash,
                "synthetic": source.synthetic,
            }
            for source in sorted(feature_data, key=lambda s: s.series_id)
        ]
    if benchmark:
        bench = default_strategy()
        bench.sizing.value = D(1)
        if profile.monthly_contribution:
            bench.trading = TradingPolicy(allow_additions=True)
            bench.sizing.mode = "target_allocation"
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
        replay = simulate(
            config,
            zero_cost,
            data,
            checkpoint,
            benchmark=False,
            gross=False,
            feature_data=feature_data,
        )
        stats["gross_return"] = replay["metrics"]["total_return"]
    return result
