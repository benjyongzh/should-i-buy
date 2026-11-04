from copy import deepcopy
from datetime import timedelta

from app.llm.client import compatible_schema
from app.models.entities import BacktestRun, utcnow
from app.schemas.domain import ProfileConfig, StrategyConfig, default_strategy
from app.services.jobs import claim, expire_stale, process_one


def prepared(client, data):
    response = client.post("/api/market-data/import", json=data.model_dump(mode="json"))
    assert response.status_code == 201, response.text
    dataset = response.json()
    response = client.post(
        "/api/strategies",
        json={"name": "Buy and hold", "config": default_strategy().model_dump(mode="json")},
    )
    assert response.status_code == 201, response.text
    strategy = response.json()
    version = client.post(
        f"/api/strategies/{strategy['id']}/publish", json={"expected_revision": 1}
    ).json()
    profile = client.post(
        "/api/backtest-profiles",
        json={
            "name": "Standard SGD Portfolio",
            "config": ProfileConfig(
                start_date=data.bars[0].session_date, end_date=data.bars[-1].session_date
            ).model_dump(mode="json"),
        },
    ).json()
    return dataset, strategy, version, profile


def test_end_to_end_immutable_version_and_profile(client, database, data):
    dataset, strategy, version, profile = prepared(client, data)
    body = {
        "strategy_version_ids": [version["id"]],
        "profile_id": profile["id"],
        "dataset_id": dataset["id"],
        "acknowledge_synthetic": True,
    }
    scheduled = client.post("/api/backtests", json=body)
    assert scheduled.status_code == 202, scheduled.text
    run = scheduled.json()[0]
    assert run["status"] == "queued"
    assert process_one(database) == run["id"]
    status = client.get(f"/api/backtests/{run['id']}").json()
    assert status["status"] == "completed", status
    result = client.get(f"/api/backtests/{run['id']}/results").json()
    assert result["metrics"]["executed_orders"] == 1
    changed = deepcopy(profile["config"])
    changed["fixed_fee"] = "5.00"
    assert (
        client.patch(
            f"/api/backtest-profiles/{profile['id']}",
            json={"name": profile["name"], "config": changed},
        ).status_code
        == 200
    )
    assert (
        client.get(f"/api/backtests/{run['id']}").json()["profile_snapshot"]["fixed_fee"] == "2.50"
    )
    assert client.get(f"/api/backtests/{run['id']}/results").json() == result
    config = strategy["draft"]
    config["sizing"]["value"] = "0.2"
    edit = client.patch(
        f"/api/strategies/{strategy['id']}",
        json={"name": "Edited", "config": config, "expected_revision": 1},
    )
    assert edit.status_code == 200
    assert (
        client.get(f"/api/strategy-versions/{version['id']}").json()["config_hash"]
        == version["config_hash"]
    )
    assert (
        client.patch(f"/api/strategy-versions/{version['id']}", json={"config": config}).status_code
        == 405
    )
    assert (
        client.patch(
            f"/api/strategies/{strategy['id']}",
            json={"name": "Lost edit", "config": config, "expected_revision": 1},
        ).status_code
        == 409
    )
    comparison = client.get(f"/api/experiments/{run['experiment_id']}/comparison").json()
    assert comparison[0]["metrics"] == result["metrics"]
    assert process_one(database) is None


def test_explicit_demo_selection_cancellation_and_stale_worker(client, database, data):
    dataset, _, version, profile = prepared(client, data)
    body = {
        "strategy_version_ids": [version["id"]],
        "profile_id": profile["id"],
        "dataset_id": dataset["id"],
    }
    assert client.post("/api/backtests", json=body).status_code == 422
    body["acknowledge_synthetic"] = True
    run = client.post("/api/backtests", json=body).json()[0]
    client.post(f"/api/backtests/{run['id']}/cancel")
    assert claim(database) is None
    run = client.post("/api/backtests", json=body).json()[0]
    ownership = claim(database)
    assert ownership[0] == run["id"]
    assert claim(database) is None
    with database() as db:
        row = db.get(BacktestRun, run["id"])
        row.heartbeat_at = utcnow() - timedelta(hours=1)
        db.commit()
    assert expire_stale(database) == 1
    status = client.get(f"/api/backtests/{run['id']}").json()
    assert status["status"] == "failed"
    assert "lease expired" in status["error"]


def test_worker_failure_persisted(client, database, data):
    dataset, _, version, profile = prepared(client, data)
    body = {
        "strategy_version_ids": [version["id"]],
        "profile_id": profile["id"],
        "dataset_id": dataset["id"],
        "acknowledge_synthetic": True,
    }
    run = client.post("/api/backtests", json=body).json()[0]
    with database() as db:
        row = db.get(BacktestRun, run["id"])
        row.provenance = {**row.provenance, "engine_version": "incompatible"}
        db.commit()
    process_one(database)
    status = client.get(f"/api/backtests/{run['id']}").json()
    assert status["status"] == "failed"
    assert "engine version" in status["error"]


def test_llm_missing_key_and_human_approval(client, data, monkeypatch):
    _, strategy, _, _ = prepared(client, data)
    response = client.post(
        "/api/llm/generate-strategy",
        json={"strategy_id": strategy["id"], "prompt": "use a smaller allocation"},
    )
    assert response.status_code == 422
    assert "not configured" in response.text
    from app.llm.client import CompatibleAuthor

    proposed = default_strategy()
    proposed.sizing.value = __import__("decimal").Decimal("0.05")
    monkeypatch.setattr(CompatibleAuthor, "propose", lambda *args: proposed)
    proposal = client.post(
        "/api/llm/modify-strategy", json={"strategy_id": strategy["id"], "prompt": "use 5 percent"}
    ).json()
    assert client.get(f"/api/strategies/{strategy['id']}").json()["draft_revision"] == 1
    accepted = client.post(f"/api/llm/proposals/{proposal['id']}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["draft"]["sizing"]["value"] == "0.05"
    assert len(client.get(f"/api/strategies/{strategy['id']}/versions").json()) == 1
    assert client.post(f"/api/llm/proposals/{proposal['id']}/accept").status_code == 409
    schema = compatible_schema(StrategyConfig.model_json_schema())
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
