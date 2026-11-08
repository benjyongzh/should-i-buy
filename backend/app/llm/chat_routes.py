"""Strategy-scoped conversations: read context, stream commentary, retain reviewed proposals."""

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import dump, get
from app.core.config import settings
from app.db.session import get_db
from app.llm.chat_context import build_context
from app.llm.chat_contracts import ChatRequest, ChatSelection
from app.llm.chat_provider import CHAT_PROMPT_VERSION, conversation_messages, stream_reply
from app.llm.conversation_history import recall_history, serialized_turn
from app.models.entities import (
    LLMProposal,
    Strategy,
    StrategyChatTurn,
    StrategyConversation,
    VersionConversation,
    utcnow,
)
from app.schemas.domain import canonical_hash

router = APIRouter(prefix="/api/llm/strategies")
logger = logging.getLogger(__name__)


def event(kind, data):
    return f"event: {kind}\ndata: {json.dumps(data, ensure_ascii=True)}\n\n"


@router.post("/{identifier}/context")
def context(identifier: str, body: ChatSelection, db: Session = Depends(get_db)):
    return build_context(db, get(db, Strategy, identifier), body)


@router.get("/{identifier}/turns")
def turns(identifier: str, db: Session = Depends(get_db)):
    get(db, Strategy, identifier)
    rows = list(
        db.scalars(
            select(StrategyChatTurn)
            .where(StrategyChatTurn.strategy_id == identifier)
            .order_by(StrategyChatTurn.sequence.desc())
            .limit(100)
        )
    )
    return [dump(row) for row in reversed(rows)]


@router.get("/{identifier}/conversation")
def conversation(identifier: str, db: Session = Depends(get_db)):
    root = get(db, StrategyConversation, identifier)
    return {
        "id": root.strategy_id,
        "strategy_id": root.strategy_id,
        "created_at": root.created_at.isoformat(),
        "total_turns": db.scalar(
            select(func.count())
            .select_from(StrategyChatTurn)
            .where(StrategyChatTurn.strategy_id == identifier)
        ),
        "recall_mode": "all eligible prior conversational messages; never silent last-N truncation",
    }


@router.get("/{identifier}/history")
def history(
    identifier: str,
    after: int = Query(0, ge=0),
    through: int | None = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    get(db, StrategyConversation, identifier)
    boundary = (
        through
        if through is not None
        else db.scalar(
            select(func.max(StrategyChatTurn.sequence)).where(
                StrategyChatTurn.strategy_id == identifier, StrategyChatTurn.status != "streaming"
            )
        )
        or 0
    )
    rows = list(
        db.scalars(
            select(StrategyChatTurn)
            .where(
                StrategyChatTurn.strategy_id == identifier,
                StrategyChatTurn.sequence > after,
                StrategyChatTurn.sequence <= boundary,
                StrategyChatTurn.status != "streaming",
            )
            .order_by(StrategyChatTurn.sequence)
            .limit(limit + 1)
        )
    )
    return {
        "conversation_id": identifier,
        "version_id": None,
        "through_sequence": boundary,
        "snapshot_hash": None,
        "origin": "current_conversation_read_only_view",
        "turns": [serialized_turn(row) for row in rows[:limit]],
        "has_more": len(rows) > limit,
        "next_after": rows[limit - 1].sequence if len(rows) > limit else None,
    }


def version_snapshot(db, identifier, version_id):
    row = get(db, VersionConversation, version_id)
    if row.strategy_id != identifier:
        raise HTTPException(404, "Version does not belong to this strategy conversation")
    if canonical_hash(row.payload) != row.content_hash:
        raise ValueError("version conversation snapshot hash mismatch")
    return row


@router.get("/{identifier}/versions/{version_id}/conversation")
def version_conversation(
    identifier: str,
    version_id: str,
    after: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    row = version_snapshot(db, identifier, version_id)
    payload = row.payload
    page = [t for t in payload["turns"] if t["sequence"] > after][: limit + 1]
    return {
        **{key: value for key, value in payload.items() if key != "turns"},
        "snapshot_hash": row.content_hash,
        "turns": page[:limit],
        "has_more": len(page) > limit,
        "next_after": page[limit - 1]["sequence"] if len(page) > limit else None,
    }


@router.get("/{identifier}/versions/{version_id}/conversation/export")
def export_conversation(identifier: str, version_id: str, db: Session = Depends(get_db)):
    row = version_snapshot(db, identifier, version_id)
    return {"content_hash": row.content_hash, "data": row.payload}


@router.post("/{identifier}/turns")
def converse(identifier: str, body: ChatRequest, db: Session = Depends(get_db)):
    cfg = settings()
    if not cfg.llm_api_key.get_secret_value() or not cfg.llm_model:
        raise ValueError("LLM conversation is not configured on the server")
    strategy = db.scalar(select(Strategy).where(Strategy.id == identifier).with_for_update())
    if strategy is None:
        raise HTTPException(404, "Strategy not found")
    if strategy.draft_revision != body.expected_revision:
        raise HTTPException(409, "Save/reload the current draft before continuing its conversation")
    db.execute(
        update(StrategyChatTurn)
        .where(
            StrategyChatTurn.strategy_id == identifier,
            StrategyChatTurn.status == "streaming",
            StrategyChatTurn.created_at < utcnow() - timedelta(minutes=5),
        )
        .values(
            status="interrupted",
            error="Previous stream did not finish; no proposal retained",
            completed_at=utcnow(),
        )
    )
    duplicate = db.scalar(
        select(StrategyChatTurn).where(
            StrategyChatTurn.strategy_id == identifier,
            StrategyChatTurn.request_id == body.request_id,
        )
    )
    if duplicate:
        raise HTTPException(409, "This message is already retained; reload conversation history")
    if db.scalar(
        select(StrategyChatTurn.id).where(
            StrategyChatTurn.strategy_id == identifier, StrategyChatTurn.status == "streaming"
        )
    ):
        raise HTTPException(409, "A reply is still streaming for this strategy")
    evidence = build_context(db, strategy, body.selection)
    messages, recall = recall_history(db, identifier, evidence)
    evidence.update(recall)
    evidence.pop("context_hash")
    evidence["model"] = cfg.llm_model
    evidence["prompt_version"] = CHAT_PROMPT_VERSION
    evidence["context_hash"] = canonical_hash(evidence)
    conversation_messages(evidence, messages, body.message)
    sequence = (
        db.scalar(
            select(func.max(StrategyChatTurn.sequence)).where(
                StrategyChatTurn.strategy_id == identifier
            )
        )
        or 0
    ) + 1
    turn = StrategyChatTurn(
        strategy_id=identifier,
        sequence=sequence,
        request_id=body.request_id,
        source_revision=strategy.draft_revision,
        user_text=body.message,
        context_json=evidence,
    )
    db.add(turn)
    db.commit()
    turn_id, revision = turn.id, turn.source_revision
    factory = sessionmaker(bind=db.get_bind(), expire_on_commit=False)

    async def generate():
        partial = ""
        completed = False
        failure = "Reply interrupted; partial text is unvalidated and cannot change a strategy"
        try:
            yield event("context", {"turn_id": turn_id, "context": evidence})
            yield event(
                "status",
                {
                    "stage": "generating",
                    "message": "Discussing intent and checking for unresolved choices",
                },
            )
            async for kind, value in stream_reply(evidence, messages, body.message):
                if kind == "delta":
                    partial += value
                    yield event("delta", {"text": value})
                elif kind == "complete":
                    reply = value["reply"]
                    yield event(
                        "status",
                        {
                            "stage": "validating",
                            "message": "Validating the reply, citations and proposed rules",
                        },
                    )
                    with factory() as transaction:
                        row = get(transaction, StrategyChatTurn, turn_id)
                        proposal = None
                        if reply.outcome == "propose":
                            proposal = LLMProposal(
                                strategy_id=identifier,
                                source_revision=revision,
                                config=reply.config.model_dump(mode="json"),
                                metadata_json={
                                    "model": cfg.llm_model,
                                    "prompt_version": CHAT_PROMPT_VERSION,
                                    "chat_turn_id": turn_id,
                                    "context_hash": evidence["context_hash"],
                                    "blocked": False,
                                    "interpretation": reply.message,
                                    "assumptions": reply.assumptions,
                                    "data_requirements": reply.data_requirements,
                                    "unsupported_requests": [],
                                    "prompt": body.message,
                                    "evidence": evidence["evidence"],
                                },
                            )
                            transaction.add(proposal)
                            transaction.flush()
                            row.proposal_id = proposal.id
                        row.reply_json = {
                            **reply.model_dump(mode="json"),
                            "provider_request_id": value.get("provider_request_id"),
                            "usage": value.get("usage"),
                        }
                        row.partial_text = partial
                        row.status = "completed"
                        row.completed_at = utcnow()
                        stale = get(transaction, Strategy, identifier).draft_revision != revision
                        transaction.commit()
                        retained = dump(row)
                        proposed = dump(proposal) if proposal else None
                    completed = True
                    yield event(
                        "complete", {"turn": retained, "proposal": proposed, "stale": stale}
                    )
            if not completed:
                raise ValueError("Provider ended without a validated reply")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.info(
                "strategy_chat_failed", extra={"turn_id": turn_id, "error_type": type(exc).__name__}
            )
            # Never expose provider response bodies or arbitrary exception text.
            category = (
                "reply_schema_invalid"
                if isinstance(exc, ValidationError)
                else "provider_or_reply_error"
            )
            failure = f"Reply failed validation or connection ({category}). Partial text is not an accepted proposal; retry or clarify."
            yield event("error", {"turn_id": turn_id, "message": failure})
        finally:
            if not completed:
                with factory() as transaction:
                    row = get(transaction, StrategyChatTurn, turn_id)
                    row.status = "failed" if failure.startswith("Reply failed") else "interrupted"
                    row.partial_text = partial
                    row.error = failure
                    row.completed_at = datetime.now(UTC)
                    transaction.commit()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
