"""SYNTHETIC conversation/evidence fixtures; no live provider access."""

import asyncio
import json
from datetime import timedelta

import httpx
import pytest

from app.core.config import settings
from app.llm import chat_provider, chat_routes
from app.llm.chat_contracts import ChatReply
from app.models.entities import BacktestRun, StrategyChatTurn, utcnow
from app.schemas.domain import ProfileConfig, canonical_hash, default_strategy


def configure(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "fixture-key")
    monkeypatch.setenv("LLM_MODEL", "fixture-model")
    settings.cache_clear()


def draft(client):
    return client.post(
        "/api/strategies",
        json={"name": "SYNTHETIC chat", "config": default_strategy().model_dump(mode="json")},
    ).json()


def events(response):
    assert response.status_code == 200, response.text
    return [
        (block.splitlines()[0][7:], json.loads(block.splitlines()[1][6:]))
        for block in response.text.strip().split("\n\n")
    ]


def reply(**values):
    return ChatReply(
        message="Let's define what small means first.",
        outcome="clarify",
        questions=[{"question": "How much per buy?", "choices": ["SGD500", "10% cash"]}],
        **values,
    )


def test_clarification_conversation_keeps_history_and_gates_publication(client, monkeypatch):
    configure(monkeypatch)
    strategy = draft(client)
    seen = []

    async def author(context, history, message):
        seen.append((context, history, message))
        answer = (
            reply()
            if not history
            else ChatReply(
                message="Buy with a fixed500 budget.",
                outcome="propose",
                config={**strategy["draft"], "sizing": {"mode": "fixed_notional", "value": "500"}},
            )
        )
        yield "delta", answer.message[:8]
        yield "delta", answer.message[8:]
        yield (
            "complete",
            {
                "reply": answer,
                "usage": {"total_tokens": 42},
                "provider_request_id": "fixture-request",
            },
        )

    monkeypatch.setattr(chat_routes, "stream_reply", author)
    path = f"/api/llm/strategies/{strategy['id']}/turns"
    first = events(
        client.post(
            path,
            json={
                "request_id": "one",
                "expected_revision": 1,
                "message": "Buy small positions more often",
            },
        )
    )
    assert [kind for kind, _ in first] == [
        "context",
        "status",
        "delta",
        "delta",
        "status",
        "complete",
    ]
    assert first[-1][1]["proposal"] is None
    assert client.get(f"/api/strategies/{strategy['id']}").json()["draft_revision"] == 1
    second = events(
        client.post(
            path,
            json={
                "request_id": "two",
                "expected_revision": 1,
                "message": "SGD500 per buy; preserve daily timing and all other rules",
            },
        )
    )
    proposal = second[-1][1]["proposal"]
    assert proposal
    assert seen[1][1][0]["reply_json"]["outcome"] == "clarify"
    assert seen[1][1][0]["user_text"] == "Buy small positions more often"
    snapshot = second[0][1]["context"]
    hashed = snapshot.pop("context_hash")
    assert canonical_hash(snapshot) == hashed
    assert client.get(f"/api/strategies/{strategy['id']}/versions").json() == []
    assert client.post(f"/api/llm/proposals/{proposal['id']}/accept").status_code == 200
    assert client.get(f"/api/strategies/{strategy['id']}/versions").json() == []
    assert (
        client.post(
            f"/api/strategies/{strategy['id']}/publish", json={"expected_revision": 2}
        ).status_code
        == 201
    )
    assert client.get(path).json()[1]["reply_json"]["provider_request_id"] == "fixture-request"
    assert client.get("/api/llm/proposals/" + proposal["id"]).status_code == 200
    assert (
        client.post(
            path, json={"request_id": "stale", "expected_revision": 1, "message": "Change it"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            path, json={"request_id": "one", "expected_revision": 2, "message": "duplicate"}
        ).status_code
        == 409
    )


def test_failed_partial_reply_is_retained_without_proposal_or_secret(client, monkeypatch):
    configure(monkeypatch)
    strategy = draft(client)

    async def broken(*args):
        yield "delta", "Partial unvalidated thought"
        raise ValueError("Authorization: Bearer secret-must-not-escape")

    monkeypatch.setattr(chat_routes, "stream_reply", broken)
    path = f"/api/llm/strategies/{strategy['id']}/turns"
    response = client.post(
        path, json={"request_id": "failed", "expected_revision": 1, "message": "Clarify my sizing"}
    )
    assert events(response)[-1][0] == "error"
    assert "secret-must-not-escape" not in response.text
    saved = client.get(path).json()[0]
    assert saved["status"] == "failed" and saved["proposal_id"] is None
    assert saved["partial_text"] == "Partial unvalidated thought"
    assert client.get(f"/api/strategies/{strategy['id']}").json()["draft_revision"] == 1


def test_active_turn_and_abandoned_stream_recovery(client, database, monkeypatch):
    configure(monkeypatch)
    strategy = draft(client)
    with database() as db:
        row = StrategyChatTurn(
            strategy_id=strategy["id"],
            request_id="active",
            source_revision=1,
            user_text="SYNTHETIC",
            context_json={},
        )
        db.add(row)
        db.commit()
        identifier = row.id
    path = f"/api/llm/strategies/{strategy['id']}/turns"
    body = {"request_id": "next", "expected_revision": 1, "message": "Resume"}
    assert client.post(path, json=body).status_code == 409
    with database() as db:
        db.get(StrategyChatTurn, identifier).created_at = utcnow() - timedelta(minutes=6)
        db.commit()

    async def author(*args):
        answer = reply()
        yield "delta", answer.message
        yield "complete", {"reply": answer}

    monkeypatch.setattr(chat_routes, "stream_reply", author)
    assert events(client.post(path, json=body))[-1][0] == "complete"
    assert client.get(path).json()[0]["status"] == "interrupted"


def test_evidence_preview_filters_future_bars_and_rejects_future_cutoff(client, data):
    strategy = draft(client)
    dataset = client.post("/api/market-data/import", json=data.model_dump(mode="json")).json()
    cutoff = data.bars[2].available_at.isoformat()
    response = client.post(
        f"/api/llm/strategies/{strategy['id']}/context",
        json={"dataset_id": dataset["id"], "as_of": cutoff},
    )
    assert response.status_code == 200, response.text
    evidence = response.json()["evidence"][0]
    assert evidence["summary"][0]["visible_bars"] == 3
    assert evidence["summary"][0]["last_close_usd"] == str(data.bars[2].close)
    assert evidence["synthetic"]
    assert (
        client.post(
            f"/api/llm/strategies/{strategy['id']}/context",
            json={"as_of": (utcnow() + timedelta(days=2)).isoformat()},
        ).status_code
        == 422
    )


def test_earlier_cutoff_excludes_later_conversation_history(client, monkeypatch):
    configure(monkeypatch)
    strategy = draft(client)
    contexts = []

    async def author(context, history, message):
        contexts.append(history)
        answer = reply()
        yield "delta", answer.message
        yield "complete", {"reply": answer}

    monkeypatch.setattr(chat_routes, "stream_reply", author)
    path = f"/api/llm/strategies/{strategy['id']}/turns"
    for i, cutoff in enumerate(["2025-01-01T00:00:00Z", "2024-01-01T00:00:00Z"]):
        response = client.post(
            path,
            json={
                "request_id": str(i),
                "expected_revision": 1,
                "message": "How large?",
                "selection": {"as_of": cutoff},
            },
        )
        assert events(response)[-1][0] == "complete"
    assert contexts == [[], []]


def test_run_evidence_retains_original_rules_and_rejects_same_day_future_marks(
    client, database, data
):
    strategy = draft(client)
    version = client.post(
        f"/api/strategies/{strategy['id']}/publish", json={"expected_revision": 1}
    ).json()
    dataset = client.post("/api/market-data/import", json=data.model_dump(mode="json")).json()
    profile = client.post(
        "/api/backtest-profiles",
        json={
            "name": "SYNTHETIC evidence",
            "config": ProfileConfig(start_date="2020-01-02", end_date="2020-01-02").model_dump(
                mode="json"
            ),
        },
    ).json()
    with database() as db:
        row = BacktestRun(
            strategy_version_id=version["id"],
            profile_id=profile["id"],
            dataset_id=dataset["id"],
            profile_snapshot=profile["config"],
            provenance={"synthetic": True},
            status="completed",
            result={
                "metrics": {"ending_equity": "10000"},
                "equity": [{"timestamp": "2020-01-02T21:00:00Z"}],
            },
        )
        db.add(row)
        db.commit()
        identifier = row.id
    amended = {**strategy["draft"], "sizing": {"mode": "fixed_notional", "value": "500"}}
    assert (
        client.patch(
            f"/api/strategies/{strategy['id']}",
            json={
                "name": strategy["name"],
                "description": "SYNTHETIC amendment",
                "expected_revision": 1,
                "config": amended,
            },
        ).status_code
        == 200
    )
    path = f"/api/llm/strategies/{strategy['id']}/context"
    result = client.post(path, json={"run_ids": [identifier], "as_of": "2020-01-03T00:00:00Z"})
    assert result.status_code == 200, result.text
    context = result.json()
    assert context["draft"]["sizing"]["mode"] == "fixed_notional"
    assert context["evidence"][0]["summary"]["strategy_config"] == version["config"]
    assert context["evidence"][0]["summary"]["strategy_config_hash"] == version["config_hash"]
    assert (
        client.post(
            path, json={"run_ids": [identifier], "as_of": "2020-01-02T20:00:00Z"}
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "kind",
    [
        "clarify_with_config",
        "proposal_with_questions",
        "proposal_without_config",
        "estimate_without_evidence",
    ],
)
def test_invalid_conversation_states_never_form_a_proposal(kind):
    values = reply().model_dump(mode="json")
    if kind == "clarify_with_config":
        values["config"] = default_strategy().model_dump(mode="json")
    if kind == "proposal_with_questions":
        values.update(outcome="propose", config=default_strategy().model_dump(mode="json"))
    if kind == "proposal_without_config":
        values.update(outcome="propose", questions=[])
    if kind == "estimate_without_evidence":
        values["estimates"] = [
            {
                "estimate": "10%",
                "horizon": "month",
                "method": "guess",
                "uncertainty": "high",
                "evidence_ids": [],
            }
        ]
    with pytest.raises(ValueError):
        ChatReply.model_validate(values)


@pytest.mark.parametrize(
    "mode",
    [
        "clarify",
        "estimate",
        "invented_citation",
        "truncated",
        "refusal",
        "invalid_config",
        "http_error",
    ],
)
def test_streamed_provider_validates_final_state_and_citations(monkeypatch, mode):
    configure(monkeypatch)
    requested = []
    answer = reply().model_dump(mode="json")
    answer["message"] = 'Clarify "small" — then choose. 😊'
    if mode in ["estimate", "invented_citation"]:
        answer.update(
            outcome="discuss",
            questions=[],
            estimates=[
                {
                    "estimate": "A conditional increase is plausible, not guaranteed.",
                    "horizon": "Next month",
                    "method": "Hypothesis from supplied history",
                    "uncertainty": "High; not calibrated",
                    "evidence_ids": ["missing" if mode == "invented_citation" else "known"],
                }
            ],
        )
    if mode == "invalid_config":
        answer.update(outcome="propose", questions=[], config={"executable_code": "no"})
    raw = json.dumps(answer, ensure_ascii=True)
    frames = [{"choices": [{"delta": {"content": raw[i : i + 7]}}]} for i in range(0, len(raw), 7)]
    frames.append(
        {
            "choices": [
                {
                    "delta": {"refusal": "no"} if mode == "refusal" else {},
                    "finish_reason": "length" if mode == "truncated" else "stop",
                }
            ]
        }
    )
    stream = "".join("data: " + json.dumps(frame) + "\n\n" for frame in frames) + "data: [DONE]\n\n"

    def handle(request):
        requested.append(json.loads(request.content))
        return httpx.Response(403 if mode == "http_error" else 200, content=stream)

    original = httpx.AsyncClient
    monkeypatch.setattr(
        chat_provider.httpx,
        "AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handle)),
    )

    async def consume():
        return [
            item
            async for item in chat_provider.stream_reply(
                {"evidence": [{"id": "known"}]}, [], "Make sizing clear"
            )
        ]

    if mode in ["clarify", "estimate"]:
        output = asyncio.run(consume())
        assert output[-1][0] == "complete"
        assert "".join(value for kind, value in output if kind == "delta") == answer["message"]
    else:
        with pytest.raises(ValueError):
            asyncio.run(consume())
    assert requested[0]["stream"] is True
    assert requested[0]["response_format"]["json_schema"]["strict"] is True
