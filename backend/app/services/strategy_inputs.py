"""Retain, review and freeze strategy-capability source revisions."""

from sqlalchemy import select

from app.market_data.strategy_inputs import StrategyInput
from app.models.entities import StrategyInputRevision
from app.schemas.domain import canonical_hash


def input_hash(payload):
    body = {k: v for k, v in payload.items() if k != "name"}
    for field, keys in (
        ("bars", ("symbol", "start_at")),
        ("states", ("symbol", "effective_at", "available_at")),
        ("events", ("event_id",)),
    ):
        body[field] = sorted(body[field], key=lambda r: tuple(r[k] for k in keys))
    return canonical_hash(body)


def checked_input(row):
    data = StrategyInput.model_validate(row.payload)
    if input_hash(row.payload) != row.content_hash or data.kind != row.kind:
        raise ValueError("strategy input identity/content hash mismatch")
    return data


def retain_input(db, data):
    payload = data.model_dump(mode="json")
    digest = input_hash(payload)
    row = db.scalar(
        select(StrategyInputRevision).where(StrategyInputRevision.content_hash == digest)
    )
    if row is None:
        row = StrategyInputRevision(kind=data.kind, content_hash=digest, payload=payload)
        db.add(row)
        db.commit()
    return row


def resolve_inputs(db, identifiers):
    if len(identifiers) > 100 or len(identifiers) != len(set(identifiers)):
        raise ValueError("duplicate or excessive strategy input revisions")
    bindings, sources = [], []
    for identifier in identifiers:
        row = db.get(StrategyInputRevision, identifier)
        if row is None:
            raise ValueError("strategy input revision not found")
        source = checked_input(row)
        if not source.reviewed:
            raise ValueError("review a new eligible input revision before running")
        parent = db.get(StrategyInputRevision, source.parent_id)
        if parent is None or parent.content_hash != source.parent_hash:
            raise ValueError("strategy input review lineage mismatch")
        checked_input(parent)
        bindings.append(
            {
                "snapshot_id": row.id,
                "kind": row.kind,
                "content_hash": row.content_hash,
                "synthetic": source.synthetic,
            }
        )
        sources.append(source)
    return sorted(bindings, key=lambda b: b["snapshot_id"]), sources


def frozen_inputs(db, provenance):
    bindings = provenance.get("strategy_inputs", [])
    if canonical_hash({"bindings": bindings}) != provenance.get(
        "strategy_input_hash", canonical_hash({"bindings": []})
    ):
        raise ValueError("frozen strategy-input manifest mismatch")
    actual, sources = resolve_inputs(db, [b["snapshot_id"] for b in bindings])
    if actual != bindings:
        raise ValueError("frozen strategy input identity/hash mismatch")
    return sources
