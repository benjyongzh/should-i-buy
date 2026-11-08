"""Full current-index inventory, not a claim of original public-release completeness."""

from datetime import datetime

from sqlalchemy import select

from app.congress.documents import SourceAccessDenied
from app.congress.evidence import HOUSE, checked, fetch, index_rows, json_bytes, retain
from app.models.entities import CongressCollectionItem, SourceArtifact
from app.schemas.domain import canonical_hash


def house_inventory(db, collection, year):
    index = db.scalar(
        select(SourceArtifact)
        .where(
            SourceArtifact.kind == "house_fd_index",
            SourceArtifact.metadata_json["year"].as_integer() == year,
            SourceArtifact.created_at >= collection.created_at,
        )
        .order_by(SourceArtifact.created_at.desc())
        .limit(1)
    )
    if index is not None:
        checked(db, index.id, "house_fd_index")
    else:
        index = fetch(
            db, f"{HOUSE}/public_disc/financial-pdfs/{year}FD.zip", "house_fd_index", {"year": year}
        )
    db.commit()
    if index.metadata_json.get("http_status") in (403, 429):
        raise SourceAccessDenied("House index denied/rate-limited; collection stopped")
    rows = index_rows(index)
    ptrs = []
    seen = set()
    for row in rows:
        if row.get("FilingType") != "P":
            continue
        key = row.get("DocID", "")
        if not (key.isdigit() and len(key) in (7, 8)):
            raise ValueError("invalid House PTR document identity")
        if key in seen:
            raise ValueError("duplicate PTR document in official annual index")
        seen.add(key)
        day = datetime.strptime(row["FilingDate"], "%m/%d/%Y").date()
        ptrs.append(
            {
                "document_id": key,
                "index_year": year,
                "filing_date": str(day),
                "reporter": (row.get("First", "") + " " + row.get("Last", "")).strip(),
                "official_url": f"{HOUSE}/public_disc/ptr-pdfs/{year}/{key}.pdf",
                "raw_index_row": row,
            }
        )
    payload = {
        "chamber": "house",
        "index_year": year,
        "index_artifact_id": index.id,
        "index_hash": index.content_hash,
        "current_download_not_original_vintage": True,
        "all_index_entries": len(rows),
        "ptr_reports": sorted(ptrs, key=lambda r: (r["filing_date"], r["document_id"])),
        "qualification": "unreviewed; neither posting clocks nor transaction identities inferred from filing dates",
    }
    manifest = retain(
        db,
        index.source_url,
        "congress_inventory",
        json_bytes(payload),
        {
            "chamber": "house",
            "year": year,
            "collection_id": collection.id,
            "report_count": len(ptrs),
        },
    )
    db.flush()
    for row in ptrs:
        prior = db.scalar(
            select(CongressCollectionItem.id).where(
                CongressCollectionItem.collection_id == collection.id,
                CongressCollectionItem.chamber == "house",
                CongressCollectionItem.year == year,
                CongressCollectionItem.report_key == row["document_id"],
            )
        )
        if prior:
            continue
        request = {**row, "inventory_artifact_id": manifest.id, "index_artifact_id": index.id}
        db.add(
            CongressCollectionItem(
                collection_id=collection.id,
                chamber="house",
                year=year,
                report_key=row["document_id"],
                request_payload=request,
                request_hash=canonical_hash(request),
            )
        )
    db.commit()
    return {
        "year": year,
        "index_artifact_id": index.id,
        "inventory_artifact_id": manifest.id,
        "entries": len(rows),
        "ptr_reports": len(ptrs),
    }
