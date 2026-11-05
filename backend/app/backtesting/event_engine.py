"""Opt-in chronological event-clock simulation; legacy daily execution stays separate."""

from bisect import bisect_right
from datetime import UTC, timedelta
from decimal import Decimal, localcontext

from app.analytics.cashflows import normalize
from app.analytics.metrics import metrics
from app.backtesting.advanced_validation import execution_policy, requirements, validate_advanced
from app.backtesting.event_clocks import source_clocks
from app.backtesting.selection import select_universe
from app.backtesting.trading import planned_order, scheduled
from app.market_data.calendar import decision_timestamp, session_times, sessions
from app.market_data.features import requirements as external_requirements
from app.market_data.input_book import SignalView
from app.portfolio.ledger import Ledger
from app.schemas.domain import (
    ExecutionPolicy,
    OrderRecord,
    TradingPolicy,
    canonical_hash,
    default_strategy,
)
from app.strategies.interpreter import condition

D = Decimal


class Rates:
    def __init__(self, data, profile):
        self.profile = profile
        self.clocks = []
        self.best = []
        for row in sorted(data.fx, key=lambda r: (r.available_at, r.observed_at)):
            self.clocks.append(row.available_at)
            self.best.append(
                max(self.best[-1], row, key=lambda r: (r.observed_at, r.available_at))
                if self.best
                else row
            )

    def at(self, clock):
        if self.profile.account_currency == "USD":
            return D(1)
        i = bisect_right(self.clocks, clock) - 1
        if i < 0:
            raise ValueError(f"no historically available USD/SGD FX at {clock.isoformat()}")
        row = self.best[i]
        if row.observed_at > clock or clock - row.observed_at > timedelta(
            days=self.profile.max_fx_age_days
        ):
            raise ValueError(f"stale historical USD/SGD FX at {clock.isoformat()}")
        return row.rate


def inside(window, clock, opening, closing):
    return (
        opening + timedelta(minutes=window.start_minutes_after_open)
        <= clock
        < closing - timedelta(minutes=window.end_minutes_before_close)
    )


def simulate_events(
    config,
    profile,
    data,
    checkpoint=None,
    benchmark=True,
    gross=True,
    *,
    feature_data=None,
    source_data=None,
):
    with localcontext() as context:
        context.prec = 34
        return _simulate(
            config,
            profile,
            data,
            checkpoint,
            benchmark,
            gross,
            feature_data or [],
            source_data or [],
        )


def _simulate(config, profile, data, checkpoint, benchmark, gross, features, sources):
    book = validate_advanced(config, profile, data, sources, features)
    policy = execution_policy(config, profile)
    track_security = requirements(config, profile)["universe"]
    trading = config.trading or TradingPolicy()
    effective = config.model_copy(update={"trading": trading})
    ledger = Ledger(profile)
    rates = Rates(data, profile)
    days = sessions(profile.start_date, profile.end_date)
    extra_clocks = (
        source_clocks(config, profile, book, features, days)
        if policy.decision_cadence == "event_or_bar"
        else {}
    )
    intervals = book.intraday if profile.timeframe != "1d" else data.bars
    per_day = {}
    for bar in intervals:
        per_day.setdefault(bar.session_date, []).append(bar)
    orders = []
    signals = []
    curve = []
    intraday_curve = []
    selection_audit = []
    catalog = {}
    previous_clock = decision_timestamp(
        sessions(days[0] - timedelta(days=14), days[0] - timedelta(days=1))[-1], data.decision_time
    )
    previous_portfolios = {}
    instrument_ids = {}
    last_quotes = {}
    external_names = {n for n, _, _ in external_requirements(config)}

    def portfolio(symbol, prices, rate, index):
        equity = ledger.equity(prices, rate)
        position = ledger.positions.get(symbol)
        return {
            "cash": ledger.cash,
            "equity": equity,
            "position_quantity": position.quantity if position else D(0),
            "position_weight": position.quantity * prices[symbol] * rate / equity
            if position and equity
            else D(0),
            "holding_sessions": D(
                index
                - (
                    position.last_added_session
                    if position.last_added_session is not None
                    else position.opened_session
                )
            )
            if position
            else D(0),
        }

    def mark(day, clock, prices, rate, flowinfo):
        equity = ledger.equity(prices, rate)
        basis = sum((p.cost_basis for p in ledger.positions.values()), D(0))
        exposure = sum((p.quantity * prices[s] * rate for s, p in ledger.positions.items()), D(0))
        return {
            "date": str(day),
            "timestamp": clock.isoformat(),
            "equity": str(equity),
            "cash": str(ledger.cash),
            "exposure": str(exposure / equity if equity else 0),
            "realized_pnl": str(ledger.realized_pnl),
            "unrealized_pnl": str(equity - ledger.cash - basis),
            **(
                {
                    "external_flow": str(flowinfo[0]),
                    "cumulative_contributions": str(ledger.contributions),
                    "equity_before_flow": str(flowinfo[1]) if flowinfo[1] is not None else None,
                    "equity_after_flow": str(flowinfo[2]) if flowinfo[2] is not None else None,
                }
                if profile.monthly_contribution
                else {}
            ),
        }

    for index, day in enumerate(days):
        if checkpoint:
            checkpoint(int(index / len(days) * 95))
        opening, closing = session_times(day)
        final_clock = decision_timestamp(day, data.decision_time)
        daybars = per_day.get(day, [])
        starts = {}
        ends = {}
        for bar in daybars:
            start = getattr(bar, "start_at", opening)
            end = getattr(bar, "end_at", closing)
            starts.setdefault(start, {})[bar.symbol] = bar
            ends.setdefault(end, {})[bar.symbol] = bar
        clocks = set(starts) | set(ends) | {opening, closing, final_clock}
        if policy.decision_cadence in {"bar_close", "event_or_bar"}:
            clocks.update(b.available_at for b in daybars if opening < b.available_at <= closing)
        clocks.update(extra_clocks.get(day, set()))
        executed_today = 0
        gap_attempted = set()
        flowinfo = (D(0), None, None)
        flow_used = False

        def fill(order, raw, clock, rate, quote_prices, index=index):
            nonlocal executed_today
            try:
                if executed_today >= profile.max_orders_per_day:
                    raise ValueError("daily order frequency limit")
                quote = ledger.quote(order.side, order.quantity, raw, rate)
                if order.side == "buy":
                    if (
                        order.symbol not in ledger.positions
                        and len(ledger.positions) >= config.risk.max_positions
                    ):
                        raise ValueError("strategy position limit")
                    if any(s not in quote_prices for s in ledger.positions):
                        raise ValueError(
                            "held asset lacks an execution-clock quote; terminal actions/valuation are required"
                        )
                    equity = ledger.equity(quote_prices, rate)
                    notional = order.quantity * raw * rate
                    post = equity + quote.cash_delta + notional
                    held = sum(
                        (p.quantity * quote_prices[s] * rate for s, p in ledger.positions.items()),
                        D(0),
                    )
                    asset = (
                        ledger.positions[order.symbol].quantity * raw * rate
                        if order.symbol in ledger.positions
                        else D(0)
                    )
                    if asset + notional > post * config.risk.max_allocation:
                        raise ValueError("maximum cumulative asset allocation at execution")
                    if held + notional > post * profile.max_exposure:
                        raise ValueError("maximum portfolio exposure at execution")
                    if track_security and order.symbol in profile.symbols:
                        state = book.state(order.symbol, clock)
                        if not state.listed:
                            raise ValueError("asset is no longer historically listed")
                        if (
                            order.symbol in ledger.positions
                            and order.symbol in instrument_ids
                            and instrument_ids[order.symbol] != state.instrument_id
                        ):
                            raise ValueError(
                                "ticker identity changed; reviewed terminal action required"
                            )
                event = ledger.execute(
                    order.symbol,
                    order.side,
                    order.quantity,
                    raw,
                    rate,
                    clock,
                    index,
                    allow_adjustments=True,
                )
                if order.side == "buy" and track_security:
                    instrument_ids[order.symbol] = book.state(order.symbol, clock).instrument_id
                order.status = "filled"
                order.execution_price = D(event["price_usd"])
                order.fees = D(event["fees"])
                order.executed_at = clock
                executed_today += 1
                if order.side == "sell" and order.symbol not in ledger.positions:
                    for pending in orders:
                        if (
                            pending is not order
                            and pending.symbol == order.symbol
                            and pending.status == "pending"
                        ):
                            pending.status = "cancelled"
                            pending.rejection_reason = "position closed by an earlier exit"
                            pending.resolved_at = clock
                    instrument_ids.pop(order.symbol, None)
            except ValueError as exc:
                order.status = "rejected"
                order.rejection_reason = str(exc)
            order.resolved_at = clock

        def levels(position):
            return (
                position.entry_price * (1 - config.risk.stop_loss)
                if config.risk.stop_loss is not None
                else None,
                position.entry_price * (1 + config.risk.take_profit)
                if config.risk.take_profit is not None
                else None,
            )

        def protect(symbol, kind, raw, clock, rate, prices):
            position = ledger.positions[symbol]
            order = OrderRecord(
                id=len(orders) + 1,
                symbol=symbol,
                side="sell",
                type=kind,
                submitted_at=position.opened_at,
                eligible_after=position.opened_at,
                quantity=position.quantity,
                reason=f"protective {kind}; completed-interval chronology",
            )
            orders.append(order)
            fill(order, raw, clock, rate, prices)

        for clock in sorted({value.astimezone(UTC) for value in clocks}):
            if checkpoint:
                checkpoint(int(index / len(days) * 95))
            rate = rates.at(clock)
            # Check identity before a quote, valuation or exit can consume the
            # holding and erase its instrument provenance.
            for symbol in tuple(ledger.positions):
                if track_security and symbol in instrument_ids:
                    state = book.state(symbol, clock)
                    if state.instrument_id != instrument_ids[symbol] or not state.listed:
                        raise ValueError(
                            "held security changed identity/listing; reviewed terminal action and valuation history required"
                        )
            ending = ends.get(clock, {})
            for symbol, bar in ending.items():
                last_quotes[symbol] = bar.close
            # A range belongs only to the interval which has just ended. Newly
            # submitted decisions at this clock cannot receive its earlier open.
            for symbol in sorted(tuple(ledger.positions)):
                bar = ending.get(symbol)
                if bar is None:
                    continue
                start = getattr(bar, "start_at", opening)
                if (symbol, start) in gap_attempted or ledger.positions[symbol].opened_at > start:
                    continue
                stop, take = levels(ledger.positions[symbol])
                if stop is not None and bar.low <= stop:
                    protect(symbol, "stop_loss", stop, clock, rate, last_quotes)
                elif take is not None and bar.high >= take:
                    protect(symbol, "take_profit", take, clock, rate, last_quotes)

            quotes = starts.get(clock, {})
            quote_prices = {s: b.open for s, b in quotes.items()}
            last_quotes.update(quote_prices)
            if clock == opening:
                for action in sorted(
                    data.actions, key=lambda a: (a.session_date, a.kind != "split", a.symbol)
                ):
                    if action.session_date != day or action.available_at > opening:
                        continue
                    if action.kind == "split":
                        ledger.split(action.symbol, action.value, opening)
                        for pending in orders:
                            if pending.symbol == action.symbol and pending.status == "pending":
                                pending.quantity *= action.value
                    else:
                        ledger.dividend(action.symbol, action.value, action.payment_date, opening)
                ledger.settle_dividends(day, rate, opening)
                if profile.monthly_contribution and scheduled("monthly", day):
                    if any(s not in quote_prices for s in ledger.positions):
                        raise ValueError("opening funding valuation lacks a held-asset quote")
                    before = ledger.equity(quote_prices, rate)
                    ledger.contribute(profile.monthly_contribution, opening, before)
                    flowinfo = (
                        profile.monthly_contribution,
                        before,
                        before + profile.monthly_contribution,
                    )

            def gap(
                symbol,
                quotes=quotes,
                clock=clock,
                rate=rate,
                quote_prices=quote_prices,
                gap_attempted=gap_attempted,
            ):
                if symbol not in ledger.positions or symbol not in quotes:
                    return
                stop, take = levels(ledger.positions[symbol])
                raw = quotes[symbol].open
                if stop is not None and raw <= stop:
                    gap_attempted.add((symbol, clock))
                    protect(symbol, "stop_loss", raw, clock, rate, quote_prices)
                elif take is not None and raw >= take:
                    gap_attempted.add((symbol, clock))
                    protect(symbol, "take_profit", take, clock, rate, quote_prices)

            for symbol in sorted(tuple(ledger.positions)):
                gap(symbol)
            for order in list(orders):
                window = policy.entry_window if order.side == "buy" else policy.exit_window
                if (
                    order.status == "pending"
                    and order.eligible_after < clock
                    and order.symbol in quotes
                    and inside(window, clock, opening, closing)
                ):
                    fill(order, quotes[order.symbol].open, clock, rate, quote_prices)
            for symbol in sorted(tuple(ledger.positions)):
                if (
                    ledger.positions[symbol].opened_at == clock
                    or ledger.positions[symbol].last_added_session == index
                ):
                    if (symbol, clock) not in gap_attempted:
                        gap(symbol)
            if clock == closing and policy.pending_expiry == "session_close":
                for order in orders:
                    if order.status == "pending" and order.submitted_at < closing:
                        order.status = "cancelled"
                        order.resolved_at = clock
                        order.rejection_reason = "unfilled order expired at session close"

            decision = (
                clock == final_clock
                if policy.decision_cadence == "daily_close"
                else (policy.decision_cadence == "event_or_bar" and clock == opening)
                or (
                    opening < clock <= closing
                    and (
                        clock in extra_clocks.get(day, set())
                        or any(b.available_at == clock for b in daybars)
                    )
                )
            )
            if decision:
                prices = {}
                for symbol in set(profile.symbols) | set(ledger.positions) | {profile.benchmark}:
                    history, _ = book.history(symbol, policy.default_timeframe, clock)
                    if history:
                        prices[symbol] = history[-1].close
                if any(s not in prices for s in ledger.positions):
                    raise ValueError("held asset lacks a historically available valuation")
                # Securities remain visible even if a later classification removes
                # them from entry eligibility. Missing terminal quotes are errors.
                for symbol in ledger.positions:
                    if (
                        book.universe
                        and symbol in instrument_ids
                        and book.state(symbol, clock).instrument_id != instrument_ids[symbol]
                    ):
                        raise ValueError(
                            "held ticker changed identity; terminal-action history is required"
                        )
                equity = ledger.equity(prices, rate)
                current = {s: portfolio(s, prices, rate, index) for s in profile.symbols}
                views = {
                    s: SignalView(
                        book,
                        s,
                        clock,
                        previous_clock,
                        policy.default_timeframe,
                        current[s],
                        previous_portfolios.get(
                            s,
                            {"cash": profile.starting_capital, "equity": profile.starting_capital},
                        ),
                    )
                    for s in profile.symbols
                }
                eligible, ranking = select_universe(config, profile, book, clock, views)
                if ranking:
                    selection_audit.append(
                        {
                            "timestamp": clock.isoformat(),
                            "selected": eligible,
                            "candidates": ranking,
                        }
                    )
                ordered = (
                    sorted(set(ledger.positions) & set(profile.symbols))
                    + [s for s in eligible if s not in ledger.positions]
                    + [
                        s
                        for s in sorted(profile.symbols)
                        if s not in eligible and s not in ledger.positions
                    ]
                )
                for symbol in ordered:
                    view = views[symbol]
                    history, _ = book.history(symbol, policy.default_timeframe, clock)
                    position = ledger.positions.get(symbol)
                    entry = condition(config.entry, history, view)
                    exit = condition(config.exit, history, view) if position else False
                    chosen = config.sizing
                    size_reason = "base sizing"
                    for rule in config.sizing_rules or []:
                        if condition(rule.when, history, view) is True:
                            chosen = rule.sizing
                            size_reason = rule.label
                            break
                    selected_config = effective.model_copy(update={"sizing": chosen})
                    plan = None
                    reason = "entry condition false/unknown or outside selected universe"
                    force = bool(
                        position
                        and config.universe
                        and config.universe.exit_when_ineligible
                        and symbol not in eligible
                    )
                    if force:
                        selected_config = selected_config.model_copy(
                            update={"trading": trading.model_copy(update={"exit_fraction": D(1)})}
                        )
                    entry_allowed = (
                        symbol in eligible
                        and symbol in prices
                        and (
                            policy.decision_cadence == "daily_close"
                            or inside(policy.entry_window, clock, opening, closing)
                        )
                    )
                    exit_allowed = policy.decision_cadence == "daily_close" or inside(
                        policy.exit_window, clock, opening, closing
                    )
                    if symbol in prices:
                        plan = planned_order(
                            selected_config,
                            profile,
                            ledger,
                            orders,
                            symbol,
                            day,
                            index,
                            entry if entry_allowed else False,
                            True if force and exit_allowed else exit if exit_allowed else False,
                            prices,
                            rate,
                            equity,
                        )
                    if plan:
                        side, quantity, reason = plan
                        reason = f"{reason}; {size_reason}" + (
                            "; left selected universe" if force else ""
                        )
                        orders.append(
                            OrderRecord(
                                id=len(orders) + 1,
                                symbol=symbol,
                                side=side,
                                submitted_at=clock,
                                eligible_after=clock,
                                quantity=quantity,
                                reason=reason,
                            )
                        )
                    elif not entry_allowed and not position:
                        reason = "outside entry window or selected universe"
                    elif any(o.symbol == symbol and o.status == "pending" for o in orders):
                        reason = "pending order prevents duplicate submission"
                    else:
                        reason = "rule, window, holding lock, or affordable sizing does not permit an order"
                    evaluations = []
                    for item in view.evaluations:
                        expression = item["expression"]
                        key = canonical_hash(expression)
                        catalog[key] = expression
                        evaluations.append(
                            {
                                "expression_id": key,
                                **{k: v for k, v in item.items() if k != "expression"},
                            }
                        )
                    signals.append(
                        {
                            "timestamp": clock.isoformat(),
                            "symbol": symbol,
                            "action": plan[0] if plan else "hold",
                            "rule": config.entry.model_dump(mode="json"),
                            "condition_result": entry,
                            "exit_rule": config.exit.model_dump(mode="json"),
                            "exit_condition_result": exit,
                            "reason": reason,
                            "selected": symbol in eligible,
                            "sizing_rule": size_reason,
                            "evaluations": evaluations,
                            **(
                                {"external_inputs": view.audit(external_names)}
                                if external_names
                                else {}
                            ),
                        }
                    )
                    if len(signals) > 500_000:
                        raise ValueError(
                            "run exceeds audit-record limit; reduce universe or use coarser intervals"
                        )
                previous_portfolios = current
                previous_clock = clock

            if profile.timeframe != "1d" and (ending or clock == opening or clock == final_clock):
                if any(
                    s not in last_quotes
                    or (s not in ending and s not in quotes and clock <= closing)
                    for s in ledger.positions
                ):
                    raise ValueError(
                        "held asset missing current interval quote; no stale terminal valuation is permitted"
                    )
                intraday_curve.append(
                    mark(
                        day,
                        clock,
                        last_quotes,
                        rate,
                        flowinfo if not flow_used else (D(0), None, None),
                    )
                )
                flow_used = True
            if clock == final_clock:
                known = {}
                for symbol in ledger.positions:
                    history, _ = book.history(
                        symbol, "intraday" if profile.timeframe != "1d" else "daily", clock
                    )
                    if not history or history[-1].session_date != day:
                        raise ValueError(
                            "held asset lacks the current session's completed valuation; terminal action required"
                        )
                    known[symbol] = history[-1].close
                curve.append(mark(day, clock, known, rate, flowinfo))

    stats = metrics(curve, ledger, profile)
    if intraday_curve:
        if profile.monthly_contribution:
            normalize(intraday_curve, profile.starting_capital)
        else:
            peak = profile.starting_capital
            for row in intraday_curve:
                value = D(row["equity"])
                peak = max(peak, value)
                row["drawdown"] = float(value / peak - 1)
        if profile.monthly_contribution:
            peak = profile.starting_capital
            for row in intraday_curve:
                value = D(row["performance_equity"])
                peak = max(peak, value)
                row["drawdown"] = float(value / peak - 1)
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
        "receivables": [
            {**r, "amount_usd": str(r["amount_usd"]), "payment_date": str(r["payment_date"])}
            for r in ledger.receivables
        ],
        "warnings": (
            ["Synthetic demonstration data — not historical investment performance."]
            if data.synthetic
            or any(s.synthetic for s in sources)
            or any(s.synthetic for s in features)
            else []
        )
        + [
            "Historical research; source publication/classification coverage and executable-quote assumptions require review.",
            "Intraday market fills use the next strictly later interval open; full fills, no liquidity model.",
            "Statistics and annualization use daily marks, not intraday observations.",
            f"Research designation: {profile.research_label}; repeated optimization is in-sample.",
            data.availability_policy,
        ]
        + (
            ["Price-only research: complete dividends are unavailable."]
            if not data.dividends_complete
            else []
        ),
        "universe_decisions": selection_audit,
        "expression_catalog": catalog,
        "execution_policy": policy.model_dump(mode="json"),
    }
    if intraday_curve:
        result["intraday_equity"] = intraday_curve
    if benchmark:
        bench = default_strategy()
        bench.sizing.value = D(1)
        bench.trading = TradingPolicy(allow_additions=bool(profile.monthly_contribution))
        if profile.monthly_contribution:
            bench.sizing.mode = "target_allocation"
        bench.execution_policy = ExecutionPolicy(
            decision_cadence="bar_close" if profile.timeframe != "1d" else "daily_close",
            default_timeframe="intraday" if profile.timeframe != "1d" else "daily",
        )
        reference = simulate_events(
            bench,
            profile.model_copy(update={"symbols": [profile.benchmark]}),
            data,
            checkpoint,
            False,
            False,
            source_data=sources,
        )
        result["benchmark"] = {
            k: reference[k] for k in ("metrics", "equity", "intraday_equity") if k in reference
        }
        stats["benchmark_total_return"] = reference["metrics"]["total_return"]
        stats["excess_return"] = stats["total_return"] - stats["benchmark_total_return"]
    if gross:
        zero = profile.model_copy(
            update={
                name: D(0)
                for name in ("fixed_fee", "commission_pct", "slippage", "spread", "fx_markup")
            }
        )
        replay = simulate_events(
            config, zero, data, checkpoint, False, False, feature_data=features, source_data=sources
        )
        stats["gross_return"] = replay["metrics"]["total_return"]
    return result
