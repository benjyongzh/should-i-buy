"""Financial, causal and reproducibility acceptance of opt-in funding and sizing."""

from datetime import date, datetime, timedelta
from decimal import Decimal, localcontext

import pytest
from conftest import fixture_data

from app.analytics.cashflows import investor_return, normalize
from app.analytics.periods import period_report
from app.backtesting.engine import simulate
from app.backtesting.trading import scheduled
from app.market_data.calendar import session_times
from app.portfolio.ledger import Ledger
from app.schemas.domain import (
    Action,
    ProfileConfig,
    StrategyConfig,
    TradingPolicy,
    canonical_hash,
    default_strategy,
)
from app.services.jobs import process_one

D = Decimal


def profile(data, **kw):
    return ProfileConfig(
        start_date=data.bars[0].session_date,
        end_date=data.bars[-1].session_date,
        account_currency="USD",
        fixed_fee="0",
        slippage="0",
        **kw,
    )


def strategy(mode="fixed_notional", value="100", **policy):
    config = default_strategy()
    config.sizing.mode = mode
    config.sizing.value = D(value)
    config.trading = TradingPolicy(**policy)
    return config


def flat_data(start=date(2020, 1, 2), end=date(2020, 3, 6)):
    data = fixture_data(start, end)
    data.bars = [
        b.model_copy(update={"open": D(100), "high": D(100), "low": D(100), "close": D(100)})
        for b in data.bars
    ]
    return data


def run(config, p, data, benchmark=False, gross=False):
    return simulate(config, p, data, benchmark=benchmark, gross=gross)


def test_legacy_serialization_and_validation():
    config = default_strategy()
    raw = config.model_dump(mode="json")
    assert "trading" not in raw
    assert StrategyConfig.model_validate(raw).model_dump(mode="json") == raw
    p = ProfileConfig()
    assert "monthly_contribution" not in p.model_dump(mode="json")
    assert canonical_hash(p.model_dump(mode="json")) == canonical_hash(
        ProfileConfig(monthly_contribution="0").model_dump(mode="json")
    )
    for value in ("-1", "NaN", "Infinity"):
        with pytest.raises(ValueError):
            ProfileConfig(monthly_contribution=value)
    with pytest.raises(ValueError, match="require a trading"):
        StrategyConfig.model_validate({**raw, "sizing": {"mode": "cash_percent", "value": "1"}})
    with pytest.raises(ValueError):
        TradingPolicy(exit_fraction=0)


def test_funding_calendar_no_retroactive_midmonth_and_no_profit():
    data = flat_data()
    config = default_strategy()
    config.entry.value = False
    p = profile(data, monthly_contribution="500")
    result = run(config, p, data, benchmark=True, gross=True)
    flows = [e for e in result["ledger"] if e["kind"] == "contribution"]
    assert [datetime.fromisoformat(e["timestamp"]).date() for e in flows] == [
        date(2020, 1, 2),
        date(2020, 2, 3),
        date(2020, 3, 2),
    ]
    assert result["metrics"]["total_contributions"] == "1500"
    assert D(result["metrics"]["ending_equity"]) == 11500
    assert D(result["metrics"]["absolute_pnl"]) == 0
    assert (
        result["metrics"]["total_return"]
        == result["metrics"]["max_drawdown"]
        == result["metrics"]["gross_return"]
        == 0
    )
    assert result["benchmark"]["metrics"]["total_contributions"] == "1500"
    report = period_report(result, p.model_dump(mode="json"), "month")
    assert all(D(row["return"]) == D(row["pnl"]) == 0 for row in report)
    assert sum(D(row["contributions"]) for row in report) == 1500
    p.start_date = date(2020, 1, 15)
    result = run(config, p, data)
    assert result["metrics"]["total_contributions"] == "1000"
    assert scheduled("monthly", date(2020, 9, 1))
    assert scheduled("weekly", date(2020, 9, 8))  # Labor Day holiday
    assert not scheduled("monthly", date(2020, 9, 8))


def test_monthly_dca_and_once_timing():
    data = flat_data()
    p = profile(data, monthly_contribution="500")
    config = strategy(entry_schedule="monthly", allow_additions=True)
    result = run(config, p, data)
    buys = [e for e in result["ledger"] if e["kind"] == "buy"]
    assert [datetime.fromisoformat(e["timestamp"]).date() for e in buys] == [
        date(2020, 1, 3),
        date(2020, 2, 4),
        date(2020, 3, 3),
    ]
    assert result["positions"]["SPY"]["quantity"] == "3"
    assert result == run(config, p, data)
    config.trading.entry_schedule = "once"
    once = run(config, p, data)
    assert len([e for e in once["ledger"] if e["kind"] == "buy"]) == 1
    assert D(once["positions"]["SPY"]["quantity"]) == 1


def test_contribution_cannot_change_previously_submitted_quantity():
    data = flat_data(date(2020, 1, 30), date(2020, 2, 4))
    config = strategy("cash_percent", "1", allow_additions=True)
    result = run(config, profile(data, monthly_contribution="1000"), data)
    buys = [e for e in result["ledger"] if e["kind"] == "buy"]
    assert D(buys[0]["quantity"]) == 100
    assert datetime.fromisoformat(buys[0]["timestamp"]).date() == date(2020, 1, 31)
    assert D(buys[1]["quantity"]) == 10
    assert datetime.fromisoformat(buys[1]["timestamp"]).date() == date(2020, 2, 4)


def test_topups_partial_sales_basis_fx_and_split_conservation():
    data = flat_data()
    p = profile(data, max_positions=1)
    p.fixed_fee = D("2.50")
    ledger = Ledger(p)
    now = data.bars[0].available_at
    ledger.execute("SPY", "buy", D(10), D(100), D("1.3"), now, 0)
    ledger.execute("SPY", "buy", D(5), D(120), D("1.4"), now, 1, allow_adjustments=True)
    assert ledger.positions["SPY"].cost_basis == D(2145)
    assert ledger.positions["SPY"].entry_price == D(1600) / 15
    ledger.split("SPY", D("1.5"), now)
    ledger.dividend("SPY", D(1), date(2020, 1, 3), now)
    assert ledger.receivables[0]["amount_usd"] == D("22.5")
    ledger.execute("SPY", "sell", D(6), D(80), D("1.5"), now, 2, allow_adjustments=True)
    assert D(ledger.trades[0]["cost_basis"]) == 572
    assert D(ledger.trades[0]["realized_pnl"]) == D("145.50")
    ledger.settle_dividends(date(2020, 1, 3), D("1.4"), now)
    ledger.execute("SPY", "sell", D("16.5"), D(80), D("1.5"), now, 3, allow_adjustments=True)
    assert sum(D(t["cost_basis"]) for t in ledger.trades) == 2145
    assert not ledger.positions
    assert ledger.cash - p.starting_capital == ledger.realized_pnl + D("31.50")


def test_legacy_ledger_rejects_topup_and_partial_exit():
    data = flat_data()
    ledger = Ledger(profile(data))
    args = (D(100), D(1), data.bars[0].available_at, 0)
    ledger.execute("SPY", "buy", D(2), *args)
    with pytest.raises(ValueError, match="duplicate"):
        ledger.execute("SPY", "buy", D(1), *args)
    with pytest.raises(ValueError, match="entire"):
        ledger.execute("SPY", "sell", D(1), *args)


def test_target_allocation_trims_without_additions_and_exit_priority():
    data = flat_data(end=date(2020, 1, 10))
    for bar in data.bars[2:]:
        bar.open = bar.high = bar.low = bar.close = D(200)
    config = strategy("target_allocation", ".5")
    result = run(config, profile(data), data)
    assert D(result["positions"]["SPY"]["quantity"]) == 38
    sells = [e for e in result["ledger"] if e["kind"] == "sell"]
    assert D(sells[0]["quantity"]) == 12
    config.exit.value = True
    config.trading.exit_fraction = D(".5")
    partial = run(config, profile(data), data)
    first_exit = next(e for e in partial["ledger"] if e["kind"] == "sell")
    assert D(first_exit["quantity"]) == 25
    assert partial["orders"][1]["reason"] == "scheduled partial/full exit"


def test_topups_obey_cumulative_allocation_and_position_limits():
    data = flat_data(end=date(2020, 1, 15))
    config = strategy("equity_percent", ".3", allow_additions=True)
    config.risk.max_allocation = D(".5")
    config.risk.max_positions = 1
    result = run(config, profile(data, max_positions=1), data)
    assert result["positions"]["SPY"]["quantity"] == "50"
    assert len([e for e in result["ledger"] if e["kind"] == "buy"]) == 2
    # A gap can make an individually valid addition violate the cumulative cap.
    data.bars[2].open = data.bars[2].high = data.bars[2].close = D(200)
    gapped = run(config, profile(data), data)
    assert gapped["orders"][1]["status"] == "rejected"
    assert "allocation" in gapped["orders"][1]["rejection_reason"]


def test_min_holding_blocks_partial_exit_since_latest_addition_not_buys():
    data = flat_data(end=date(2020, 1, 10))
    config = strategy(allow_additions=True)
    p = profile(data, min_holding_sessions=3)
    result = run(config, p, data)
    assert len([e for e in result["ledger"] if e["kind"] == "buy"]) == len(data.bars) - 1


def test_cashflow_linking_overnight_fx_gap_and_drawdown():
    curve = [
        {"equity": "80", "external_flow": "0"},
        {
            "equity": "220",
            "external_flow": "100",
            "equity_before_flow": "100",
            "equity_after_flow": "200",
        },
    ]
    with localcontext() as ctx:
        ctx.prec = 34
        values = normalize(curve, D(100))
    assert values == [D(100), D(80), D(110)]  # +25% overnight, then +10%; deposit earns neither
    data = flat_data(end=date(2020, 2, 5))
    for bar in data.bars[2:]:
        bar.open = bar.high = bar.low = bar.close = D(50)
    config = strategy("target_allocation", "1", entry_schedule="once")
    result = run(config, profile(data, monthly_contribution="10000"), data)
    assert result["metrics"]["max_drawdown"] == -0.5
    assert result["metrics"]["total_return"] == -0.5
    assert D(result["metrics"]["absolute_pnl"]) == -10000
    assert D(result["metrics"]["ending_equity"]) == 20000
    periods = period_report(
        result, profile(data, monthly_contribution="10000").model_dump(mode="json"), "month"
    )
    assert D(periods[1]["pnl"]) == D(periods[1]["return"]) == 0


def test_zero_equity_recapitalization_does_not_erase_total_loss():
    rows = [
        {"equity": "0", "external_flow": "0"},
        {
            "equity": "100",
            "external_flow": "100",
            "equity_before_flow": "0",
            "equity_after_flow": "100",
        },
    ]
    assert normalize(rows, D(100)) == [D(100), D(0), D(0)]
    with pytest.raises(ValueError, match="unexplained"):
        normalize(
            [{"equity": "0", "external_flow": "0"}, {"equity": "10", "external_flow": "0"}], D(100)
        )


def test_money_weighted_return_known_root_and_short_horizon():
    start = session_times(date(2020, 1, 2))[0]
    end = start + timedelta(days=365)
    curve = [{"date": "2020-01-02", "timestamp": end.isoformat(), "equity": "1210"}]
    events = [{"kind": "contribution", "timestamp": start.isoformat(), "cash_delta": "100"}]
    assert investor_return(curve, events, D(1000)) == pytest.approx(0.1)
    curve[0]["timestamp"] = (end - timedelta(days=1)).isoformat()
    assert investor_return(curve, events, D(1000)) is None


def test_funded_partial_strategy_future_mutation_isolation_and_reproducibility():
    data = flat_data()
    config = strategy("cash_percent", ".2", allow_additions=True, exit_fraction=".25")
    p = profile(data, monthly_contribution="500")
    before = run(config, p, data, benchmark=True, gross=True)
    mutated = data.model_copy(deep=True)
    cutoff = date(2020, 2, 3)
    for b in mutated.bars:
        if b.session_date > cutoff:
            b.open *= 3
            b.close *= 3
            b.low *= 3
            b.high *= 3
    for fx in mutated.fx:
        if fx.available_at.date() > cutoff:
            fx.rate *= 2
    after = run(config, p, mutated, benchmark=True, gross=True)
    for key in ("equity", "signals", "ledger"):
        stamp = "date" if key == "equity" else "timestamp"
        assert [r for r in before[key] if r[stamp][:10] <= str(cutoff)] == [
            r for r in after[key] if r[stamp][:10] <= str(cutoff)
        ]
    assert before == run(config, p, data, benchmark=True, gross=True)


def test_dividend_entitlement_precedes_same_open_contribution_and_buy():
    data = flat_data(date(2020, 1, 30), date(2020, 2, 5))
    ex = date(2020, 2, 3)
    data.actions = [
        Action(
            symbol="SPY",
            kind="dividend",
            session_date=ex,
            value="1",
            payment_date=date(2020, 2, 4),
            available_at=session_times(ex)[0] - timedelta(days=1),
        )
    ]
    result = run(strategy(allow_additions=True), profile(data, monthly_contribution="500"), data)
    entitlement = next(e for e in result["ledger"] if e["kind"] == "dividend_entitlement")
    assert D(entitlement["amount_usd"]) == 1  # Jan31 holding only, not Feb3 addition
    contribution = next(e for e in result["ledger"] if e["kind"] == "contribution")
    assert D(contribution["equity_before_flow"]) == 10001


def test_funded_profile_snapshot_publication_worker_and_exact_repeat(client, database):
    data = flat_data(end=date(2020, 2, 5))
    dataset = client.post("/api/market-data/import", json=data.model_dump(mode="json")).json()
    config = strategy("cash_percent", ".2", entry_schedule="monthly", allow_additions=True)
    draft = client.post(
        "/api/strategies",
        json={"name": "SYNTHETIC funding acceptance", "config": config.model_dump(mode="json")},
    ).json()
    assert client.get(f"/api/strategies/{draft['id']}/versions").json() == []
    version = client.post(
        f"/api/strategies/{draft['id']}/publish", json={"expected_revision": 1}
    ).json()
    p = profile(data, monthly_contribution="500")
    saved = client.post(
        "/api/backtest-profiles",
        json={"name": "SYNTHETIC funded profile", "config": p.model_dump(mode="json")},
    ).json()
    body = {
        "strategy_version_ids": [version["id"]],
        "profile_id": saved["id"],
        "dataset_id": dataset["id"],
        "acknowledge_synthetic": True,
    }
    first = client.post("/api/backtests", json=body).json()[0]
    assert first["profile_snapshot"]["monthly_contribution"] == "500"
    # A later profile edit cannot alter queued snapshots or their hash.
    p.monthly_contribution = D(900)
    assert (
        client.patch(
            f"/api/backtest-profiles/{saved['id']}",
            json={"name": saved["name"], "config": p.model_dump(mode="json")},
        ).status_code
        == 200
    )
    assert process_one(database) == first["id"]
    status = client.get(f"/api/backtests/{first['id']}").json()
    assert status["status"] == "completed", status
    result = client.get(f"/api/backtests/{first['id']}/results").json()
    assert result["metrics"]["total_contributions"] == "1000"
    p.monthly_contribution = D(500)
    client.patch(
        f"/api/backtest-profiles/{saved['id']}",
        json={"name": saved["name"], "config": p.model_dump(mode="json")},
    )
    second = client.post("/api/backtests", json=body).json()[0]
    assert first["provenance"]["profile_hash"] == second["provenance"]["profile_hash"]
    assert process_one(database) == second["id"]
    assert client.get(f"/api/backtests/{second['id']}/results").json() == result
    assert client.get(f"/api/strategy-versions/{version['id']}").json()[
        "config"
    ] == config.model_dump(mode="json")
