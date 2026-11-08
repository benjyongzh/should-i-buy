"""Durable collection queue with bounded work, cancellation and worker leases."""

import logging
import time
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, select, text, update

from app.core.config import settings
from app.models.entities import CompanyIntake, IntakeReport, utcnow
from app.onboarding.collect import collect
from app.onboarding.contracts import IntakeRequest
from app.schemas.domain import canonical_hash

logger = logging.getLogger(__name__)


class CollectionCancelled(Exception):
    pass


def enqueue(db, request: IntakeRequest):
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(71899322)"))
    payload = request.model_dump(mode="json")
    digest = canonical_hash(payload)
    existing = db.scalar(
        select(CompanyIntake).where(CompanyIntake.idempotency_key == request.idempotency_key)
    )
    if existing:
        if existing.request_hash != digest:
            raise ValueError("idempotency key already belongs to a different request")
        return existing
    active = db.scalar(
        select(func.count())
        .select_from(CompanyIntake)
        .where(CompanyIntake.status.in_(["queued", "running"]))
    )
    if active >= settings().max_active_jobs:
        raise ValueError("company collection queue is full; retry after pending work finishes")
    row = CompanyIntake(
        idempotency_key=request.idempotency_key, request_hash=digest, request_payload=payload
    )
    db.add(row)
    db.commit()
    return row


def claim(factory):
    with factory() as db:
        db.execute(
            update(CompanyIntake)
            .where(
                CompanyIntake.status == "running",
                CompanyIntake.heartbeat_at
                < utcnow() - timedelta(seconds=settings().worker_lease_seconds),
            )
            .values(
                status="failed",
                completed_at=utcnow(),
                worker_token=None,
                error="Collection worker lease expired; retry creates a new attempt and retains existing evidence.",
            )
        )
        identifier = db.scalar(
            select(CompanyIntake.id)
            .where(CompanyIntake.status == "queued", CompanyIntake.cancel_requested.is_(False))
            .order_by(CompanyIntake.created_at, CompanyIntake.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        token = str(uuid4())
        changed = None
        if identifier:
            changed = db.execute(
                update(CompanyIntake)
                .where(CompanyIntake.id == identifier, CompanyIntake.status == "queued")
                .values(status="running", worker_token=token, heartbeat_at=utcnow())
            )
        db.commit()
        return (identifier, token) if changed is not None and changed.rowcount == 1 else None


def process_intake_one(factory):
    ownership = claim(factory)
    if not ownership:
        return None
    identifier, token = ownership
    started = time.monotonic()

    def checkpoint():
        if time.monotonic() - started > settings().intake_max_seconds:
            raise ValueError(
                "Collection exceeded its configured time limit; shorten the requested interval"
            )
        with factory() as db:
            row = db.get(CompanyIntake, identifier)
            if row.status != "running" or row.worker_token != token or row.cancel_requested:
                raise CollectionCancelled()
            db.execute(
                update(CompanyIntake)
                .where(
                    CompanyIntake.id == identifier,
                    CompanyIntake.worker_token == token,
                    CompanyIntake.status == "running",
                )
                .values(heartbeat_at=utcnow())
            )
            db.commit()

    try:
        with factory() as db:
            row = db.get(CompanyIntake, identifier)
            if canonical_hash(row.request_payload) != row.request_hash:
                raise ValueError("intake request content hash mismatch")
            request = IntakeRequest.model_validate(row.request_payload)
            payload = collect(db, identifier, request, checkpoint)
            checkpoint()
            # Compare-and-set keeps a cancelled/expired worker from publishing its report.
            changed = db.execute(
                update(CompanyIntake)
                .where(
                    CompanyIntake.id == identifier,
                    CompanyIntake.worker_token == token,
                    CompanyIntake.status == "running",
                    CompanyIntake.cancel_requested.is_(False),
                )
                .values(
                    status="awaiting_review", progress=100, completed_at=utcnow(), worker_token=None
                )
            )
            if changed.rowcount != 1:
                raise CollectionCancelled()
            db.add(
                IntakeReport(
                    intake_id=identifier, content_hash=canonical_hash(payload), payload=payload
                )
            )
            db.commit()
    except Exception as exc:
        with factory() as db:
            db.execute(
                update(CompanyIntake)
                .where(
                    CompanyIntake.id == identifier,
                    CompanyIntake.worker_token == token,
                    CompanyIntake.status == "running",
                )
                .values(
                    status="cancelled" if isinstance(exc, CollectionCancelled) else "failed",
                    completed_at=utcnow(),
                    worker_token=None,
                    error=None
                    if isinstance(exc, CollectionCancelled)
                    else str(exc)[:1000]
                    if isinstance(exc, ValueError)
                    else "Collection failed; retained evidence is available. Review server logs and retry.",
                )
            )
            db.commit()
        if not isinstance(exc, (CollectionCancelled, ValueError)):
            logger.exception("company_collection_failed", extra={"intake_id": identifier})
    return identifier
