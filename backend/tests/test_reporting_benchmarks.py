from copy import deepcopy
from datetime import date
from decimal import Decimal

import pytest
from conftest import fixture_data
from test_workflow import prepared

from app.analytics.benchmarks import cash_benchmark
from app.backtesting.engine import simulate
from app.schemas.domain import ProfileConfig, default_strategy
from app.services.jobs import process_one


def test_cash_baseline_replays_only_recorded_deposits_without_early_credit_or_mutation():
    result = {
        "equity": [
            {"date": day, "timestamp": day + "T21:30:00+00:00"}
            for day in ["2020-01-31", "2020-02-03", "2020-02-04"]
        ],
        "ledger": [
            {"kind": "buy", "timestamp": "2020-01-31T14:30:00Z", "cash_delta": "-1000"},
            {
                "kind": "contribution",
                "timestamp": "2020-02-03T14:30:00Z",
                "cash_delta": "500.1234567891",
            },
            {"kind": "dividend_payment", "timestamp": "2020-02-03T14:30:00Z", "cash_delta": "3"},
            {"kind": "contribution", "timestamp": "2020-02-04T22:00:00Z", "cash_delta": "900"},
        ],
    }
    profile = {
        "starting_capital": "10000",
        "account_currency": "SGD",
        "monthly_contribution": "999",
    }
    original = deepcopy(result)
    cash = cash_benchmark(result, profile)
    assert [r["equity"] for r in cash["equity"]] == [
        "10000",
        "10500.1234567891",
        "10500.1234567891",
    ]
    assert cash["metrics"]["total_contributions"] == "500.1234567891"
    assert cash["metrics"]["absolute_pnl"] == "0"
    assert cash["metrics"]["total_return"] == 0
    assert result == original


def test_cash_baseline_stays_in_account_currency_and_ignores_trading_returns():
    data = fixture_data(date(2020, 1, 2), date(2020, 2, 4))
    profile = ProfileConfig(
        start_date=date(2020, 1, 2), end_date=date(2020, 2, 4), monthly_contribution="500"
    )
    result = simulate(default_strategy(), profile, data)
    cash = cash_benchmark(result, profile.model_dump(mode="json"))
    assert cash["currency"] == "SGD"
    assert Decimal(cash["equity"][0]["equity"]) == 10500
    assert Decimal(cash["equity"][-1]["equity"]) == 11000
    assert all(r["performance_equity"] == "10000" and r["drawdown"] == 0 for r in cash["equity"])
    assert cash["metrics"]["total_commissions"] == "0"


def test_cash_baseline_rejects_invalid_deposits():
    for amount in ["-1", "NaN", "Infinity"]:
        with pytest.raises(ValueError, match="positive deposits"):
            cash_benchmark(
                {
                    "equity": [],
                    "ledger": [
                        {
                            "kind": "contribution",
                            "timestamp": "2020-01-02T14:30:00Z",
                            "cash_delta": amount,
                        }
                    ],
                },
                {"starting_capital": "10000", "account_currency": "USD"},
            )


def test_intraday_cash_curve_credits_only_at_actual_deposit_clock():
    result = {
        "ledger": [
            {"kind": "contribution", "timestamp": "2020-02-03T14:30:00Z", "cash_delta": "500"}
        ],
        "equity": [{"date": "2020-02-03", "timestamp": "2020-02-03T21:00:00Z"}],
        "intraday_equity": [
            {"date": "2020-02-03", "timestamp": clock}
            for clock in ["2020-02-03T14:29:00Z", "2020-02-03T14:30:00Z", "2020-02-03T21:00:00Z"]
        ],
    }
    cash = cash_benchmark(result, {"starting_capital": "10000", "account_currency": "SGD"})
    assert [r["equity"] for r in cash["intraday_equity"]] == ["10000", "10500", "10500"]
    assert cash["equity"][-1]["equity"] == cash["intraday_equity"][-1]["equity"]
    result["intraday_equity"].reverse()
    with pytest.raises(ValueError, match="chronological"):
        cash_benchmark(result, {"starting_capital": "10000", "account_currency": "SGD"})


def test_cash_baseline_api_is_read_only_and_requires_completed_run(client, database, data):
    dataset, _, version, profile = prepared(client, data)
    run = client.post(
        "/api/backtests",
        json={
            "strategy_version_ids": [version["id"]],
            "profile_id": profile["id"],
            "dataset_id": dataset["id"],
            "acknowledge_synthetic": True,
        },
    ).json()[0]
    path = f"/api/research/runs/{run['id']}/cash-benchmark"
    assert client.get(path).status_code == 409
    process_one(database)
    original = client.get(f"/api/backtests/{run['id']}/results").json()
    cash = client.get(path)
    assert cash.status_code == 200, cash.text
    assert cash.json()["synthetic"] is True
    assert cash.json()["metrics"]["ending_equity"] == "10000"
    assert client.get(f"/api/backtests/{run['id']}/results").json() == original
