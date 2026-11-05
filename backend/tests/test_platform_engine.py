from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, localcontext

import pytest
from platform_fixtures import (
    event,
    event_source,
    platform_data,
    platform_profile,
    platform_strategy,
    universe_source,
)

from app.backtesting.engine import simulate
from app.market_data.calendar import session_times
from app.market_data.input_book import InputBook, SignalView
from app.schemas.domain import Action, Compare, UniversePolicy
from app.strategies.interpreter import condition, numeric

D = Decimal


def run(config, profile, data, sources, **kw):
    return simulate(config, profile, data, source_data=sources, benchmark=False, gross=False, **kw)


def test_strictly_later_interval_window_and_no_same_bar_fill():
    data, source = platform_data()
    config = platform_strategy(60)
    p = platform_profile(data)
    result = run(config, p, data, [source])
    fill = next(o for o in result["orders"] if o["status"] == "filled")
    opening = session_times(p.start_date)[0]
    assert datetime.fromisoformat(fill["submitted_at"]) == opening + timedelta(minutes=60)
    assert datetime.fromisoformat(fill["executed_at"]) == opening + timedelta(minutes=65)
    assert D(fill["quantity"]) == 10
    assert result["metrics"]["total_return"] == 0
    assert len(result["equity"]) == 2 and len(result["intraday_equity"]) > 100
    assert result == run(config, p, data, [source])


def test_intraday_requires_real_resolution_and_complete_coverage():
    data, source = platform_data()
    config = platform_strategy(60)
    with pytest.raises(ValueError, match="daily candles cannot"):
        run(config, platform_profile(data, minute=None), data, [source])
    with pytest.raises(ValueError, match="matching the profile"):
        run(config, platform_profile(data), data, [])
    source.bars = source.bars[1:]
    with pytest.raises(ValueError, match="missing required intraday"):
        run(config, platform_profile(data), data, [source])


def test_engine_revalidates_source_chronology_and_review_status_not_only_ingestion():
    data, source = platform_data()
    opening = session_times(date(2020, 1, 2))[0]
    broken = source.model_copy(
        update={
            "bars": [
                b.model_copy(update={"available_at": opening + timedelta(minutes=5)})
                for b in source.bars
            ]
        }
    )
    with pytest.raises(ValueError, match="completed before"):
        run(platform_strategy(), platform_profile(data), data, [broken])
    unreviewed = source.model_copy(
        update={"reviewed": False, "parent_id": None, "parent_hash": None, "review_note": ""}
    )
    with pytest.raises(ValueError, match="reviewed revisions"):
        run(platform_strategy(), platform_profile(data), data, [unreviewed])


def test_nonoverlapping_intraday_partitions_and_overlap_rejection():
    data, source = platform_data()
    first = source.model_copy(
        update={"bars": [b for b in source.bars if b.session_date == date(2020, 1, 2)]}
    )
    second = source.model_copy(
        update={"bars": [b for b in source.bars if b.session_date == date(2020, 1, 3)]}
    )
    config = platform_strategy()
    p = platform_profile(data)
    assert run(config, p, data, [first, second]) == run(config, p, data, [source])
    with pytest.raises(ValueError, match="overlapping intraday"):
        run(config, p, data, [first, source])


def test_early_close_and_dst_use_actual_exchange_open():
    for start, end in [
        (date(2020, 11, 27), date(2020, 11, 27)),
        (date(2020, 3, 6), date(2020, 3, 9)),
    ]:
        data, source = platform_data(start, end)
        result = run(platform_strategy(60), platform_profile(data), data, [source])
        fill = next(o for o in result["orders"] if o["status"] == "filled")
        assert datetime.fromisoformat(fill["executed_at"]) - session_times(start)[0] == timedelta(
            minutes=65
        )
        assert all(
            datetime.fromisoformat(o["executed_at"])
            <= session_times(
                datetime.fromisoformat(o["executed_at"])
                .astimezone(__import__("zoneinfo").ZoneInfo("America/New_York"))
                .date()
            )[1]
            for o in result["orders"]
            if o["executed_at"]
        )


def test_funding_is_monthly_not_per_tick_and_metrics_use_daily_marks():
    data, source = platform_data(date(2020, 1, 30), date(2020, 2, 4))
    p = platform_profile(data, monthly_contribution="500")
    config = platform_strategy()
    config.trading.entry_schedule = "daily"
    config.trading.allow_additions = True
    result = simulate(config, p, data, source_data=[source])
    contributions = [e for e in result["ledger"] if e["kind"] == "contribution"]
    assert len(contributions) == 1 and D(contributions[0]["cash_delta"]) == 500
    assert result["metrics"]["total_contributions"] == "500"
    assert result["metrics"]["annualized_return"] is None
    assert len(result["metrics"]["daily_returns"]) == 4
    assert result["benchmark"]["metrics"]["total_contributions"] == "500"
    assert result["metrics"]["total_return"] == result["metrics"]["gross_return"] == 0
    assert D(result["intraday_equity"][-1]["equity"]) == D(result["equity"][-1]["equity"])


def test_universe_sector_preference_ranking_and_historical_changes():
    data, source = platform_data(symbols=("SPY", "AAPL", "MSFT", "CVS"))
    states = universe_source(["AAPL", "MSFT", "CVS"])
    config = platform_strategy()
    config.universe = UniversePolicy(prefer_sectors=["Technology"], top_n=1)
    p = platform_profile(data)
    p.symbols = ["AAPL", "MSFT", "CVS"]
    result = run(config, p, data, [source, states])
    assert {e["symbol"] for e in result["ledger"] if e["kind"] == "buy"} == {"AAPL"}
    assert result["universe_decisions"][0]["selected"] == ["AAPL"]
    states.states[0].available_at = datetime(2025, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="no historically known"):
        run(config, p, data, [source, states])


def test_future_classification_and_price_event_mutations_preserve_prefix():
    data, source = platform_data(symbols=("SPY", "AAPL", "MSFT"))
    states = universe_source(["AAPL", "MSFT"])
    news = event_source([event(clock="2020-01-03T15:30:00Z")])
    config = platform_strategy()
    config.universe = UniversePolicy(sectors=["Technology"], top_n=1)
    config.entry = Compare(
        type="compare",
        op="gte",
        left={"type": "event", "stream_id": "NEWS", "scope": "global"},
        right={"type": "constant", "value": 0},
    )
    p = platform_profile(data)
    p.symbols = ["AAPL", "MSFT"]
    before = run(config, p, data, [source, states, news])
    mutated = source.model_copy(deep=True)
    for b in mutated.bars:
        if b.session_date > date(2020, 1, 2):
            b.open *= 3
            b.close *= 3
            b.high *= 3
            b.low *= 3
    changed = states.model_copy(deep=True)
    changed.states.append(
        changed.states[0].model_copy(
            update={
                "effective_at": datetime(2020, 1, 3, tzinfo=UTC),
                "available_at": datetime(2020, 1, 3, tzinfo=UTC),
                "sector": "Healthcare",
            }
        )
    )
    after = run(config, p, data, [mutated, changed, news])
    cutoff = session_times(date(2020, 1, 2))[1] + timedelta(hours=8)
    for key in ("signals", "ledger", "intraday_equity", "universe_decisions"):
        assert [r for r in before[key] if datetime.fromisoformat(r["timestamp"]) <= cutoff] == [
            r for r in after[key] if datetime.fromisoformat(r["timestamp"]) <= cutoff
        ]


def test_delayed_news_score_and_unknown_vs_zero_event_coverage():
    data, source = platform_data()
    news = event_source([event(score=".8", score_available_at="2020-01-02T16:30:00Z")])
    book = InputBook(data, [source, news])
    clock = datetime(2020, 1, 2, 16, tzinfo=UTC)
    view = SignalView(book, "SPY", clock, clock - timedelta(minutes=5), "intraday", {}, {})
    counted = Compare(
        type="compare",
        op="gt",
        left={"type": "event", "stream_id": "NEWS", "measure": "count"},
        right={"type": "constant", "value": 0},
    )
    scored = Compare(
        type="compare",
        op="gt",
        left={"type": "event", "stream_id": "NEWS", "measure": "latest_score"},
        right={"type": "constant", "value": 0},
    )
    bars, _ = book.history("SPY", "intraday", clock)
    assert condition(counted, bars, view) is True and condition(scored, bars, view) is None
    empty = InputBook(data, [source, event_source([])])
    assert (
        condition(
            counted,
            bars,
            SignalView(empty, "SPY", clock, clock - timedelta(minutes=5), "intraday", {}, {}),
        )
        is False
    )
    missing = InputBook(data, [source])
    with pytest.raises(ValueError, match="complete event coverage"):
        condition(
            counted,
            bars,
            SignalView(missing, "SPY", clock, clock - timedelta(minutes=5), "intraday", {}, {}),
        )


def test_known_future_corporate_action_is_usable_only_after_announcement():
    data, source = platform_data()
    data.actions = [
        Action(
            symbol="SPY",
            kind="dividend",
            session_date=date(2020, 1, 3),
            payment_date=date(2020, 1, 3),
            value="1",
            available_at="2020-01-02T16:00:00Z",
        )
    ]
    book = InputBook(data, [source])
    expr = Compare(
        type="compare",
        op="gt",
        left={
            "type": "corporate_action",
            "kind": "dividend",
            "window": "effective_next",
            "days": 7,
        },
        right={"type": "constant", "value": 0},
    )
    for clock, expected in [
        (datetime(2020, 1, 2, 15, tzinfo=UTC), False),
        (datetime(2020, 1, 2, 17, tzinfo=UTC), True),
    ]:
        bars, _ = book.history("SPY", "intraday", clock)
        view = SignalView(book, "SPY", clock, clock - timedelta(minutes=5), "intraday", {}, {})
        assert condition(expr, bars, view) is expected


def test_conditional_sizing_and_portfolio_scalar_are_declarative():
    data, source = platform_data()
    config = platform_strategy()
    config.sizing_rules = [
        __import__("app.schemas.domain", fromlist=["ConditionalSizing"]).ConditionalSizing(
            when={
                "type": "compare",
                "op": "gte",
                "left": {"type": "portfolio", "field": "cash"},
                "right": {"type": "constant", "value": 10000},
            },
            sizing={"mode": "fixed_notional", "value": 500},
            label="Conservative initial tranche",
        )
    ]
    result = run(config, platform_profile(data), data, [source])
    assert D(next(o for o in result["orders"] if o["status"] == "filled")["quantity"]) == 5
    assert "Conservative initial tranche" in result["orders"][0]["reason"]


def test_stop_does_not_use_later_interval_to_preempt_earlier_fill():
    data, source = platform_data()
    config = platform_strategy()
    config.risk.stop_loss = D(".1")
    p = platform_profile(data)
    original = run(config, p, data, [source])
    later = source.model_copy(deep=True)
    opening = session_times(p.start_date)[0]
    for bar in later.bars:
        if bar.start_at == opening + timedelta(minutes=30):
            bar.low = D(80)
    after = run(config, p, data, [later])
    assert after["orders"][0] == original["orders"][0]
    stopped = next(o for o in after["orders"] if o["type"] == "stop_loss")
    assert datetime.fromisoformat(stopped["executed_at"]) == opening + timedelta(minutes=35)


def test_streamed_indicators_match_existing_exact_decimal_conventions():
    from app.schemas.domain import MACD, Indicator, Stochastic

    data, source = platform_data()
    for i, bar in enumerate(source.bars):
        price = D(100 + i % 13 - i % 7)
        bar.open = bar.close = price
        bar.high = price + 2
        bar.low = price - 2
    book = InputBook(data, [source])
    nodes = (
        [
            Indicator(type="indicator", name=name, period=5)
            for name in [
                "sma",
                "ema",
                "rsi",
                "momentum",
                "avg_volume",
                "rolling_high",
                "rolling_low",
            ]
        ]
        + [
            MACD(type="macd", fast_period=3, slow_period=7, signal_period=4, component=c)
            for c in ["line", "signal", "histogram"]
        ]
        + [
            Stochastic(type="stochastic", period=5, smooth_k=3, smooth_d=3, component=c)
            for c in ["k", "d"]
        ]
    )
    with localcontext() as ctx:
        ctx.prec = 34
        for bar in source.bars:
            clock = bar.available_at
            history, key = book.history("SPY", "intraday", clock)
            for node in nodes:
                assert book.cache.value(node, history, key) == numeric(node, history), (
                    node,
                    len(history),
                )


def test_intraday_historical_fx_split_dividend_and_costs_reconcile_by_hand():
    from app.schemas.domain import FXObservation

    data, source = platform_data()
    opening = session_times(date(2020, 1, 2))[0]
    data.fx = [
        FXObservation(
            observed_at=opening - timedelta(hours=1),
            available_at=opening - timedelta(minutes=30),
            rate="1.35",
        ),
        FXObservation(
            observed_at=opening + timedelta(minutes=8),
            available_at=opening + timedelta(minutes=9),
            rate="1.4",
        ),
    ]
    splitday = date(2020, 1, 3)
    for b in source.bars:
        if b.session_date == splitday:
            b.open = b.close = b.high = b.low = D(50)
    for b in data.bars:
        if b.session_date == splitday:
            b.open = b.close = b.high = b.low = D(50)
    data.actions = [
        Action(symbol="SPY", kind="split", session_date=splitday, value="2", available_at=opening),
        Action(
            symbol="SPY",
            kind="dividend",
            session_date=splitday,
            value="1",
            payment_date=splitday,
            available_at=opening,
        ),
    ]
    p = platform_profile(data, monthly_contribution="500")
    p.account_currency = "SGD"
    p.fx_markup = D(".01")
    p.slippage = D(".001")
    p.fixed_fee = D("2.50")
    result = simulate(platform_strategy(), p, data, source_data=[source])
    buy = next(e for e in result["ledger"] if e["kind"] == "buy")
    assert D(buy["quantity"]) == 7 and D(buy["fx_sgd_per_usd"]) == D("1.4")
    assert D(buy["cash_delta"]) == D("-993.2898")
    assert D(result["positions"]["SPY"]["quantity"]) == 14
    assert D(result["metrics"]["ending_equity"]) == D("10506.3102")
    assert D(result["metrics"]["absolute_pnl"]) == D("6.3102")
    assert D(result["equity"][-1]["cash"]) == D("9526.3102")
    assert D(
        next(e for e in result["ledger"] if e["kind"] == "dividend_payment")["cash_delta"]
    ) == D("19.6")


def test_carried_opening_take_profit_precedes_that_intervals_later_low():
    data, source = platform_data()
    config = platform_strategy()
    config.risk.stop_loss = D(".1")
    config.risk.take_profit = D(".1")
    opening = session_times(date(2020, 1, 2))[0]
    bar = next(b for b in source.bars if b.start_at == opening + timedelta(minutes=15))
    bar.open = D(120)
    bar.high = D(125)
    bar.low = D(80)
    result = run(config, platform_profile(data), data, [source])
    exit = next(o for o in result["orders"] if o["side"] == "sell" and o["status"] == "filled")
    assert exit["type"] == "take_profit" and D(exit["execution_price"]) == 110
    assert datetime.fromisoformat(exit["executed_at"]) == opening + timedelta(minutes=15)


def test_cross_asset_later_range_cannot_change_earlier_order_frequency_outcome():
    data, source = platform_data(symbols=("SPY", "AAPL", "MSFT"))
    config = platform_strategy()
    config.risk.stop_loss = D(".1")
    p = platform_profile(data, max_orders_per_day=1)
    p.symbols = ["AAPL", "MSFT"]
    before = run(config, p, data, [source])
    changed = source.model_copy(deep=True)
    opening = session_times(p.start_date)[0]
    for b in changed.bars:
        if b.symbol == "AAPL" and b.start_at == opening + timedelta(minutes=30):
            b.low = D(80)
    after = run(config, p, data, [changed])
    assert before["orders"][:2] == after["orders"][:2]
    assert (
        after["orders"][1]["status"] == "rejected"
        and "frequency" in after["orders"][1]["rejection_reason"]
    )


@pytest.mark.parametrize("protective", [False, True])
def test_identity_transition_is_checked_before_ordinary_and_protective_exits(protective):
    data, bars = platform_data()
    opening = session_times(date(2020, 1, 2))[0]
    states = universe_source(["SPY"])
    changed_at = opening + timedelta(minutes=60)
    states.states.append(
        states.states[0].model_copy(
            update={
                "instrument_id": "DIFFERENT_COMPANY",
                "effective_at": changed_at,
                "available_at": changed_at,
            }
        )
    )
    config = platform_strategy()
    config.universe = UniversePolicy(top_n=1)
    news = event_source([event(clock=(opening + timedelta(minutes=55)).isoformat())])
    if protective:
        config.risk.take_profit = D(".1")
        bar = next(b for b in bars.bars if b.start_at == changed_at)
        bar.open = D(120)
        bar.high = D(125)
    else:
        config.exit = Compare(
            type="compare",
            op="gt",
            left={"type": "event", "stream_id": "NEWS"},
            right={"type": "constant", "value": 0},
        )
    with pytest.raises(ValueError, match="held security changed identity"):
        run(config, platform_profile(data), data, [bars, states, news])


def test_calendar_conditions_allow_first_friday_and_open_relative_rules_without_code():
    from app.schemas.domain import Group

    data, bars = platform_data()
    config = platform_strategy(60)
    config.entry = Group(
        type="all",
        conditions=[
            {
                "type": "compare",
                "op": "eq",
                "left": {"type": "calendar", "field": "weekday"},
                "right": {"type": "constant", "value": 4},
            },
            {
                "type": "compare",
                "op": "gte",
                "left": {"type": "calendar", "field": "minutes_after_open"},
                "right": {"type": "constant", "value": 60},
            },
        ],
    )
    result = run(config, platform_profile(data), data, [bars])
    fill = next(o for o in result["orders"] if o["status"] == "filled")
    assert datetime.fromisoformat(fill["executed_at"]) == session_times(date(2020, 1, 3))[
        0
    ] + timedelta(minutes=65)


def test_event_cadence_reacts_after_publication_without_private_clock_leakage():
    data, bars = platform_data()
    opening = session_times(date(2020, 1, 2))[0]
    public = event(clock=(opening + timedelta(minutes=12)).isoformat())
    private = event(
        event_id="private",
        clock=(opening + timedelta(minutes=13)).isoformat(),
        access="subscription",
    )
    config = platform_strategy()
    config.execution_policy.decision_cadence = "event_or_bar"
    config.entry = Compare(
        type="compare",
        op="gt",
        left={"type": "event", "stream_id": "NEWS", "access": "public_only"},
        right={"type": "constant", "value": 0},
    )
    p = platform_profile(data)
    first = run(config, p, data, [bars, event_source([public], access_coverage="any_licensed")])
    second = run(
        config, p, data, [bars, event_source([public, private], access_coverage="any_licensed")]
    )
    assert first == second
    filled = next(o for o in first["orders"] if o["status"] == "filled")
    assert datetime.fromisoformat(filled["submitted_at"]) == opening + timedelta(minutes=12)
    assert datetime.fromisoformat(filled["executed_at"]) == opening + timedelta(minutes=15)


def test_partition_order_with_equal_instant_different_offsets_is_exactly_reproducible():
    from datetime import timezone

    data, bars = platform_data(symbols=("SPY", "AAPL"))
    first = bars.model_copy(update={"bars": [b for b in bars.bars if b.symbol == "SPY"]})
    offset = timezone(timedelta(hours=8))
    second = bars.model_copy(
        update={
            "bars": [
                b.model_copy(
                    update={
                        field: getattr(b, field).astimezone(offset)
                        for field in ("start_at", "end_at", "source_timestamp", "available_at")
                    }
                )
                for b in bars.bars
                if b.symbol == "AAPL"
            ]
        }
    )
    config = platform_strategy()
    p = platform_profile(data)
    assert run(config, p, data, [first, second]) == run(config, p, data, [second, first])
