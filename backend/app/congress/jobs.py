"""Resumable acquisition batches with explicit access/clock gaps; never auto-approval."""

import logging
import time
from datetime import timedelta
from uuid import uuid4
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

import httpx
from sqlalchemy import func, select, text, update

from app.congress.collection_contracts import CollectionRequest
from app.congress.documents import SourceAccessDenied, acquire_pdf, archive_bound
from app.congress.evidence import fetch
from app.congress.inventory import house_inventory
from app.models.entities import CongressCollection, CongressCollectionItem, SourceArtifact, utcnow
from app.schemas.domain import canonical_hash

logger = logging.getLogger(__name__)
BATCH_SIZE = 12
REQUEST_PAUSE_SECONDS = 0.5


def enqueue(db, request: CollectionRequest):
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(71899323)"))
    payload = request.model_dump(mode="json")
    digest = canonical_hash(payload)
    prior = db.scalar(
        select(CongressCollection).where(CongressCollection.request_id == request.request_id)
    )
    if prior:
        if prior.request_hash != digest:
            raise ValueError("collection request identifier already used for different scope")
        return prior
    active = db.scalar(
        select(func.count())
        .select_from(CongressCollection)
        .where(CongressCollection.status.in_(["queued", "running"]))
    )
    if active >= 3:
        raise ValueError("Congress acquisition queue capacity reached")
    row = CongressCollection(
        request_id=request.request_id, request_hash=digest, request_payload=payload
    )
    db.add(row)
    db.commit()
    return row


def claim(factory):
    with factory() as db:
        # Restart resumes unfinished items. Acquired immutable evidence remains untouched.
        db.execute(
            update(CongressCollection)
            .where(
                CongressCollection.status == "running",
                CongressCollection.heartbeat_at < utcnow() - timedelta(minutes=5),
            )
            .values(status="queued", worker_token=None)
        )
        row = db.scalar(
            select(CongressCollection)
            .where(CongressCollection.status == "queued")
            .order_by(CongressCollection.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if row is None:
            return None
        token = str(uuid4())
        changed = db.execute(
            update(CongressCollection)
            .where(CongressCollection.id == row.id, CongressCollection.status == "queued")
            .values(status="running", worker_token=token, heartbeat_at=utcnow())
        )
        identifier = row.id
        db.commit()
        return (identifier, token) if changed.rowcount == 1 else None


class Cancelled(Exception):
    pass


def process_collection_one(factory):
    ownership = claim(factory)
    if not ownership:
        return None
    identifier, token = ownership

    def checkpoint():
        with factory() as db:
            row = db.get(CongressCollection, identifier)
            if row.worker_token != token or row.status != "running":
                raise Cancelled()
            if row.cancel_requested:
                raise Cancelled()
            db.execute(
                update(CongressCollection)
                .where(
                    CongressCollection.id == identifier, CongressCollection.worker_token == token
                )
                .values(heartbeat_at=utcnow())
            )
            db.commit()

    try:
        with factory() as db:
            row = db.get(CongressCollection, identifier)
            if canonical_hash(row.request_payload) != row.request_hash:
                raise ValueError("Congress request hash mismatch")
            request = CollectionRequest.model_validate(row.request_payload)
            state = dict(row.state)
            years = list(range(request.start_year, request.end_year + 1)) + request.supporting_years
            if "house" in request.chambers:
                inventories = dict(state.get("house_inventories", {}))
                pending = [year for year in years if str(year) not in inventories]
                if pending:
                    year = pending[0]
                    checkpoint()
                    try:
                        inventories[str(year)] = house_inventory(db, row, year)
                    except SourceAccessDenied:
                        raise
                    except (ValueError, KeyError, BadZipFile, ParseError, httpx.HTTPError) as exc:
                        db.rollback()
                        inventories[str(year)] = {
                            "year": year,
                            "error": type(exc).__name__
                            + (
                                ": " + str(exc)[:300]
                                if isinstance(exc, ValueError)
                                else ": index unavailable/unvalidated"
                            ),
                        }
                    row = db.get(CongressCollection, identifier)
                    state["house_inventories"] = inventories
                    row.state = state
                    row.status = "queued"
                    row.worker_token = None
                    db.commit()
                    return identifier
            if "senate" in request.chambers and "senate_access" not in state:
                checkpoint()
                try:
                    artifact = fetch(
                        db,
                        "https://efdsearch.senate.gov/search/home/",
                        "senate_access",
                        {"origin": "normal server access probe; no challenge bypass"},
                    )
                    state["senate_access"] = {
                        "artifact_id": artifact.id,
                        "http_status": artifact.metadata_json["http_status"],
                        "state": "acknowledgement_required"
                        if artifact.metadata_json["http_status"] == 200
                        else "blocked_access",
                        "qualified": False,
                    }
                except httpx.HTTPError:
                    state["senate_access"] = {"state": "blocked_network", "qualified": False}
                row.state = state
                db.commit()
            raw_bytes = db.scalar(
                select(
                    func.coalesce(func.sum(SourceArtifact.metadata_json["bytes"].as_integer()), 0)
                )
                .select_from(CongressCollectionItem)
                .join(
                    SourceArtifact, CongressCollectionItem.official_artifact_id == SourceArtifact.id
                )
                .where(CongressCollectionItem.collection_id == identifier)
            )
            if raw_bytes >= 4_000_000_000:
                row.status = "blocked_capacity"
                row.error = "Collection raw-byte budget reached4GB; use explicit smaller partitions"
                row.worker_token = None
                db.commit()
                return identifier
            row.phase = "documents"
            db.commit()
            items = list(
                db.scalars(
                    select(CongressCollectionItem)
                    .where(
                        CongressCollectionItem.collection_id == identifier,
                        CongressCollectionItem.status == "queued",
                    )
                    .order_by(CongressCollectionItem.year, CongressCollectionItem.report_key)
                    .limit(BATCH_SIZE)
                )
            )
            for item in items:
                checkpoint()
                if canonical_hash(item.request_payload) != item.request_hash:
                    raise ValueError("Congress item request hash mismatch")
                try:
                    acquire_pdf(db, item)
                except SourceAccessDenied:
                    raise
                except Exception as exc:
                    db.rollback()
                    item = db.get(CongressCollectionItem, item.id)
                    item.status = "failed"
                    item.error = (
                        type(exc).__name__
                        + ": document acquisition/extraction failed; retry retains evidence"
                    )
                    db.commit()
                time.sleep(REQUEST_PAUSE_SECONDS)
            remaining = db.scalar(
                select(func.count())
                .select_from(CongressCollectionItem)
                .where(
                    CongressCollectionItem.collection_id == identifier,
                    CongressCollectionItem.status == "queued",
                )
            )
            if remaining:
                checkpoint()
                row = db.get(CongressCollection, identifier)
                row.status = "queued"
                row.worker_token = None
                db.commit()
                return identifier
            if request.lookup_archives:
                row.phase = "archive_bounds"
                db.commit()
                items = list(
                    db.scalars(
                        select(CongressCollectionItem)
                        .where(
                            CongressCollectionItem.collection_id == identifier,
                            CongressCollectionItem.status == "downloaded",
                            CongressCollectionItem.clock_status == "unknown",
                        )
                        .order_by(CongressCollectionItem.year, CongressCollectionItem.report_key)
                        .limit(BATCH_SIZE)
                    )
                )
                for item in items:
                    checkpoint()
                    try:
                        archive_bound(db, item)
                    except SourceAccessDenied:
                        raise
                    except Exception as exc:
                        db.rollback()
                        item = db.get(CongressCollectionItem, item.id)
                        item.clock_status = "unavailable"
                        item.error = type(exc).__name__ + ": public bound not established"
                        db.commit()
                    time.sleep(REQUEST_PAUSE_SECONDS)
                remaining = db.scalar(
                    select(func.count())
                    .select_from(CongressCollectionItem)
                    .where(
                        CongressCollectionItem.collection_id == identifier,
                        CongressCollectionItem.status == "downloaded",
                        CongressCollectionItem.clock_status == "unknown",
                    )
                )
                if remaining:
                    checkpoint()
                    row = db.get(CongressCollection, identifier)
                    row.status = "queued"
                    row.worker_token = None
                    db.commit()
                    return identifier
            checkpoint()
            row = db.get(CongressCollection, identifier)
            row.status = "needs_review"
            row.phase = "review"
            row.completed_at = utcnow()
            row.worker_token = None
            db.commit()
    except SourceAccessDenied as exc:
        with factory() as db:
            db.execute(
                update(CongressCollection)
                .where(
                    CongressCollection.id == identifier, CongressCollection.worker_token == token
                )
                .values(
                    status="blocked_access",
                    worker_token=None,
                    error=str(exc),
                    completed_at=utcnow(),
                )
            )
            db.commit()
    except Cancelled:
        with factory() as db:
            db.execute(
                update(CongressCollection)
                .where(
                    CongressCollection.id == identifier, CongressCollection.worker_token == token
                )
                .values(status="cancelled", worker_token=None, completed_at=utcnow())
            )
            db.commit()
    except Exception as exc:
        logger.exception("congress_collection_failed", extra={"collection_id": identifier})
        with factory() as db:
            db.execute(
                update(CongressCollection)
                .where(
                    CongressCollection.id == identifier, CongressCollection.worker_token == token
                )
                .values(
                    status="failed",
                    worker_token=None,
                    error=type(exc).__name__ + ": acquisition stopped; existing evidence retained",
                    completed_at=utcnow(),
                )
            )
            db.commit()
    return identifier
