from datetime import date, datetime
from decimal import Decimal

import pytest

from app.backtesting.engine import simulate
from app.market_data.calendar import session_times
from app.portfolio.ledger import Ledger
from app.schemas.domain import ProfileConfig, default_strategy

D = Decimal


def profile_for(data, **kwargs):
    return ProfileConfig(
        start_date=data.bars[0].session_date, end_date=data.bars[-1].session_date, **kwargs
    )


def test_next_open_determinism_and_duplicate_prevention(data):
    config = default_strategy()
    profile = profile_for(data)
    first = simulate(config, profile, data)
    assert first == simulate(config, profile, data)
    filled = [o for o in first["orders"] if o["status"] == "filled"]
    assert len(filled) == 1
    assert (
        datetime.fromisoformat(filled[0]["executed_at"])
        == session_times(data.bars[1].session_date)[0]
    )
    assert D(first["metrics"]["total_commissions"]) == D("2.50")
    assert D(first["equity"][-1]["equity"]) >= D(first["equity"][-1]["cash"])


def test_future_mutation_invariance_mandatory(data):
    cutoff = date(2020, 3, 31)
    config = default_strategy()
    config.entry = __import__("app.schemas.domain", fromlist=["Compare"]).Compare(
        type="compare",
        op="crosses_above",
        left={"type": "price"},
        right={"type": "indicator", "name": "sma", "period": 5},
    )
    before = simulate(config, profile_for(data), data)
    mutated = data.model_copy(
        update={
            "bars": [
                b.model_copy(
                    update={
                        "open": b.open * 5,
                        "high": b.high * 5,
                        "low": b.low * 5,
                        "close": b.close * 5,
                    }
                )
                if b.session_date > cutoff
                else b
                for b in data.bars
            ]
        }
    )
    after = simulate(config, profile_for(data), mutated)
    for key, timestamp in [("signals", "timestamp"), ("equity", "date")]:
        assert [r for r in before[key] if r[timestamp][:10] <= str(cutoff)] == [
            r for r in after[key] if r[timestamp][:10] <= str(cutoff)
        ]
    assert [
        o for o in before["orders"] if o["executed_at"] and o["executed_at"][:10] <= str(cutoff)
    ] == [o for o in after["orders"] if o["executed_at"] and o["executed_at"][:10] <= str(cutoff)]


def test_round_trip_fees_cash_and_pnl(data):
    profile = profile_for(data, slippage="0", fx_markup="0.01", commission_pct="0.001")
    ledger = Ledger(profile)
    now = data.bars[0].available_at
    buy = ledger.execute("SPY", "buy", D(10), D(100), D("1.35"), now, 0)
    assert ledger.cash == D(10000) + D(buy["cash_delta"])
    sell = ledger.execute("SPY", "sell", D(10), D(110), D("1.4"), now, 4)
    assert ledger.cash == D(10000) + D(buy["cash_delta"]) + D(sell["cash_delta"])
    assert ledger.realized_pnl == ledger.cash - D(10000)
    assert ledger.fees == D("2.50") * 2 + (D(1350) + D(1540)) * D("0.001")
    assert ledger.trades[0]["holding_sessions"] == 4
    with pytest.raises(ValueError, match="insufficient cash"):
        ledger.execute("SPY", "buy", D(10000), D(100), D("1.35"), now, 5)


def test_flat_no_trade_metrics(data):
    config = default_strategy()
    config.entry.value = False
    result = simulate(config, profile_for(data), data)
    assert result["metrics"]["total_return"] == 0
    assert result["metrics"]["sharpe_ratio"] is None
    assert result["metrics"]["win_rate"] is None
    assert all(D(row["equity"]) == 10000 for row in result["equity"])


def test_historical_fx_changes_valuation(data):
    ledger = Ledger(profile_for(data, fixed_fee="0", slippage="0"))
    ledger.execute("SPY", "buy", D(10), D(100), D(1), data.bars[0].available_at, 0)
    assert ledger.equity({"SPY": D(100)}, D("1.4")) == D(10400)


def test_split_preserves_quantity_cost_basis_and_equity(data):
    ledger = Ledger(profile_for(data, fixed_fee="0", slippage="0"))
    ledger.execute("SPY", "buy", D(10), D(100), D(1), data.bars[0].available_at, 0)
    ledger.split("SPY", D(2), data.bars[1].available_at)
    assert ledger.positions["SPY"].quantity == 20
    assert ledger.positions["SPY"].cost_basis == 1000
    assert ledger.equity({"SPY": D(50)}, D(1)) == 10000


def test_stop_first_and_gap_policy(data):
    short = data.model_copy(update={"bars": data.bars[:3], "fx": data.fx[:3]})
    bars = [
        b.model_copy(update={"open": D(100), "close": D(100), "high": D(110), "low": D(90)})
        for b in short.bars
    ]
    short = short.model_copy(update={"bars": bars})
    config = default_strategy()
    config.risk.stop_loss, config.risk.take_profit = D("0.05"), D("0.05")
    result = simulate(config, profile_for(short, slippage="0"), short)
    stops = [o for o in result["orders"] if o["type"] == "stop_loss"]
    assert stops and D(stops[0]["execution_price"]) == 95
    bars[1] = bars[1].model_copy(update={"open": D(90)})
    # New positions use their actual execution price; test existing position's gap on day three.
    config.risk.take_profit = None
    bars[1] = bars[1].model_copy(update={"open": D(100), "low": D(99), "high": D(101)})
    bars[2] = bars[2].model_copy(
        update={"open": D(80), "low": D(79), "close": D(85), "high": D(86)}
    )
    result = simulate(
        config, profile_for(short, slippage="0"), short.model_copy(update={"bars": bars})
    )
    stop = next(o for o in result["orders"] if o["type"] == "stop_loss")
    assert D(stop["execution_price"]) == 80
