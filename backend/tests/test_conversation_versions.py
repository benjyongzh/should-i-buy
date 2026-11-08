"""SYNTHETIC conversation histories; tests never contact live LLM/data providers."""

import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError, IntegrityError
from test_strategy_chat import configure, draft, events

from app.llm import chat_routes
from app.llm.chat_contracts import ChatReply
from app.models.entities import StrategyChatTurn, StrategyConversation, utcnow
from app.schemas.domain import canonical_hash, default_strategy


def fake_author(monkeypatch, seen):
    async def author(context, history, message):
        seen.append((context, history, message))
        answer = ChatReply(message="SYNTHETIC acknowledgment; no rules changed.", outcome="discuss")
        yield "delta", answer.message
        yield "complete", {"reply": answer}

    monkeypatch.setattr(chat_routes, "stream_reply", author)


def seed_turn(
    db,
    strategy_id,
    sequence,
    message="SYNTHETIC note",
    *,
    status="completed",
    reply=None,
    cutoff="2020-01-01T00:00:00Z",
):
    row = StrategyChatTurn(
        strategy_id=strategy_id,
        sequence=sequence,
        request_id=f"fixture-{sequence}",
        source_revision=1,
        user_text=message,
        status=status,
        completed_at=utcnow(),
        context_json={"evidence_cutoff": cutoff},
        reply_json=reply
        or {
            "message": "SYNTHETIC reply",
            "outcome": "discuss",
            "cited_evidence_ids": [],
            "estimates": [],
        },
        partial_text="",
    )
    db.add(row)
    return row


def test_all_prior_turns_recalled_beyond_eight_and_isolated_by_strategy(
    client, database, monkeypatch
):
    configure(monkeypatch)
    seen = []
    fake_author(monkeypatch, seen)
    first, other = draft(client), draft(client)
    with database() as db:
        for i in range(1, 14):
            record = seed_turn(
                db,
                first["id"],
                i,
                "Remember a321SGD budget, not321shares"
                if i == 1
                else f"SYNTHETIC intervening note{i}",
            )
            if i == 1:
                record.reply_json = {**record.reply_json, "config": first["draft"]}
        db.commit()
    response = events(
        client.post(
            f"/api/llm/strategies/{first['id']}/turns",
            json={
                "request_id": "recall",
                "expected_revision": 1,
                "message": "What budget did I choose at the start?",
            },
        )
    )
    assert response[-1][0] == "complete"
    assert (
        len(seen[0][1]) == 13
        and seen[0][1][0]["user_text"] == "Remember a321SGD budget, not321shares"
    )
    assert len(seen[0][0]["history_turn_ids"]) == 13
    assert seen[0][1][0]["reply_json"]["config"] == first["draft"]
    events(
        client.post(
            f"/api/llm/strategies/{other['id']}/turns",
            json={"request_id": "other", "expected_revision": 1, "message": "Different strategy"},
        )
    )
    assert seen[1][1] == []
    root = client.get(f"/api/llm/strategies/{first['id']}/conversation").json()
    assert root["id"] == first["id"] and root["total_turns"] == 14
    clone = client.post(f"/api/strategies/{first['id']}/clone").json()
    assert client.get(f"/api/llm/strategies/{clone['id']}/conversation").json()["total_turns"] == 0
    with database() as db:
        db.add(StrategyConversation(strategy_id=first["id"]))
        with pytest.raises(IntegrityError):
            db.commit()


def test_version_transcripts_freeze_before_later_dialogue_and_are_read_only(client, monkeypatch):
    configure(monkeypatch)
    strategy = draft(client)

    async def author(context, history, message):
        answer = ChatReply(
            message="SYNTHETIC requested budget " + message,
            outcome="propose",
            config={**strategy["draft"], "sizing": {"mode": "fixed_notional", "value": message}},
        )
        yield "delta", answer.message
        yield "complete", {"reply": answer}

    monkeypatch.setattr(chat_routes, "stream_reply", author)
    root = f"/api/llm/strategies/{strategy['id']}"
    versions = []
    for number, budget in enumerate(["321", "700"], 1):
        turn = events(
            client.post(
                root + "/turns",
                json={"request_id": budget, "expected_revision": number, "message": budget},
            )
        )[-1][1]
        assert (
            client.post("/api/llm/proposals/" + turn["proposal"]["id"] + "/accept").status_code
            == 200
        )
        version = client.post(
            f"/api/strategies/{strategy['id']}/publish", json={"expected_revision": number + 1}
        ).json()
        versions.append(version)
        snapshot = client.get(root + f"/versions/{version['id']}/conversation/export").json()
        assert snapshot["content_hash"] == canonical_hash(snapshot["data"])
        assert snapshot["data"]["accepted_chat_turn_id"] == turn["turn"]["id"]
        assert len(snapshot["data"]["turns"]) == number
        if number == 1:
            original = snapshot
    path = root + f"/versions/{versions[0]['id']}/conversation"
    assert client.get(path + "/export").json() == original
    assert [t["user_text"] for t in client.get(path).json()["turns"]] == ["321"]
    assert client.post(path, json={"message": "change history"}).status_code == 405
    assert client.get("/api/strategy-versions/" + versions[0]["id"]).json() == versions[0]
    other = draft(client)
    assert (
        client.get(
            f"/api/llm/strategies/{other['id']}/versions/{versions[0]['id']}/conversation"
        ).status_code
        == 404
    )


def test_publication_rejects_streaming_then_freezes_interrupted_turn(client, database):
    strategy = draft(client)
    with database() as db:
        row = seed_turn(db, strategy["id"], 1, status="streaming")
        db.commit()
        identifier = row.id
    url = f"/api/strategies/{strategy['id']}/publish"
    assert client.post(url, json={"expected_revision": 1}).status_code == 409
    assert client.get(f"/api/strategies/{strategy['id']}/versions").json() == []
    with database() as db:
        db.get(StrategyChatTurn, identifier).status = "interrupted"
        db.commit()
    version = client.post(url, json={"expected_revision": 1}).json()
    snapshot = client.get(
        f"/api/llm/strategies/{strategy['id']}/versions/{version['id']}/conversation"
    ).json()
    assert snapshot["turns"][0]["status"] == "interrupted"


def test_archive_pagination_reads_beyond_latest100_and_keeps_boundary(client, database):
    strategy = draft(client)
    root = f"/api/llm/strategies/{strategy['id']}"
    with database() as db:
        for i in range(1, 123):
            seed_turn(db, strategy["id"], i)
        db.commit()
    assert client.get(root + "/turns").json()[0]["sequence"] == 23
    first = client.get(root + "/history?limit=50").json()
    assert first["turns"][0]["sequence"] == 1 and first["has_more"]
    with database() as db:
        seed_turn(db, strategy["id"], 123)
        db.commit()
    second = client.get(
        root + f"/history?after={first['next_after']}&through={first['through_sequence']}&limit=100"
    ).json()
    assert second["turns"][-1]["sequence"] == 122 and not second["has_more"]
    version = client.post(
        f"/api/strategies/{strategy['id']}/publish", json={"expected_revision": 1}
    ).json()
    path = root + f"/versions/{version['id']}/conversation"
    initial = client.get(path + "?limit=100").json()
    assert len(initial["turns"]) == 100 and initial["has_more"]
    assert len(client.get(path + "?after=100&limit=100").json()["turns"]) == 23


def test_recall_keeps_failed_user_intent_but_withholds_unselected_facts_and_future_turns(
    client, database, monkeypatch
):
    configure(monkeypatch)
    seen = []
    fake_author(monkeypatch, seen)
    strategy = draft(client)
    with database() as db:
        a = seed_turn(db, strategy["id"], 1, "My budget is500SGD", status="failed")
        a.partial_text = "Unvalidated false assistant promise"
        seed_turn(
            db,
            strategy["id"],
            2,
            "Keep weekly buys",
            reply={
                "message": "A deselected source said a future price",
                "cited_evidence_ids": ["deselected"],
                "estimates": [],
            },
        )
        seed_turn(db, strategy["id"], 3, "SYNTHETIC later fact", cutoff="2025-01-01T00:00:00Z")
        db.commit()
    events(
        client.post(
            f"/api/llm/strategies/{strategy['id']}/turns",
            json={
                "request_id": "cutoff",
                "expected_revision": 1,
                "message": "Recall my intent",
                "selection": {"as_of": "2021-01-01T00:00:00Z"},
            },
        )
    )
    context, history, _ = seen[0]
    assert (
        len(history) == 2
        and history[0]["user_text"] == "My budget is500SGD"
        and history[1]["user_text"] == "Keep weekly buys"
    )
    assert "Unvalidated false" not in json.dumps(
        history
    ) and "deselected source said" not in json.dumps(history)
    assert (
        len(context["excluded_future_turn_ids"]) == 1
        and len(context["withheld_reply_turn_ids"]) == 2
    )


def test_large_memory_fails_explicitly_instead_of_silently_forgetting(
    client, database, monkeypatch
):
    configure(monkeypatch)
    seen = []
    fake_author(monkeypatch, seen)
    strategy = draft(client)
    with database() as db:
        for i in range(1, 31):
            seed_turn(db, strategy["id"], i, "SYNTHETIC " + ("x" * 4900))
        db.commit()
    root = f"/api/llm/strategies/{strategy['id']}"
    response = client.post(
        root + "/turns",
        json={"request_id": "too-big", "expected_revision": 1, "message": "Recall it all"},
    )
    assert response.status_code == 422 and "No older messages were truncated" in response.text
    assert not seen and client.get(root + "/conversation").json()["total_turns"] == 30


def test_007_backfills_legacy_boundaries_without_future_replies_and_enforces_immutability(
    tmp_path, monkeypatch
):
    import sqlalchemy as sa
    from alembic import command
    from alembic.config import Config

    from app.core.config import settings

    url = f"sqlite:///{tmp_path / 'legacy.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "006_strategy_chat")
    engine = sa.create_engine(url)
    metadata = sa.MetaData()
    strategy = sa.Table("strategies", metadata, autoload_with=engine)
    version = sa.Table("strategy_versions", metadata, autoload_with=engine)
    turns = sa.Table("strategy_chat_turns", metadata, autoload_with=engine)
    rules = default_strategy().model_dump(mode="json")

    def clock(hour, minute):
        return datetime(2020, 1, 2, hour, minute, tzinfo=UTC)

    with engine.begin() as db:
        db.execute(
            strategy.insert().values(
                id="s",
                created_at=clock(10, 0),
                name="SYNTHETIC legacy",
                description="",
                archived=False,
                draft=rules,
                draft_revision=1,
            )
        )
        db.execute(
            version.insert().values(
                id="v",
                created_at=clock(12, 0),
                strategy_id="s",
                number=1,
                config=rules,
                config_hash=canonical_hash(rules),
                schema_version=1,
                change_summary="SYNTHETIC",
            )
        )
        for i, (created, completed) in enumerate(
            [
                (clock(11, 0), clock(11, 30)),
                (clock(11, 50), clock(12, 30)),
                (clock(12, 1), clock(12, 2)),
            ],
            1,
        ):
            db.execute(
                turns.insert().values(
                    id=str(i),
                    created_at=created,
                    completed_at=completed,
                    strategy_id="s",
                    request_id=str(i),
                    source_revision=1,
                    user_text=f"SYNTHETIC user{i}",
                    status="completed",
                    context_json={"evidence_cutoff": created.isoformat()},
                    reply_json={"message": f"SYNTHETIC reply{i}"},
                    partial_text=f"SYNTHETIC partial{i}",
                )
            )
    command.upgrade(config, "head")
    command.check(config)
    snapshots = sa.Table("version_conversations", sa.MetaData(), autoload_with=engine)
    with engine.connect() as db:
        row = db.execute(sa.select(snapshots)).mappings().one()
        payload = row["payload"]
        assert canonical_hash(payload) == row["content_hash"]
        assert (
            len(payload["turns"]) == 2
            and payload["turns"][1]["status"] == "in_progress_at_publication"
        )
        assert (
            payload["turns"][1]["reply_json"] is None and payload["turns"][1]["partial_text"] == ""
        )
        assert "reply3" not in json.dumps(payload) and "reply2" not in json.dumps(payload)
    for statement in [
        "UPDATE strategy_conversations SET created_at=created_at",
        "DELETE FROM strategy_conversations",
        "UPDATE version_conversations SET content_hash='tamper'",
        "DELETE FROM version_conversations",
        "UPDATE strategy_chat_turns SET user_text='tamper' WHERE id='1'",
        "DELETE FROM strategy_chat_turns WHERE id='1'",
    ]:
        with pytest.raises(DatabaseError, match="Immutable"), engine.begin() as db:
            db.execute(text(statement))
    engine.dispose()


def assert_postgres_conversation_immutability(factory):
    from app.models.entities import Strategy, StrategyVersion, VersionConversation

    rules = default_strategy().model_dump(mode="json")
    with factory() as db:
        strategy = Strategy(name="SYNTHETIC conversation immutability", draft=rules)
        db.add(strategy)
        db.flush()
        turn = seed_turn(db, strategy.id, 1)
        version = StrategyVersion(
            strategy_id=strategy.id,
            number=1,
            config=rules,
            config_hash=canonical_hash(rules),
            schema_version=1,
        )
        db.add(version)
        db.flush()
        payload = {"conversation_id": strategy.id, "turn_ids": [turn.id]}
        db.add(
            VersionConversation(
                version_id=version.id,
                strategy_id=strategy.id,
                payload=payload,
                content_hash=canonical_hash(payload),
            )
        )
        db.commit()
        sid, vid, tid = strategy.id, version.id, turn.id
    checks = [
        (
            "UPDATE strategy_conversations SET created_at=created_at WHERE strategy_id=:identifier",
            sid,
        ),
        ("DELETE FROM strategy_conversations WHERE strategy_id=:identifier", sid),
        ("UPDATE version_conversations SET payload=payload WHERE version_id=:identifier", vid),
        ("DELETE FROM version_conversations WHERE version_id=:identifier", vid),
        ("UPDATE strategy_chat_turns SET user_text=user_text WHERE id=:identifier", tid),
        ("DELETE FROM strategy_chat_turns WHERE id=:identifier", tid),
    ]
    for statement, identifier in checks:
        with factory() as db, pytest.raises(DatabaseError, match="Immutable"):
            db.execute(text(statement), {"identifier": identifier})
            db.commit()
