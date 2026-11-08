"""Complete conversation recall and immutable publication transcripts; no engine inputs."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select

from app.models.entities import StrategyChatTurn, VersionConversation
from app.schemas.domain import canonical_hash


def serialized_turn(row):
    return {
        column.name: (
            (value.replace(tzinfo=UTC) if value.tzinfo is None else value).isoformat()
            if isinstance(value := getattr(row, column.name), datetime)
            else value
        )
        for column in row.__table__.columns
    }


def transcript_payload(strategy_id, version_id, turns, *, origin="publication", published_at=None):
    return {
        "conversation_id": strategy_id,
        "version_id": version_id,
        "origin": origin,
        "published_at": published_at,
        "through_sequence": max((t["sequence"] for t in turns), default=0),
        "turns": turns,
    }


def freeze_conversation(db, strategy, version):
    rows = list(
        db.scalars(
            select(StrategyChatTurn)
            .where(StrategyChatTurn.strategy_id == strategy.id)
            .order_by(StrategyChatTurn.sequence)
        )
    )
    if any(row.status == "streaming" for row in rows):
        raise HTTPException(409, "Wait for or stop the active conversation reply before publishing")
    payload = transcript_payload(
        strategy.id,
        version.id,
        [serialized_turn(row) for row in rows],
        published_at=version.created_at.isoformat(),
    )
    payload.update(
        strategy_config_hash=version.config_hash,
        draft_revision_at_publication=strategy.draft_revision,
        accepted_chat_turn_id=(strategy.llm_metadata or {}).get("chat_turn_id"),
        manual_edits_after_proposal=bool(
            (strategy.llm_metadata or {}).get("manually_edited_after_acceptance")
        ),
    )
    import json

    if len(json.dumps(payload)) > 20_000_000:
        raise ValueError(
            "publication transcript exceeds the snapshot size limit; history was not truncated"
        )
    db.add(
        VersionConversation(
            version_id=version.id,
            strategy_id=strategy.id,
            payload=payload,
            content_hash=canonical_hash(payload),
        )
    )


def recall_history(db, strategy_id, evidence):
    """Never silently drop older user intent. Exclude future facts explicitly."""
    rows = list(
        db.scalars(
            select(StrategyChatTurn)
            .where(
                StrategyChatTurn.strategy_id == strategy_id, StrategyChatTurn.status != "streaming"
            )
            .order_by(StrategyChatTurn.sequence)
        )
    )
    cutoff = datetime.fromisoformat(evidence["evidence_cutoff"])
    known = {item["id"] for item in evidence["evidence"]}
    messages, included, excluded, withheld = [], [], [], []
    for row in rows:
        recorded_cutoff = row.context_json.get("evidence_cutoff")
        clock = (
            datetime.fromisoformat(recorded_cutoff)
            if recorded_cutoff
            else (
                row.created_at.replace(tzinfo=UTC)
                if row.created_at.tzinfo is None
                else row.created_at
            )
        )
        if clock > cutoff:
            excluded.append(row.id)
            continue
        included.append(row.id)
        item = {"turn_id": row.id, "user_text": row.user_text}
        reply = row.reply_json or {}
        citations = set(reply.get("cited_evidence_ids", []))
        for estimate in reply.get("estimates", []):
            citations.update(estimate["evidence_ids"])
        if row.status == "completed" and citations.issubset(known):
            # Preserve conversational text AND proposed rule JSON. Only provider
            # accounting is omitted; input-budget admission never silently truncates history.
            item["reply_json"] = {
                k: v for k, v in reply.items() if k not in {"usage", "provider_request_id"}
            }
        else:
            item["reply_json"] = {
                "message": "Prior assistant reply was incomplete or used evidence no longer selected. Preserve user intent, but do not treat that reply as a fact or accepted change.",
                "outcome": "withheld",
            }
            withheld.append(row.id)
        messages.append(item)
    audit = {
        "conversation_id": strategy_id,
        "history_turn_ids": included,
        "excluded_future_turn_ids": excluded,
        "withheld_reply_turn_ids": withheld,
        "recall_mode": "all eligible prior user messages and conversational replies; no last-N window",
    }
    return messages, audit
