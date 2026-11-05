import hashlib
from datetime import UTC, date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from pydantic import AwareDatetime, Field, TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.benchmarks import cash_benchmark
from app.analytics.periods import period_report
from app.api.routes import completed, dump, get
from app.db.session import get_db
from app.market_data.context import (
    CATALOG,
    ContextData,
    ContextFetch,
    ContextPoint,
    SeriesID,
    fetch_context,
)
from app.market_data.providers import csv_records
from app.models.entities import BacktestRun, ContextSnapshot
from app.schemas.domain import StrictModel, canonical_hash
from app.services.feature_inputs import as_feature, checked_context, context_content_hash

router = APIRouter(prefix="/api/research")


class ContextReview(StrictModel):
    acknowledge_publication_policy: Literal[True]
    review_note: str = Field(min_length=20, max_length=2000)


class ContextCSV(StrictModel):
    series_id: SeriesID
    source: str = Field(min_length=1, max_length=160)
    source_url: str = Field(pattern=r"^https?://", max_length=1000)
    availability_policy: str = Field(min_length=20, max_length=2000)
    observations_csv: str = Field(min_length=1, max_length=5_000_000)
    synthetic: bool = False
    missing_omitted: int = Field(default=0, ge=0, le=100000)


def retain_context(data: ContextData, db: Session) -> ContextSnapshot:
    payload = data.model_dump(mode="json")
    digest = context_content_hash(payload)
    row = db.scalar(select(ContextSnapshot).where(ContextSnapshot.content_hash == digest))
    if not row:
        row = ContextSnapshot(series_id=data.series_id, content_hash=digest, payload=payload)
        db.add(row)
        db.commit()
    return row


def summary(row: ContextSnapshot) -> dict:
    return {
        **dump(row, {"payload"}),
        **{k: v for k, v in row.payload.items() if k != "observations"},
        "observation_count": len(row.payload["observations"]),
    }


@router.get("/context/catalog")
def catalog():
    return [
        {
            "series_id": key,
            "name": value[0],
            "units": value[1],
            "frequency": value[2],
            "key_required": key not in ("VIX", "FEAR_GREED_US"),
            "manual_only": key == "FEAR_GREED_US",
        }
        for key, value in CATALOG.items()
    ]


@router.get("/context")
def snapshots(db: Session = Depends(get_db)):
    return [
        summary(row)
        for row in db.scalars(
            select(ContextSnapshot).order_by(ContextSnapshot.created_at.desc()).limit(500)
        )
    ]


@router.post("/context/fetch", status_code=201)
def ingest_context(body: ContextFetch, db: Session = Depends(get_db)):
    data = fetch_context(body)
    return summary(retain_context(data, db))


@router.post("/context/import-csv", status_code=201)
def ingest_context_csv(body: ContextCSV, db: Session = Depends(get_db)):
    points = []
    for record in csv_records(body.observations_csv):
        if record.get("available_at") and not record.get("release_date"):
            clock = TypeAdapter(AwareDatetime).validate_python(record["available_at"])
            record["release_date"] = str(clock.astimezone(ZoneInfo("America/New_York")).date())
        points.append(ContextPoint.model_validate(record))
    if not points:
        raise ValueError("External CSV has no observations")
    points.sort(key=lambda p: p.observation_date)
    name, units, frequency = CATALOG[body.series_id]
    data = ContextData(
        series_id=body.series_id,
        name=("SYNTHETIC · " if body.synthetic else "") + name,
        units=units,
        frequency=frequency,
        source=body.source,
        source_url=body.source_url,
        requested_start=points[0].observation_date,
        requested_end=points[-1].observation_date,
        retrieved_at=datetime.now(UTC),
        availability_policy=body.availability_policy,
        research_only=True,
        synthetic=body.synthetic,
        observations=points,
        missing_omitted=body.missing_omitted,
        source_hashes=[hashlib.sha256(body.observations_csv.encode()).hexdigest()],
    )
    return summary(retain_context(data, db))


@router.post("/context/{identifier}/approve", status_code=201)
def approve_context(identifier: str, body: ContextReview, db: Session = Depends(get_db)):
    source = get(db, ContextSnapshot, identifier)
    data = checked_context(source)
    if not data.research_only:
        raise ValueError("This snapshot is already strategy-eligible; select its existing revision")
    as_feature(data, source.content_hash)  # Unknown/invalid publication metadata cannot be waived.
    payload = data.model_dump(mode="json")
    payload.update(
        research_only=False,
        source_snapshot_id=source.id,
        source_snapshot_hash=source.content_hash,
        review_note=body.review_note,
        reviewed_at=datetime.now(UTC).isoformat(),
    )
    return summary(retain_context(ContextData.model_validate(payload), db))


@router.get("/context/{identifier}/export")
def export_context(identifier: str, db: Session = Depends(get_db)):
    row = get(db, ContextSnapshot, identifier)
    ContextData.model_validate(row.payload)
    # Preserve hashes of earlier snapshots when optional schema fields are added.
    if (
        canonical_hash({k: v for k, v in row.payload.items() if k != "retrieved_at"})
        != row.content_hash
    ):
        raise ValueError("Context snapshot hash mismatch")
    return {**dump(row, {"payload"}), "data": row.payload}


@router.get("/runs/{identifier}/cash-benchmark")
def cash_reference(identifier: str, db: Session = Depends(get_db)):
    run = get(db, BacktestRun, identifier)
    result = completed(db, identifier)
    return {
        "run_id": run.id,
        "synthetic": run.provenance["synthetic"],
        **cash_benchmark(result, run.profile_snapshot),
    }


@router.get("/runs/{identifier}/periods")
def periods(
    identifier: str,
    start: date | None = None,
    end: date | None = None,
    frequency: str = Query("year", pattern="^(year|quarter|month)$"),
    db: Session = Depends(get_db),
):
    run = get(db, BacktestRun, identifier)
    result = completed(db, identifier)
    return {
        "run_id": run.id,
        "research_label": run.profile_snapshot["research_label"],
        "provenance": run.provenance,
        "basis": "Continuous portfolio; each period begins at the preceding saved equity mark (first period uses starting capital). Positions and cash are not reset. Retrospective development analysis.",
        "periods": period_report(result, run.profile_snapshot, frequency, start, end),
    }
