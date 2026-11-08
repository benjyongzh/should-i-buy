"""SYNTHETIC financial fixtures; journal tests never contact providers."""

from copy import deepcopy
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DatabaseError
from test_workflow import prepared

from app.api import journal
from app.llm.chat_context import build_context
from app.llm.chat_contracts import ChatSelection
from app.models.entities import BacktestRun, Profile, ResearchEvent, ResearchStudy, Strategy, utcnow
from app.schemas.domain import canonical_hash
from app.services.jobs import process_one


def baseline(client, database, data):
    dataset, strategy, version, profile = prepared(client, data)
    response = client.post(
        "/api/backtests",
        json={
            "strategy_version_ids": [version["id"]],
            "profile_id": profile["id"],
            "dataset_id": dataset["id"],
            "acknowledge_synthetic": True,
        },
    )
    run = response.json()[0]
    assert process_one(database) == run["id"]
    return strategy, run


def plan(client, run, **kwargs):
    body = {
        "request_id": "plan-one",
        "baseline_run_id": run["id"],
        "question": "Does reducing position size reduce drawdown?",
        "hypothesis": "Smaller positions may reduce the drawdown and the return.",
        "planned_change": "Reduce fixed fraction of cash from one to one half.",
        "evaluation_criteria": "Compare ending equity and maximum drawdown, yearly periods and all attempts.",
        **kwargs,
    }
    response = client.post("/api/research/studies", json=body)
    assert response.status_code == 201, response.text
    return response.json(), body


def publish_candidate(client, strategy):
    config = deepcopy(strategy["draft"])
    config["sizing"]["value"] = "0.5"
    response = client.patch(
        f"/api/strategies/{strategy['id']}",
        json={"name": strategy["name"], "config": config, "expected_revision": 1},
    )
    assert response.status_code == 200, response.text
    return client.post(
        f"/api/strategies/{strategy['id']}/publish",
        json={"expected_revision": 2, "change_summary": "SYNTHETIC half cash sizing"},
    ).json()


def bind(client, study, version):
    response = client.post(
        f"/api/research/studies/{study['id']}/candidate",
        json={"strategy_version_id": version["id"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_prospective_plan_repeat_attempts_failed_outcome_and_immutable_conclusion(
    client, database, data
):
    strategy, run = baseline(client, database, data)
    study, body = plan(client, run)
    assert client.post("/api/research/studies", json=body).json()["id"] == study["id"]
    assert (
        client.post(
            "/api/research/studies",
            json={
                **body,
                "hypothesis": "A different hypothesis that conflicts with the same request.",
            },
        ).status_code
        == 409
    )
    assert canonical_hash(study["payload"]) == study["content_hash"]
    assert "daily_returns" not in study["payload"]["baseline"]["metrics"]
    bind(client, study, publish_candidate(client, strategy))
    path = f"/api/research/studies/{study['id']}"
    assert client.post(path + "/schedule", json={"request_id": "attempt-one"}).status_code == 422
    request = {"request_id": "attempt-one", "acknowledge_synthetic": True}
    response = client.post(path + "/schedule", json=request)
    assert response.status_code == 202, response.text
    first = response.json()["attempts"][0]["id"]
    assert client.post(path + "/schedule", json=request).json()["attempts"][0]["id"] == first
    assert len(client.get(path).json()["attempts"]) == 1
    assert (
        client.post(
            path + "/conclusion",
            json={"assessment": "mixed", "summary": "Wait for the result to finish."},
        ).status_code
        == 422
    )
    assert process_one(database) == first
    repeat = client.post(
        path + "/schedule", json={"request_id": "repeat", "acknowledge_synthetic": True}
    ).json()["attempts"][-1]["id"]
    assert process_one(database) == repeat
    failure = client.post(
        path + "/schedule", json={"request_id": "failed-attempt", "acknowledge_synthetic": True}
    ).json()["attempts"][-1]["id"]
    # A failed job must remain visible and be captured in the conclusion.
    with database() as db:
        failed = db.get(BacktestRun, failure)
        failed.status, failed.error, failed.completed_at = (
            "failed",
            "SYNTHETIC provider fixture failure",
            utcnow(),
        )
        db.commit()
    state = client.get(path).json()
    assert state["attempts"][0]["result_hash"] == state["attempts"][1]["result_hash"]
    assert state["attempts"][-1]["error"] == "SYNTHETIC provider fixture failure"
    assert state["attempts"][0]["metric_deltas"]["executed_orders"] == "0"
    conclusion = {
        "assessment": "mixed",
        "summary": "Smaller sizing changed returns; one attempt failed and remains recorded.",
        "next_hypothesis": "Compare different timing next.",
    }
    response = client.post(path + "/conclusion", json=conclusion)
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "concluded"
    final = response.json()["events"][-1]
    assert len(final["payload"]["attempts"]) == 3
    assert client.post(path + "/conclusion", json=conclusion).status_code == 200
    assert (
        client.post(path + "/conclusion", json={**conclusion, "assessment": "improved"}).status_code
        == 409
    )
    assert client.post(path + "/schedule", json={"request_id": "after-close"}).status_code == 409
    assert (
        client.post(
            path + "/notes",
            json={"request_id": "later-note", "text": "Later interpretation retained separately."},
        ).status_code
        == 200
    )
    assert (
        client.post(
            path + "/notes", json={"request_id": "later-note", "text": "Overwritten note."}
        ).status_code
        == 409
    )


def test_prospective_chronology_cross_strategy_and_retrospective_label(client, database, data):
    strategy, run = baseline(client, database, data)
    candidate = publish_candidate(client, strategy)
    study, _ = plan(client, run)
    path = f"/api/research/studies/{study['id']}"
    assert (
        client.post(path + "/candidate", json={"strategy_version_id": candidate["id"]}).status_code
        == 422
    )
    retro, _ = plan(client, run, request_id="retro", mode="retrospective")
    bind(client, retro, candidate)
    other_strategy, other_run = baseline(client, database, data)
    other = publish_candidate(client, other_strategy)
    assert (
        client.post(path + "/candidate", json={"strategy_version_id": other["id"]}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/research/studies",
            json={
                "request_id": "bad-parent",
                "baseline_run_id": other_run["id"],
                "parent_id": study["id"],
                "question": "A separate strategy question.",
                "hypothesis": "An unrelated hypothesis for another strategy.",
                "planned_change": "A separate rule change.",
                "evaluation_criteria": "Compare all candidate results.",
            },
        ).status_code
        == 422
    )
    assert (
        client.get("/api/research/studies", params={"strategy_id": strategy["id"]}).json()[0][
            "strategy_id"
        ]
        == strategy["id"]
    )


def test_controls_and_atomic_scheduling_reject_profile_or_engine_changes(
    client, database, data, monkeypatch
):
    strategy, run = baseline(client, database, data)
    study, _ = plan(client, run)
    candidate = publish_candidate(client, strategy)
    bind(client, study, candidate)
    path = f"/api/research/studies/{study['id']}"
    with database() as db:
        profile = db.get(Profile, study["payload"]["profile_id"])
        profile.config = {**profile.config, "fixed_fee": "99"}
        db.commit()
    assert (
        client.post(
            path + "/schedule", json={"request_id": "bad-profile", "acknowledge_synthetic": True}
        ).status_code
        == 422
    )
    with database() as db:
        profile = db.get(Profile, study["payload"]["profile_id"])
        profile.config = study["payload"]["profile_snapshot"]
        db.commit()
        before = db.scalar(select(func.count()).select_from(BacktestRun))
    original = journal.check_run

    def rejected(*args):
        raise ValueError("SYNTHETIC control mismatch after queue construction")

    monkeypatch.setattr(journal, "check_run", rejected)
    assert (
        client.post(
            path + "/schedule", json={"request_id": "rolled-back", "acknowledge_synthetic": True}
        ).status_code
        == 422
    )
    with database() as db:
        assert db.scalar(select(func.count()).select_from(BacktestRun)) == before
    monkeypatch.setattr(journal, "check_run", original)
    monkeypatch.setattr(journal, "ENGINE_VERSION", "future-engine")
    assert (
        client.post(
            path + "/schedule", json={"request_id": "engine-change", "acknowledge_synthetic": True}
        ).status_code
        == 422
    )
    # Attach path validates the same controls as scheduling.
    with database() as db:
        wrong = BacktestRun(
            strategy_version_id=candidate["id"],
            profile_id=run["profile_id"],
            dataset_id=run["dataset_id"],
            profile_snapshot=run["profile_snapshot"],
            provenance={**run["provenance"], "profile_hash": "wrong"},
            status="failed",
        )
        db.add(wrong)
        db.commit()
        wrong_id = wrong.id
    assert client.post(path + "/runs", json={"run_id": wrong_id}).status_code == 422


def test_journal_evidence_cutoff_keeps_conversation_isolation_and_future_outcomes_hidden(
    client, database, data
):
    strategy, run = baseline(client, database, data)
    study, _ = plan(client, run)
    bind(client, study, publish_candidate(client, strategy))
    path = f"/api/research/studies/{study['id']}"
    response = client.post(
        path + "/schedule", json={"request_id": "one", "acknowledge_synthetic": True}
    )
    attempt = response.json()["attempts"][0]["id"]
    before_completion = utcnow()
    assert process_one(database) == attempt
    with database() as db:
        row = db.get(Strategy, strategy["id"])
        context = build_context(
            db, row, ChatSelection(study_ids=[study["id"]], as_of=before_completion)
        )
        evidence = context["evidence"][0]
        assert evidence["summary"]["attempts"][0]["status"] == "outcome_not_available_at_cutoff"
        assert "metrics" not in evidence["summary"]["attempts"][0]
        assert not evidence["reviewed"]
        assert len(evidence["summary"]["baseline_yearly_periods"]) == 1
        assert "yearly_periods" not in evidence["summary"]["attempts"][0]
        completed_context = build_context(db, row, ChatSelection(study_ids=[study["id"]]))
        assert (
            len(completed_context["evidence"][0]["summary"]["attempts"][0]["yearly_periods"]) == 1
        )
        with pytest.raises(ValueError, match="did not exist"):
            build_context(
                db,
                row,
                ChatSelection(
                    study_ids=[study["id"]],
                    as_of=journal.stamp(db.get(ResearchStudy, study["id"]).created_at)
                    - timedelta(seconds=1),
                ),
            )
        other = Strategy(name="SYNTHETIC another conversation", draft=row.draft)
        db.add(other)
        db.flush()
        with pytest.raises(ValueError, match="another strategy"):
            build_context(db, other, ChatSelection(study_ids=[study["id"]]))


def assert_postgres_journal_immutability(factory):
    """Invoked after real Alembic migrations, not metadata.create_all."""
    with factory() as db:
        strategy = Strategy(name="SYNTHETIC journal immutability", draft={})
        db.add(strategy)
        db.flush()
        study = ResearchStudy(
            strategy_id=strategy.id,
            request_id="journal-pg",
            request_hash="0" * 64,
            content_hash="1" * 64,
            payload={"fixture": True},
        )
        db.add(study)
        db.flush()
        event = ResearchEvent(
            study_id=study.id,
            slot="note-one",
            kind="note",
            content_hash="2" * 64,
            payload={"text": "SYNTHETIC"},
        )
        db.add(event)
        db.commit()
        for row in (study, event):
            row.payload = {"overwrite": True}
            with pytest.raises(DatabaseError, match="Immutable"):
                db.commit()
            db.rollback()
            db.delete(row)
            with pytest.raises(DatabaseError, match="Immutable"):
                db.commit()
            db.rollback()
