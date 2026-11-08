"""Company requests and explicit review; source credentials remain server-side."""

from uuid import uuid4

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes import dump, get
from app.core.config import settings
from app.db.session import get_db
from app.models.entities import (
    CompanyIntake,
    CompanyPackage,
    IntakeArtifact,
    IntakeReport,
    SourceArtifact,
    utcnow,
)
from app.onboarding.contracts import SUPPORTED, EvidenceUpload, IntakeRequest, IntakeReview
from app.onboarding.evidence import checked_artifact, retain_artifact
from app.onboarding.jobs import enqueue
from app.onboarding.review import approve, checked_report
from app.schemas.domain import canonical_hash

router = APIRouter(prefix="/api/company-intakes")


def artifact_summary(row):
    return {
        "id": row.id,
        "source_url": row.source_url,
        "kind": row.kind,
        "content_hash": row.content_hash,
        "metadata": row.metadata_json,
    }


@router.get("/configuration")
def configuration():
    config = settings()
    return {
        "supported": sorted(SUPPORTED),
        "configured": {
            "sec_contact": bool(config.data_source_contact_email),
            "alpaca": bool(
                config.alpaca_api_key.get_secret_value()
                and config.alpaca_secret_key.get_secret_value()
            ),
        },
        "limits": {
            "bytes": config.intake_max_bytes,
            "artifact_bytes": config.intake_max_artifact_bytes,
            "seconds": config.intake_max_seconds,
            "days_including_warmup": 5000,
        },
        "note": "Historical daily accounting and SEC 8-K/8-K/A filing presence only. Collection is not approval; package scope is not strategy readiness.",
    }


@router.get("")
def list_intakes(db: Session = Depends(get_db)):
    return [
        dump(r, {"worker_token"})
        for r in db.scalars(
            select(CompanyIntake).order_by(CompanyIntake.created_at.desc()).limit(200)
        )
    ]


@router.post("", status_code=201)
def create(body: IntakeRequest, db: Session = Depends(get_db)):
    return dump(enqueue(db, body), {"worker_token"})


@router.get("/{identifier}")
def detail(identifier: str, db: Session = Depends(get_db)):
    intake = get(db, CompanyIntake, identifier)
    report = db.scalar(select(IntakeReport).where(IntakeReport.intake_id == identifier))
    packages = list(
        db.scalars(select(CompanyPackage).where(CompanyPackage.intake_id == identifier))
    )
    for package in packages:
        if canonical_hash(package.payload) != package.content_hash:
            raise ValueError("company package content hash mismatch")
    return {
        **dump(intake, {"worker_token"}),
        "report": {
            "id": report.id,
            "content_hash": report.content_hash,
            "payload": checked_report(report),
        }
        if report
        else None,
        "artifacts": [
            artifact_summary(r)
            for r in db.scalars(
                select(SourceArtifact)
                .join(IntakeArtifact, SourceArtifact.id == IntakeArtifact.artifact_id)
                .where(IntakeArtifact.intake_id == identifier)
            )
        ],
        "packages": [dump(p) for p in packages],
    }


@router.post("/{identifier}/cancel")
def cancel(identifier: str, db: Session = Depends(get_db)):
    row = get(db, CompanyIntake, identifier)
    if row.status not in {"queued", "running"}:
        raise ValueError("only queued or running collections can be cancelled")
    row.cancel_requested = True
    if row.status == "queued":
        row.status, row.completed_at = "cancelled", utcnow()
    db.commit()
    return dump(row, {"worker_token"})


@router.post("/{identifier}/retry", status_code=201)
def retry(identifier: str, db: Session = Depends(get_db)):
    row = get(db, CompanyIntake, identifier)
    if row.status not in {"failed", "cancelled", "awaiting_review"}:
        raise ValueError("wait for this attempt to finish or cancel it before retrying")
    if canonical_hash(row.request_payload) != row.request_hash:
        raise ValueError("intake request content hash mismatch")
    body = {**row.request_payload, "idempotency_key": str(uuid4()), "refresh": True}
    return dump(enqueue(db, IntakeRequest.model_validate(body)), {"worker_token"})


@router.post("/{identifier}/evidence", status_code=201)
def evidence(identifier: str, body: EvidenceUpload, db: Session = Depends(get_db)):
    intake = get(db, CompanyIntake, identifier)
    if intake.status != "awaiting_review" or body.symbol not in {
        intake.request_payload["symbol"],
        intake.request_payload["benchmark"],
    }:
        raise ValueError("upload evidence for a requested symbol after collection finishes")
    # User-supplied URLs are provenance labels, never server fetch targets.
    artifacts = list(
        db.scalars(
            select(SourceArtifact)
            .join(IntakeArtifact, SourceArtifact.id == IntakeArtifact.artifact_id)
            .where(IntakeArtifact.intake_id == identifier)
        )
    )
    if (
        len(artifacts) >= 500
        or sum(r.metadata_json["bytes"] for r in artifacts) + len(body.text.encode())
        > settings().intake_max_bytes
    ):
        raise ValueError("intake evidence budget exhausted")
    row = retain_artifact(
        db,
        identifier,
        body.source_url,
        "issuer_evidence",
        body.text.encode(),
        {
            "symbol": body.symbol,
            "title": body.title,
            "available_at": body.available_at.isoformat(),
            "clock_policy": body.clock_policy,
            "origin": "reviewer supplied transcript; not independently fetched",
        },
    )
    return artifact_summary(row)


@router.get("/{identifier}/artifacts/{artifact_id}")
def download(identifier: str, artifact_id: str, db: Session = Depends(get_db)):
    get(db, CompanyIntake, identifier)
    row = checked_artifact(db, identifier, artifact_id)
    return Response(
        row.body,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="evidence-{row.id}.txt"',
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'",
        },
    )


@router.post("/{identifier}/approve", status_code=201)
def review(identifier: str, body: IntakeReview, db: Session = Depends(get_db)):
    return dump(approve(db, get(db, CompanyIntake, identifier), body))
