from copy import deepcopy
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.backtesting.engine import simulate
from app.market_data.calendar import session_times
from app.market_data.features import FeatureBook, FeaturePoint, FeatureSeries, decision_pair
from app.models.entities import ContextSnapshot
from app.schemas.domain import (
    MACD,
    Action,
    Compare,
    External,
    Negate,
    ProfileConfig,
    Stochastic,
    StrategyConfig,
    canonical_hash,
    default_strategy,
)
from app.services.feature_inputs import frozen_features, resolve_features
from app.services.jobs import process_one
from app.strategies.interpreter import condition, numeric
from tests.test_workflow import prepared

D = Decimal


def feature_rule(op="gt", age=366):
    config = default_strategy()
    config.sizing.value = D("0.95")
    config.entry = Compare(
        type="compare",
        op=op,
        left=External(type="external", series_id="FEAR_GREED_US", max_age_days=age),
        right={"type": "constant", "value": 50},
    )
    return config


def feature_source():
    points = [
        FeaturePoint(observation_date="2019-12-31", available_at="2019-12-31T21:30:00Z", value=20),
        FeaturePoint(observation_date="2020-01-02", available_at="2020-01-03T21:31:00Z", value=80),
    ]
    return FeatureSeries(
        series_id="FEAR_GREED_US",
        content_hash=canonical_hash({"points": [p.model_dump(mode="json") for p in points]}),
        synthetic=True,
        points=points,
    )


def test_macd_explicit_seed_and_component_warmup(data):
    bars = [b.model_copy(update={"close": D(i + 1)}) for i, b in enumerate(data.bars[:8])]
    line = MACD(type="macd", fast_period=2, slow_period=3, signal_period=2, component="line")
    signal = line.model_copy(update={"component": "signal"})
    histogram = line.model_copy(update={"component": "histogram"})
    # On a linear sequence, the two independently SMA-seeded EMAs differ by 0.5.
    assert numeric(line, bars[:2]) is None
    assert numeric(line, bars[:3]) == D("0.5")
    assert numeric(signal, bars[:3]) is None
    assert numeric(signal, bars[:4]) == D("0.5")
    assert numeric(histogram, bars) == 0
    assert (
        condition(
            Negate(
                type="not",
                condition=Compare(
                    type="compare", op="gt", left=signal, right={"type": "constant", "value": 0}
                ),
            ),
            bars[:3],
        )
        is None
    )


def test_macd_nonlinear_hand_calculation_and_crossover(data):
    bars = [
        b.model_copy(update={"close": D(value)})
        for b, value in zip(data.bars, [1, 2, 4, 8, 16], strict=False)
    ]
    line = MACD(type="macd", fast_period=2, slow_period=3, signal_period=2, component="line")
    # SMA seeds: fast=1.5, slow=7/3. Fast at t3=19/6, t4=115/18;
    # slow at t4=31/6. MACD t3=5/6, t4=11/9, signal t4=37/36.
    assert abs(numeric(line, bars[:4]) - D(11) / 9) < D("1e-24")
    assert abs(numeric(line.model_copy(update={"component": "signal"}), bars[:4]) - D(37) / 36) < D(
        "1e-24"
    )
    assert abs(
        numeric(line.model_copy(update={"component": "histogram"}), bars[:4]) - D(7) / 36
    ) < D("1e-24")
    assert (
        condition(
            Compare(
                type="compare",
                op="crosses_above",
                left=line,
                right={"type": "constant", "value": 1},
            ),
            bars[:4],
        )
        is True
    )


@pytest.mark.parametrize(
    "component,required,expected", [("k", 4, D(800) / 11), ("d", 5, D(700) / 11)]
)
def test_stochastic_smoothing_hand_calculation_and_warmup(data, component, required, expected):
    bars = [
        b.model_copy(update={"close": D(value), "high": D(12), "low": D(1)})
        for b, value in zip(data.bars, [2, 4, 6, 8, 10], strict=False)
    ]
    node = Stochastic(type="stochastic", period=3, smooth_k=2, smooth_d=2, component=component)
    assert numeric(node, bars[: required - 1]) is None
    assert abs(numeric(node, bars) - expected) < D("1e-24")
    flat = [
        b.model_copy(update={"open": D(10), "close": D(10), "high": D(10), "low": D(10)})
        for b in bars
    ]
    assert numeric(node, flat) == 50


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "macd", "fast_period": 26, "slow_period": 12},
        {"type": "macd", "signal_period": 0},
        {"type": "stochastic", "smooth_k": 0},
        {"type": "stochastic", "period": 501},
        {"type": "external", "series_id": "../secret", "max_age_days": 7},
        {"type": "external", "series_id": "VIX", "max_age_days": 0},
    ],
)
def test_new_operands_are_declarative_and_bounded(payload):
    config = default_strategy().model_dump(mode="json")
    config["entry"] = {
        "type": "compare",
        "op": "gt",
        "left": payload,
        "right": {"type": "constant", "value": 0},
    }
    with pytest.raises(ValidationError):
        StrategyConfig.model_validate(config)


def test_legacy_default_configuration_hash_does_not_change():
    assert (
        canonical_hash(default_strategy().model_dump(mode="json"))
        == "0665ea2e5c28d0456e35dee8fe9d307b1cbed35011690f989f985d239997ccd5"
    )


def test_external_publication_gating_previous_clock_and_missing_stale_errors():
    book = FeatureBook([feature_source()])
    now = datetime(2020, 1, 3, 21, 30, tzinfo=UTC)
    before = book.materialize(now, datetime(2020, 1, 2, 21, 30, tzinfo=UTC))
    assert before.value("FEAR_GREED_US", 7) == 20
    after = book.materialize(now + timedelta(minutes=1), now)
    assert after.value("FEAR_GREED_US", 7) == 80
    assert after.value("FEAR_GREED_US", 7, 1) == 20
    with pytest.raises(ValueError, match="No published"):
        before.value("VIX", 7)
    with pytest.raises(ValueError, match="Stale"):
        book.materialize(now + timedelta(days=20), now).value("FEAR_GREED_US", 7)
    with pytest.raises(ValueError, match="Future"):
        book.materialize(now, now + timedelta(seconds=1))


def test_late_old_observation_does_not_replace_newer_known_observation():
    source = feature_source().model_copy(
        update={
            "points": [
                FeaturePoint(
                    observation_date="2020-01-02", available_at="2020-01-06T20:00:00Z", value=10
                ),
                FeaturePoint(
                    observation_date="2020-01-03", available_at="2020-01-03T20:00:00Z", value=90
                ),
            ]
        }
    )
    view = FeatureBook([source]).materialize(
        datetime(2020, 1, 6, 21, tzinfo=UTC), datetime(2020, 1, 3, 21, tzinfo=UTC)
    )
    assert view.value("FEAR_GREED_US", 7) == 90
    assert view.value("FEAR_GREED_US", 7, 1) == 90


def test_external_crossovers_compare_previous_decision_not_previous_release(data):
    source = feature_source()
    current, previous = decision_pair(date(2020, 1, 6), "close_plus_30m")
    view = FeatureBook([source]).materialize(current, previous)
    assert condition(feature_rule("crosses_above").entry, data.bars[:3], view) is True
    tomorrow = FeatureBook([source]).materialize(*decision_pair(date(2020, 1, 7), "close_plus_30m"))
    assert condition(feature_rule("crosses_above").entry, data.bars[:4], tomorrow) is False


def test_mixed_crossover_does_not_use_late_bar_in_previous_comparison_leg(data):
    current, previous = decision_pair(data.bars[2].session_date, "close_plus_30m")
    source = feature_source().model_copy(
        update={
            "points": [
                FeaturePoint(
                    observation_date="2019-12-31", available_at="2019-12-31T21:30:00Z", value=50
                )
            ]
        }
    )
    view = FeatureBook([source]).materialize(current, previous)
    bars = [
        data.bars[0].model_copy(update={"close": D(40)}),
        data.bars[1].model_copy(update={"close": D(100), "available_at": current}),
        data.bars[2].model_copy(update={"close": D(60)}),
    ]
    rule = Compare(
        type="compare",
        op="crosses_above",
        left={"type": "price", "field": "close"},
        right={"type": "external", "series_id": "FEAR_GREED_US", "max_age_days": 7},
    )
    assert (
        condition(rule, bars, view) is True
    )  # Previous known close was 40, not late-reported 100.


def test_external_signals_fill_next_open_with_independently_checked_sgd_costs(data):
    profile = ProfileConfig(
        start_date=data.bars[0].session_date, end_date=data.bars[10].session_date
    )
    result = simulate(feature_rule(), profile, data, feature_data=[feature_source()])
    buy = next(e for e in result["ledger"] if e["kind"] == "buy")
    assert buy["timestamp"] == session_times(date(2020, 1, 7))[0].isoformat()
    assert buy["quantity"] == "70"
    # 70 * (100 * 1.0005) * 1.35 + 2.50 = SGD 9,457.225 debit.
    assert D(buy["cash_after"]) == D("542.775")
    assert D(buy["price_usd"]) == D("100.05")
    assert all(D(e["cash_after"]) >= 0 for e in result["ledger"] if "cash_after" in e)
    assert result["metrics"]["gross_return"] is not None
    first = next(s for s in result["signals"] if s["action"] == "buy")
    assert (
        first["external_inputs"]["FEAR_GREED_US"]["current"]["available_at"]
        == "2020-01-03T21:31:00+00:00"
    )
    zero = profile.model_copy(
        update={
            "fixed_fee": D(0),
            "slippage": D(0),
            "commission_pct": D(0),
            "fx_markup": D(0),
            "spread": D(0),
        }
    )
    independent_gross = simulate(
        feature_rule(), zero, data, benchmark=False, gross=False, feature_data=[feature_source()]
    )
    assert result["metrics"]["gross_return"] == independent_gross["metrics"]["total_return"]


def test_mixed_split_day_cross_uses_prices_adjusted_at_each_actual_decision(data):
    bars = [
        b.model_copy(update={k: D(120 if i < 2 else 60) for k in ("open", "high", "low", "close")})
        for i, b in enumerate(data.bars[:5])
    ]
    action = Action(
        symbol="SPY",
        session_date=bars[2].session_date,
        available_at=session_times(bars[2].session_date)[0],
        kind="split",
        value=2,
    )
    fixture = data.model_copy(update={"bars": bars, "actions": [action]})
    source = feature_source().model_copy(
        update={
            "points": [
                FeaturePoint(
                    observation_date="2019-12-31", available_at="2019-12-31T21:30:00Z", value=100
                )
            ]
        }
    )
    config = feature_rule("crosses_below")
    payload = config.model_dump(mode="json")
    payload["entry"]["left"] = {"type": "price", "field": "close"}
    payload["entry"]["right"] = {
        "type": "external",
        "series_id": "FEAR_GREED_US",
        "max_age_days": 14,
    }
    config = StrategyConfig.model_validate(payload)
    profile = ProfileConfig(start_date=bars[0].session_date, end_date=bars[-1].session_date)
    result = simulate(config, profile, fixture, feature_data=[source])
    signal = next(s for s in result["signals"] if s["action"] == "buy")
    assert (
        signal["timestamp"]
        == decision_pair(bars[2].session_date, fixture.decision_time)[0].isoformat()
    )
    assert (
        datetime.fromisoformat(result["orders"][0]["executed_at"])
        == session_times(bars[3].session_date)[0]
    )


def test_future_external_mutation_cannot_change_earlier_signals_fills_or_equity(data):
    profile = ProfileConfig(
        start_date=data.bars[0].session_date, end_date=data.bars[30].session_date
    )
    baseline = feature_source()
    future = FeaturePoint(
        observation_date=data.bars[20].session_date,
        available_at=data.bars[20].available_at,
        value=90,
    )
    altered = baseline.model_copy(update={"points": baseline.points + [future]})
    a = simulate(feature_rule(), profile, data, feature_data=[baseline])
    b = simulate(feature_rule(), profile, data, feature_data=[altered])
    cutoff = data.bars[19].available_at.isoformat()
    assert [s for s in a["signals"] if s["timestamp"] <= cutoff] == [
        s for s in b["signals"] if s["timestamp"] <= cutoff
    ]
    assert a["ledger"] == b["ledger"]
    assert a["equity"][:20] == b["equity"][:20]
    assert a == simulate(feature_rule(), profile, data, feature_data=[baseline])


def test_feature_missing_stale_and_forged_chronology_fail_at_engine_boundary(data):
    profile = ProfileConfig(
        start_date=data.bars[0].session_date, end_date=data.bars[10].session_date
    )
    with pytest.raises(ValueError, match="No published"):
        simulate(feature_rule(), profile, data)
    with pytest.raises(ValueError, match="Stale"):
        simulate(feature_rule(age=1), profile, data, feature_data=[feature_source()])
    broken = feature_source().model_copy(deep=True)
    broken.points[0] = broken.points[0].model_copy(update={"observation_date": date(2025, 1, 1)})
    with pytest.raises(ValueError, match="precedes"):
        simulate(feature_rule(), profile, data, feature_data=[broken])


@pytest.mark.parametrize("operand", [MACD(type="macd"), Stochastic(type="stochastic")])
def test_oscillator_future_mutation_preserves_earlier_simulation(data, operand):
    config = default_strategy()
    config.entry = Compare(
        type="compare", op="gt", left=operand, right={"type": "constant", "value": 0}
    )
    profile = ProfileConfig(
        start_date=data.bars[0].session_date, end_date=data.bars[-1].session_date
    )
    altered = data.model_copy(deep=True)
    for bar in altered.bars[70:]:
        for field in ("open", "high", "low", "close", "volume"):
            setattr(bar, field, getattr(bar, field) * 2)
    a, b = simulate(config, profile, data), simulate(config, profile, altered)
    assert a["equity"][:70] == b["equity"][:70]
    assert a["signals"][:70] == b["signals"][:70]
    cutoff = data.bars[69].available_at
    assert [e for e in a["ledger"] if datetime.fromisoformat(e["timestamp"]) <= cutoff] == [
        e for e in b["ledger"] if datetime.fromisoformat(e["timestamp"]) <= cutoff
    ]
    assert a == simulate(config, profile, data)


def imported_source(client, unknown=False, synthetic=True):
    csv = "observation_date,available_at,value\n2019-12-31,2019-12-31T21:30:00Z,20\n2020-01-02,2020-01-03T21:31:00Z,80\n"
    if unknown:
        csv = "observation_date,available_at,value\n2019-12-31,,20\n"
    response = client.post(
        "/api/research/context/import-csv",
        json={
            "series_id": "FEAR_GREED_US",
            "source": "SYNTHETIC source fixture",
            "source_url": "https://example.test/fixture",
            "availability_policy": "Explicit synthetic publication clocks, not real financial data.",
            "observations_csv": csv,
            "synthetic": synthetic,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def approved_source(client):
    source = imported_source(client)
    before = client.get(f"/api/research/context/{source['id']}/export").json()
    response = client.post(
        f"/api/research/context/{source['id']}/approve",
        json={
            "acknowledge_publication_policy": True,
            "review_note": "Reviewed explicit SYNTHETIC fixture publication clocks and coverage.",
        },
    )
    assert response.status_code == 201, response.text
    approved = response.json()
    assert approved["id"] != source["id"]
    assert approved["source_snapshot_hash"] == source["content_hash"]
    assert approved["research_only"] is False
    assert client.get(f"/api/research/context/{source['id']}/export").json() == before
    return approved


def prepared_external(client, data):
    dataset, strategy, _, profile = prepared(client, data)
    edited = client.patch(
        f"/api/strategies/{strategy['id']}",
        json={
            "name": "External fixture strategy",
            "config": feature_rule().model_dump(mode="json"),
            "expected_revision": 1,
        },
    )
    assert edited.status_code == 200
    version = client.post(
        f"/api/strategies/{strategy['id']}/publish", json={"expected_revision": 2}
    ).json()
    return {
        "strategy_version_ids": [version["id"]],
        "profile_id": profile["id"],
        "dataset_id": dataset["id"],
        "acknowledge_synthetic": True,
    }


def test_review_cannot_waive_unknown_publication_or_fear_greed_bounds(client):
    source = imported_source(client, unknown=True)
    body = {
        "acknowledge_publication_policy": True,
        "review_note": "Review cannot invent missing publication timestamps for this source.",
    }
    response = client.post(f"/api/research/context/{source['id']}/approve", json=body)
    assert response.status_code == 422 and "Unknown publication" in response.text
    assert (
        client.post(
            f"/api/research/context/{source['id']}/approve",
            json={**body, "acknowledge_publication_policy": False},
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/research/context/import-csv",
            json={
                "series_id": "FEAR_GREED_US",
                "source": "fixture",
                "source_url": "https://example.test/",
                "availability_policy": "Synthetic invalid-range fixture.",
                "observations_csv": "observation_date,available_at,value\n2019-12-31,2019-12-31T21:30:00Z,101\n",
            },
        ).status_code
        == 422
    )


def test_queue_blocks_unreviewed_missing_duplicate_or_stale_external_inputs(client, data):
    body = prepared_external(client, data)
    assert client.post("/api/backtests", json=body).status_code == 422
    unreviewed = imported_source(client)
    assert (
        client.post(
            "/api/backtests", json={**body, "context_snapshot_ids": [unreviewed["id"]]}
        ).status_code
        == 422
    )
    approved = approved_source(client)
    assert (
        client.post(
            "/api/backtests",
            json={**body, "context_snapshot_ids": [approved["id"], approved["id"]]},
        ).status_code
        == 422
    )
    assert client.get("/api/backtests").json() == []


def test_worker_pins_approved_revision_and_reproduces_after_another_source_import(
    client, database, data
):
    body = prepared_external(client, data)
    approved = approved_source(client)
    body["context_snapshot_ids"] = [approved["id"]]
    response = client.post("/api/backtests", json=body)
    assert response.status_code == 202, response.text
    run = response.json()[0]
    from app.backtesting.engine import ENGINE_VERSION

    assert run["provenance"]["engine_version"] == ENGINE_VERSION
    assert run["provenance"]["external_inputs"][0]["content_hash"] == approved["content_hash"]
    # Import a different source revision while the old job is waiting. No lookup of "latest".
    imported_source(client, unknown=True)
    process_one(database)
    status = client.get(f"/api/backtests/{run['id']}").json()
    assert status["status"] == "completed", status
    result = client.get(f"/api/backtests/{run['id']}/results").json()
    assert result["metrics"]["executed_orders"] == 1
    again = client.post("/api/backtests", json=body).json()[0]
    process_one(database)
    assert client.get(f"/api/backtests/{again['id']}/results").json() == result


def test_worker_rejects_frozen_source_content_tampering(client, database, data):
    body = prepared_external(client, data)
    approved = approved_source(client)
    run = client.post(
        "/api/backtests", json={**body, "context_snapshot_ids": [approved["id"]]}
    ).json()[0]
    # SQLite fixture uses create_all; production migrations additionally forbid this update.
    with database() as db:
        row = db.get(ContextSnapshot, approved["id"])
        payload = deepcopy(row.payload)
        payload["observations"][0]["value"] = "99"
        row.payload = payload
        db.commit()
    process_one(database)
    status = client.get(f"/api/backtests/{run['id']}").json()
    assert status["status"] == "failed"
    assert "hash mismatch" in status["error"]


def test_frozen_manifest_and_duplicate_series_rejected(client, database):
    first, second = approved_source(client), approved_source(client)
    with database() as db:
        with pytest.raises(ValueError, match="one snapshot per"):
            resolve_features(db, [first["id"], second["id"]])
        with pytest.raises(ValueError, match="manifest hash mismatch"):
            frozen_features(db, {"external_inputs": [], "external_input_hash": "0" * 64})
