"""Bounded House source acquisition and explicit canonical-ledger review."""

import json
from datetime import UTC, datetime
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes import get
from app.api.strategy_inputs import summary
from app.congress.contracts import HouseDocument, HouseIndex, LedgerApproval, LedgerRequest
from app.congress.evidence import (
    HOUSE,
    artifact_summary,
    checked,
    collect_document,
    fetch,
    index_rows,
    json_bytes,
    retain,
)
from app.congress.ledger import prepare
from app.db.session import get_db
from app.market_data.strategy_inputs import StrategyInput
from app.models.entities import SourceArtifact, StrategyInputRevision
from app.schemas.domain import canonical_hash
from app.services.strategy_inputs import checked_input, retain_input

router = APIRouter(prefix="/api/research/congress", tags=["Congress source review"])


@router.post("/house-index", status_code=201)
def collect_index(body: HouseIndex, db: Session = Depends(get_db)):
    if body.year > datetime.now(UTC).year:
        raise ValueError("index year cannot be in the future")
    try:
        row = fetch(
            db,
            f"{HOUSE}/public_disc/financial-pdfs/{body.year}FD.zip",
            "house_fd_index",
            {"year": body.year},
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            502, "House index acquisition failed; no inventory established"
        ) from exc
    db.commit()
    # Keep failed response evidence but do not claim a parseable report inventory.
    try:
        count = len(index_rows(row))
        error = None
    except (ValueError, KeyError, BadZipFile, ParseError) as exc:
        count = None
        error = "Official index could not be validated: " + type(exc).__name__
    return {**artifact_summary(row), "index_entries": count, "error": error}


@router.post("/house-documents", status_code=201)
def document(body: HouseDocument, db: Session = Depends(get_db)):
    try:
        return collect_document(db, body)
    except httpx.HTTPError as exc:
        raise HTTPException(
            502, "Official House PDF acquisition failed; no observation established"
        ) from exc


@router.get("/artifacts")
def artifacts(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    return [
        artifact_summary(row)
        for row in db.scalars(
            select(SourceArtifact)
            .where(SourceArtifact.kind.in_(["house_fd_index", "house_ptr", "house_ptr_replay"]))
            .order_by(SourceArtifact.created_at.desc())
            .limit(limit)
        )
    ]


@router.get("/artifacts/{identifier}")
def artifact(identifier: str, db: Session = Depends(get_db)):
    row = get(db, SourceArtifact, identifier)
    if row.kind not in (
        "house_fd_index",
        "house_ptr",
        "house_ptr_replay",
        "congress_inventory",
        "congress_pdf_text",
        "congress_archive_lookup",
        "senate_access",
        "senate_dom_search",
        "senate_dom_report",
        "senate_pdf",
        "senate_import",
    ):
        raise ValueError("not a Congress source response")
    checked(db, row.id, row.kind)
    is_pdf = (
        row.kind in ("house_ptr", "house_ptr_replay")
        and row.metadata_json.get("http_status") == 200
        and row.body.lstrip().startswith(b"%PDF-")
    )
    suffix = (
        "pdf"
        if is_pdf
        else "zip"
        if row.kind == "house_fd_index" and row.body.startswith(b"PK")
        else "raw"
    )
    return Response(
        row.body,
        media_type="application/pdf" if is_pdf else "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{row.id}.{suffix}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/ledgers", status_code=201)
def create_ledger(body: LedgerRequest, db: Session = Depends(get_db)):
    payload = prepare(db, body)
    raw = retain_input(db, StrategyInput.model_validate(payload["source"]), commit=False)
    payload["source"] = checked_input(raw).model_dump(mode="json")
    payload["raw_source_id"] = raw.id
    payload["raw_source_hash"] = raw.content_hash
    row = retain(
        db,
        "https://disclosures-clerk.house.gov/FinancialDisclosure",
        "congress_ledger",
        json_bytes(payload),
        {
            "policy_version": payload["policy_version"],
            "request_hash": canonical_hash(body.model_dump(mode="json")),
        },
    )
    db.commit()
    return ledger_detail(db, row)


def ledger_detail(db, row):
    checked(db, row.id, "congress_ledger")
    payload = json.loads(row.body)
    raw = get(db, StrategyInputRevision, payload["raw_source_id"])
    source = checked_input(raw)
    if (
        raw.content_hash != payload["raw_source_hash"]
        or source.model_dump(mode="json") != payload["source"]
    ):
        raise ValueError("canonical ledger/raw source lineage mismatch")
    approvals = []
    for candidate in db.scalars(
        select(SourceArtifact)
        .where(SourceArtifact.kind == "congress_approval")
        .order_by(SourceArtifact.created_at)
    ):
        if candidate.metadata_json.get("ledger_id") == row.id:
            checked(db, candidate.id, "congress_approval")
            data = json.loads(candidate.body)
            approved = get(db, StrategyInputRevision, data["approved_source_id"])
            checked_input(approved)
            if (
                data["ledger_hash"] != row.content_hash
                or approved.content_hash != data["approved_source_hash"]
            ):
                raise ValueError("canonical ledger approval content mismatch")
            approvals.append({**artifact_summary(candidate), "data": data})
    return {**artifact_summary(row), "data": payload, "approvals": approvals}


@router.get("/ledgers")
def ledgers(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(SourceArtifact)
        .where(SourceArtifact.kind == "congress_ledger")
        .order_by(SourceArtifact.created_at.desc())
        .limit(limit)
        .execution_options(yield_per=10)
    )
    return [
        {
            **artifact_summary(row),
            "name": json.loads(row.body)["request"]["name"],
            "blockers": json.loads(row.body)["blockers"],
        }
        for row in rows
    ]


@router.get("/ledgers/{identifier}")
def ledger(identifier: str, db: Session = Depends(get_db)):
    return ledger_detail(db, get(db, SourceArtifact, identifier))


@router.post("/ledgers/{identifier}/approve", status_code=201)
def approve(identifier: str, body: LedgerApproval, db: Session = Depends(get_db)):
    row = get(db, SourceArtifact, identifier)
    packet = ledger_detail(db, row)["data"]
    if packet["blockers"]:
        raise ValueError(
            "Canonical ledger has unresolved blockers; retain a corrected new ledger revision"
        )
    # Re-derive rather than trusting display fields or changing immutable raw rows.
    rebuilt = prepare(db, LedgerRequest.model_validate(packet["request"]))
    # Display names are excluded from the existing immutable source identity.
    rebuilt["source"]["name"] = packet["source"]["name"]
    if rebuilt != {
        k: v for k, v in packet.items() if k not in ("raw_source_id", "raw_source_hash")
    }:
        raise ValueError("canonical ledger derivation no longer matches retained evidence")
    raw = get(db, StrategyInputRevision, packet["raw_source_id"])
    data = checked_input(raw).model_dump(mode="json")
    data.update(
        reviewed=True,
        complete=True,
        parent_id=raw.id,
        parent_hash=raw.content_hash,
        review_note=body.review_note,
    )
    approved = retain_input(db, StrategyInput.model_validate(data), commit=False)
    payload = {
        "ledger_id": row.id,
        "ledger_hash": row.content_hash,
        "approved_source_id": approved.id,
        "approved_source_hash": approved.content_hash,
        "review": body.model_dump(mode="json"),
    }
    record = retain(
        db,
        row.source_url,
        "congress_approval",
        json_bytes(payload),
        {"ledger_id": row.id, "ledger_hash": row.content_hash},
    )
    db.commit()
    return {
        "approval": artifact_summary(record),
        "source": summary(approved),
        "ledger": ledger_detail(db, row),
    }
