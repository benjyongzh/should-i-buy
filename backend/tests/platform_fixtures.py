from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from conftest import fixture_data

from app.market_data.calendar import session_times
from app.market_data.strategy_inputs import IntradayBar, StrategyInput
from app.schemas.domain import (
    ExecutionPolicy,
    ProfileConfig,
    TradingPolicy,
    TradingWindow,
    default_strategy,
)


def platform_data(start=date(2020, 1, 2), end=date(2020, 1, 3), symbols=("SPY",), minute=5):
    data = fixture_data(start, end)
    original = data.bars
    data.bars = [
        b.model_copy(
            update={
                "symbol": s,
                "open": Decimal(100),
                "high": Decimal(100),
                "low": Decimal(100),
                "close": Decimal(100),
            }
        )
        for s in symbols
        for b in original
    ]
    bars = []
    for daily in data.bars:
        opening, closing = session_times(daily.session_date)
        clock = opening
        while clock < closing:
            end_at = min(clock + timedelta(minutes=minute), closing)
            bars.append(
                IntradayBar(
                    **{
                        **daily.model_dump(),
                        "start_at": clock,
                        "end_at": end_at,
                        "available_at": end_at,
                        "source_timestamp": end_at,
                    }
                )
            )
            clock = end_at
    source = StrategyInput(
        kind="intraday",
        name="SYNTHETIC intraday financial fixture",
        source="synthetic fixture",
        source_url="https://fixture.invalid/bars",
        availability_policy="SYNTHETIC completed bars available exactly at interval end",
        synthetic=True,
        complete=True,
        reviewed=True,
        parent_id="SYNTHETIC-fixture-review",
        parent_hash="a" * 64,
        review_note="Explicit SYNTHETIC test fixture review, not real source certification.",
        coverage_start=session_times(start)[0],
        coverage_end=session_times(end)[1],
        symbols=list(symbols),
        bar_minutes=minute,
        bars=bars,
    )
    return data, source


def platform_profile(data, minute=5, **kwargs):
    return ProfileConfig(
        start_date=min(b.session_date for b in data.bars),
        end_date=max(b.session_date for b in data.bars),
        symbols=sorted({b.symbol for b in data.bars}),
        account_currency="USD",
        fixed_fee="0",
        slippage="0",
        timeframe=f"{minute}min" if minute else "1d",
        **kwargs,
    )


def platform_strategy(window=0):
    config = default_strategy()
    config.sizing.mode = "fixed_notional"
    config.sizing.value = Decimal(1000)
    config.trading = TradingPolicy(entry_schedule="once")
    config.execution_policy = ExecutionPolicy(
        decision_cadence="bar_close",
        default_timeframe="intraday",
        entry_window=TradingWindow(start_minutes_after_open=window),
    )
    return config


def universe_source(symbols, **changes):
    body = dict(
        kind="universe",
        name="SYNTHETIC historical universe",
        source="fixture",
        source_url="https://fixture.invalid/universe",
        availability_policy="SYNTHETIC event-sourced membership and sector publications",
        synthetic=True,
        complete=True,
        reviewed=True,
        parent_id="SYNTHETIC-fixture-review",
        parent_hash="a" * 64,
        review_note="Explicit SYNTHETIC test fixture review, not real source certification.",
        coverage_start=datetime(2010, 1, 1, tzinfo=UTC),
        coverage_end=datetime(2030, 1, 1, tzinfo=UTC),
        symbols=list(symbols),
        states=[
            dict(
                symbol=s,
                instrument_id=s + "-id",
                effective_at="2010-01-01T00:00:00Z",
                available_at="2010-01-01T00:00:00Z",
                listed=True,
                sector="Technology" if s in {"AAPL", "MSFT"} else "Healthcare",
                source_url="https://fixture.invalid/security",
            )
            for s in symbols
        ],
    )
    return StrategyInput.model_validate({**body, **changes})


def event_source(events, stream="NEWS", **changes):
    body = dict(
        kind="events",
        name="SYNTHETIC events",
        source="fixture",
        source_url="https://fixture.invalid/events",
        availability_policy="SYNTHETIC original-version publication plus score derivation availability",
        synthetic=True,
        complete=True,
        reviewed=True,
        parent_id="SYNTHETIC-fixture-review",
        parent_hash="a" * 64,
        review_note="Explicit SYNTHETIC test fixture review, not real source certification.",
        coverage_start=datetime(2010, 1, 1, tzinfo=UTC),
        coverage_end=datetime(2030, 1, 1, tzinfo=UTC),
        symbols=["SPY", "AAPL", "MSFT", "CVS"],
        stream_id=stream,
        events=events,
    )
    return StrategyInput.model_validate({**body, **changes})


def event(event_id="one", clock="2020-01-02T15:30:00Z", **changes):
    body = dict(
        event_id=event_id,
        published_at=clock,
        available_at=clock,
        category="news",
        symbols=["SPY"],
        title="SYNTHETIC archived headline",
        source_url="https://fixture.invalid/article",
        original_content_hash="a" * 64,
        derivation="SYNTHETIC source classification",
    )
    return {**body, **changes}
