"""Adversarial temporal/accounting review cases, independent of strategy-editor behavior."""

from datetime import datetime
from decimal import Decimal

import pytest

from app.backtesting.engine import simulate
from app.market_data.calendar import session_times
from app.market_data.view import DataView
from app.portfolio.ledger import Ledger
from app.schemas.domain import ProfileConfig, default_strategy

D = Decimal


def flat_fixture(data, count=4):
    return data.model_copy(
        update={
            "bars": [
                b.model_copy(
                    update={"open": D(100), "high": D(100), "low": D(100), "close": D(100)}
                )
                for b in data.bars[:count]
            ]
        }
    )


def usd_profile(data, **kwargs):
    return ProfileConfig(
        start_date=data.bars[0].session_date,
        end_date=data.bars[-1].session_date,
        account_currency="USD",
        fixed_fee="0",
        slippage="0",
        **kwargs,
    )


def replay(config, profile, data):
    return simulate(config, profile, data, benchmark=False, gross=False)


def test_open_fill_is_invariant_to_unpublished_same_session_volume(data):
    fixture = flat_fixture(data)
    profile = usd_profile(fixture)
    before = replay(default_strategy(), profile, fixture)
    changed = fixture.model_copy(
        update={
            "bars": [
                b.model_copy(update={"volume": D(0)}) if i == 1 else b
                for i, b in enumerate(fixture.bars)
            ]
        }
    )
    after = replay(default_strategy(), profile, changed)
    opening = session_times(fixture.bars[1].session_date)[0]

    def at_open(result):
        return [
            o
            for o in result["orders"]
            if o["executed_at"] and datetime.fromisoformat(o["executed_at"]) <= opening
        ]

    assert at_open(before) == at_open(after)


def two_positions(data):
    fixture = flat_fixture(data, count=5)
    original = fixture.bars
    # QQQ is acquired first; it can hit an intraday stop. SPY gaps through a stop.
    qqq = [
        b.model_copy(update={"symbol": "QQQ", "low": D(94) if i == 3 else D(100)})
        for i, b in enumerate(original)
    ]
    spy = [
        b.model_copy(update={"open": D(90), "high": D(90), "low": D(90), "close": D(90)})
        if i == 3
        else b
        for i, b in enumerate(original)
    ]
    return fixture.model_copy(update={"bars": qqq + spy}), original[3].session_date


def test_open_gap_exit_cannot_depend_on_another_assets_later_low(data):
    fixture, day = two_positions(data)
    profile = usd_profile(flat_fixture(data, count=5), symbols=["QQQ", "SPY"], max_orders_per_day=1)
    config = default_strategy()
    config.sizing.value = D("0.2")
    config.risk.stop_loss = D("0.05")
    before = replay(config, profile, fixture)
    changed = fixture.model_copy(
        update={
            "bars": [
                b.model_copy(update={"low": D(100)})
                if b.symbol == "QQQ" and b.session_date == day
                else b
                for b in fixture.bars
            ]
        }
    )
    after = replay(config, profile, changed)
    for result in (before, after):
        timestamps = [datetime.fromisoformat(e["timestamp"]) for e in result["ledger"]]
        assert timestamps == sorted(timestamps)
    opening = session_times(day)[0]

    def at_open(result):
        return [e for e in result["ledger"] if datetime.fromisoformat(e["timestamp"]) <= opening]

    assert at_open(before) == at_open(after)


@pytest.mark.parametrize("constraint", ["allocation", "exposure"])
def test_post_fee_equity_defines_allocation_limit(data, constraint):
    fixture = flat_fixture(data, count=2)
    fixture = fixture.model_copy(
        update={
            "bars": [
                fixture.bars[0],
                fixture.bars[1].model_copy(
                    update={
                        "open": D("101.5"),
                        "high": D("101.5"),
                        "low": D("101.5"),
                        "close": D("101.5"),
                    }
                ),
            ]
        }
    )
    profile = usd_profile(fixture).model_copy(update={"fixed_fee": D(100)})
    config = default_strategy()
    config.sizing.value = D("0.5")
    if constraint == "allocation":
        config.risk.max_allocation = D("0.5")
    else:
        profile.max_exposure = D("0.5")
    result = replay(config, profile, fixture)
    assert result["orders"][0]["status"] == "rejected"
    assert result["orders"][0]["rejection_reason"] == (
        "maximum asset allocation at execution"
        if constraint == "allocation"
        else "maximum portfolio exposure at execution"
    )


def test_known_take_profit_at_open_precedes_later_stop_range(data):
    fixture = flat_fixture(data, count=3)
    fixture = fixture.model_copy(
        update={
            "bars": [
                fixture.bars[0],
                fixture.bars[1],
                fixture.bars[2].model_copy(
                    update={"open": D(110), "high": D(110), "low": D(90), "close": D(100)}
                ),
            ]
        }
    )
    config = default_strategy()
    config.risk.stop_loss = config.risk.take_profit = D("0.05")
    result = replay(config, usd_profile(fixture), fixture)
    exits = [o for o in result["orders"] if o["side"] == "sell"]
    assert exits[0]["type"] == "take_profit"
    assert (
        datetime.fromisoformat(exits[0]["executed_at"])
        == session_times(fixture.bars[2].session_date)[0]
    )
    assert D(exits[0]["execution_price"]) == 105


def test_data_view_cannot_expose_a_future_session_with_bad_availability(data):
    current = data.bars[0].available_at
    malformed = data.bars[1].model_copy(update={"available_at": current})
    view = DataView([data.bars[0], malformed], current)
    assert [b.session_date for b in view.history("SPY")] == [data.bars[0].session_date]
    later_view = DataView([data.bars[0], malformed], data.bars[1].available_at)
    assert [b.session_date for b in later_view.history("SPY", through=current)] == [
        data.bars[0].session_date
    ]


def test_simulator_revalidates_input_timestamps_at_its_boundary(data):
    fixture = flat_fixture(data)
    malformed = fixture.model_copy(
        update={
            "bars": [
                fixture.bars[0],
                fixture.bars[1].model_copy(update={"available_at": fixture.bars[0].available_at}),
                *fixture.bars[2:],
            ]
        }
    )
    with pytest.raises(ValueError, match="precedes close"):
        replay(default_strategy(), usd_profile(fixture), malformed)


def test_ledger_rejects_unknown_side_without_mutation(data):
    ledger = Ledger(usd_profile(flat_fixture(data)))
    now = data.bars[0].available_at
    ledger.execute("SPY", "buy", D(1), D(100), D(1), now, 0)
    cash = ledger.cash
    with pytest.raises(ValueError, match="side"):
        ledger.execute("SPY", "invalid", D(1000), D(100), D(1), now, 1)
    assert ledger.cash == cash and ledger.positions["SPY"].quantity == 1


def test_total_loss_produces_valid_metrics_and_flat_zero_equity(data):
    fixture = flat_fixture(data, count=4)
    fixture = fixture.model_copy(
        update={
            "bars": [
                b.model_copy(
                    update={
                        "open": D(90) if i < 2 else D(10),
                        "high": D(90) if i < 2 else D(10),
                        "low": D(90) if i < 2 else D(10),
                        "close": D(90) if i < 2 else D(10),
                    }
                )
                for i, b in enumerate(fixture.bars)
            ]
        }
    )
    config = default_strategy()
    config.sizing.value = D(1)
    config.exit.value = True
    profile = usd_profile(fixture, starting_capital="100").model_copy(update={"fixed_fee": D(10)})
    result = replay(config, profile, fixture)
    assert D(result["metrics"]["ending_equity"]) == 0
    assert result["metrics"]["total_return"] == -1
    assert result["metrics"]["max_drawdown"] == -1
    assert result["metrics"]["daily_returns"][-2:] == [-1, 0]
    assert D(result["equity"][-1]["cash"]) == 0
