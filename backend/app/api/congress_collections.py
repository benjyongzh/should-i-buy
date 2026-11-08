from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.routes import dump, get
from app.congress.collection_contracts import CollectionRequest
from app.congress.jobs import enqueue
from app.congress.senate import SenateImport, import_dom
from app.db.session import get_db
from app.models.entities import CongressCollection, CongressCollectionItem, SourceArtifact

router = APIRouter(prefix="/api/research/congress", tags=["Congress coverage"])


@router.post("/collections", status_code=202)
def create(body: CollectionRequest, db: Session = Depends(get_db)):
    return dump(enqueue(db, body), {"worker_token"})


@router.get("/collections")
def collections(db: Session = Depends(get_db)):
    return [
        dump(r, {"worker_token"})
        for r in db.scalars(
            select(CongressCollection).order_by(CongressCollection.created_at.desc()).limit(100)
        )
    ]


@router.get("/collections/{identifier}")
def detail(identifier: str, db: Session = Depends(get_db)):
    row = get(db, CongressCollection, identifier)
    counts = [
        {"chamber": c, "year": y, "status": s, "clock_status": k, "reports": n}
        for c, y, s, k, n in db.execute(
            select(
                CongressCollectionItem.chamber,
                CongressCollectionItem.year,
                CongressCollectionItem.status,
                CongressCollectionItem.clock_status,
                func.count(),
            )
            .where(CongressCollectionItem.collection_id == identifier)
            .group_by(
                CongressCollectionItem.chamber,
                CongressCollectionItem.year,
                CongressCollectionItem.status,
                CongressCollectionItem.clock_status,
            )
        )
    ]
    total = sum(x["reports"] for x in counts)
    downloaded = sum(x["reports"] for x in counts if x["status"] == "downloaded")
    verified = sum(x["reports"] for x in counts if x["clock_status"] == "verified")
    return {
        **dump(row, {"worker_token"}),
        "counts": counts,
        "total_discovered": total,
        "documents_downloaded": downloaded,
        "verified_archive_bounds": verified,
        "fully_qualified": False,
        "qualification": "Acquisition and extractable text are not strategy eligibility. Full coverage remains blocked until inventory gaps, Senate access, row/issuer/taxonomy review and public-clock/amendment lineage are resolved. Filing dates are never substituted for posting clocks.",
    }


@router.get("/collections/{identifier}/items")
def items(
    identifier: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    reporter: str = Query("", max_length=160),
    db: Session = Depends(get_db),
):
    get(db, CongressCollection, identifier)
    query = select(CongressCollectionItem).where(CongressCollectionItem.collection_id == identifier)
    if reporter:
        query = query.where(
            CongressCollectionItem.request_payload["reporter"]
            .as_string()
            .ilike("%" + reporter + "%")
        )
    rows = list(
        db.scalars(
            query.order_by(CongressCollectionItem.year, CongressCollectionItem.report_key)
            .offset(offset)
            .limit(limit + 1)
        )
    )
    return {
        "items": [dump(r) for r in rows[:limit]],
        "has_more": len(rows) > limit,
        "next_offset": offset + limit if len(rows) > limit else None,
    }


@router.get("/collections/{identifier}/items/{item_id}/text")
def text(identifier: str, item_id: str, db: Session = Depends(get_db)):
    import json

    from app.congress.evidence import checked

    item = get(db, CongressCollectionItem, item_id)
    if item.collection_id != identifier:
        raise ValueError("item is outside this collection")
    if not item.text_artifact_id:
        raise ValueError("no retained text extraction; inspect document failure")
    return json.loads(checked(db, item.text_artifact_id, "congress_pdf_text").body)


@router.post("/collections/{identifier}/cancel")
def cancel(identifier: str, db: Session = Depends(get_db)):
    row = get(db, CongressCollection, identifier)
    if row.status not in ("queued", "running"):
        raise ValueError("only an active collection can be cancelled")
    row.cancel_requested = True
    if row.status == "queued":
        row.status = "cancelled"
    db.commit()
    return dump(row, {"worker_token"})


@router.post("/collections/{identifier}/resume", status_code=202)
def resume(identifier: str, db: Session = Depends(get_db)):
    row = get(db, CongressCollection, identifier)
    if row.status in ("queued", "running"):
        raise ValueError("collection is already active")
    row.state = {
        **row.state,
        "house_inventories": {
            k: v for k, v in row.state.get("house_inventories", {}).items() if not v.get("error")
        },
    }
    if row.state.get("senate_access", {}).get("state") in (
        "blocked_access",
        "blocked_network",
        "acknowledgement_required",
    ):
        row.state = {k: v for k, v in row.state.items() if k != "senate_access"}
    # Retry missing responses/bounds without deleting successful evidence or changing scope.
    db.execute(
        update(CongressCollectionItem)
        .where(
            CongressCollectionItem.collection_id == identifier,
            CongressCollectionItem.status == "failed",
        )
        .values(status="queued", error=None)
    )
    db.execute(
        update(CongressCollectionItem)
        .where(
            CongressCollectionItem.collection_id == identifier,
            CongressCollectionItem.clock_status == "unavailable",
        )
        .values(clock_status="unknown", error=None)
    )
    row.status = "queued"
    row.cancel_requested = False
    row.error = None
    row.completed_at = None
    row.worker_token = None
    db.commit()
    return dump(row, {"worker_token"})


@router.post("/senate-imports", status_code=201)
def import_senate(body: SenateImport, db: Session = Depends(get_db)):
    return import_dom(db, body)


@router.get("/senate-imports")
def senate_imports(db: Session = Depends(get_db)):
    import json

    return [
        {"id": r.id, "content_hash": r.content_hash, "data": json.loads(r.body)}
        for r in db.scalars(
            select(SourceArtifact)
            .where(SourceArtifact.kind == "senate_import")
            .order_by(SourceArtifact.created_at.desc())
            .limit(100)
        )
    ]
