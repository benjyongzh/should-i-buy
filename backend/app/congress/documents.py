"""Bounded exact-source acquisition and review-only PDF text, never financial inference."""

import io
import json
import re
from datetime import UTC, datetime
from urllib.parse import quote

from sqlalchemy import select

from app.congress.evidence import HOUSE, checked, fetch, json_bytes, public_bound, retain
from app.models.entities import SourceArtifact


class SourceAccessDenied(Exception):
    pass


def cached_pdf(db, year, key):
    for row in db.scalars(
        select(SourceArtifact)
        .where(
            SourceArtifact.kind == "house_ptr",
            SourceArtifact.metadata_json["year"].as_integer() == year,
            SourceArtifact.metadata_json["document_id"].as_string() == key,
        )
        .order_by(SourceArtifact.created_at.desc())
        .execution_options(yield_per=50)
    ):
        if (
            row.metadata_json.get("year") == year
            and row.metadata_json.get("document_id") == key
            and row.metadata_json.get("http_status") == 200
        ):
            checked(db, row.id, "house_ptr")
            if row.body.lstrip().startswith(b"%PDF-"):
                return row
    return None


def extract_text(db, official):
    from pypdf import PdfReader

    warnings = []
    pages = []
    try:
        reader = PdfReader(io.BytesIO(official.body), strict=False)
        if reader.is_encrypted:
            raise ValueError("encrypted PDF requires separate review")
        if len(reader.pages) > 100:
            raise ValueError("PDF exceeds100-page extraction bound")
        chars = 0
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text(extraction_mode="layout") or ""
            chars += len(text)
            if chars > 1_000_000:
                raise ValueError("PDF text exceeds1M character extraction bound")
            pages.append({"page": number, "text": text})
        if not any(p["text"].strip() for p in pages):
            warnings.append(
                "No extractable text; scanned/image document requires manual transcription, not invented empty transactions"
            )
    except Exception as exc:
        pages = []
        warnings.append("Text extraction needs review: " + type(exc).__name__)
    # These are search candidates, not accepted security identities or trade rows.
    mentions = sorted(
        {m for p in pages for m in re.findall(r"\(([A-Z][A-Z0-9.\-]{0,9})\)", p["text"])}
    )
    payload = {
        "official_artifact_id": official.id,
        "official_hash": official.content_hash,
        "extractor": "pypdf7.0.0-layout-v1",
        "pages": pages,
        "ticker_mentions_unvalidated": mentions,
        "warnings": warnings,
        "reviewed": False,
        "transaction_rows_normalized": False,
    }
    return retain(
        db,
        official.source_url,
        "congress_pdf_text",
        json_bytes(payload),
        {
            "official_artifact_id": official.id,
            "official_hash": official.content_hash,
            "pages": len(pages),
            "warnings": warnings,
            "reviewed": False,
        },
    )


def acquire_pdf(db, item):
    row = cached_pdf(db, item.year, item.report_key)
    if row is None:
        row = fetch(
            db,
            f"{HOUSE}/public_disc/ptr-pdfs/{item.year}/{item.report_key}.pdf",
            "house_ptr",
            {"year": item.year, "document_id": item.report_key},
            max_bytes=32_000_000,
        )
    item.official_artifact_id = row.id
    if row.metadata_json.get("http_status") != 200 or not row.body.lstrip().startswith(b"%PDF-"):
        item.status = "failed"
        item.error = "Official response unavailable or not a PDF; retained as failure evidence"
        db.commit()
        if row.metadata_json.get("http_status") in (403, 429):
            raise SourceAccessDenied(
                "Source denied or rate-limited acquisition; stopped without bypass"
            )
        return
    item.status = "downloaded"
    item.error = None
    db.commit()  # Exact acquisition survives even when text extraction cannot finish.
    try:
        text = extract_text(db, row)
        item.text_artifact_id = text.id
        db.commit()
    except Exception as exc:
        db.rollback()
        item.error = "Raw PDF retained; text needs manual review: " + type(exc).__name__
        db.commit()


def archive_bound(db, item):
    official = checked(db, item.official_artifact_id, "house_ptr")
    # Existing verified exact-byte captures may be reused in the isolated copy.
    for row in db.scalars(
        select(SourceArtifact)
        .where(
            SourceArtifact.kind == "house_ptr_replay",
            SourceArtifact.metadata_json["year"].as_integer() == item.year,
            SourceArtifact.metadata_json["document_id"].as_string() == item.report_key,
        )
        .order_by(SourceArtifact.created_at)
        .execution_options(yield_per=50)
    ):
        if (
            row.metadata_json.get("year") == item.year
            and row.metadata_json.get("document_id") == item.report_key
        ):
            checked(db, row.id, "house_ptr_replay")
            stamp, findings = public_bound(official, row)
            if stamp is not None:
                item.replay_artifact_id = row.id
                item.clock_status = "verified"
                db.commit()
                return
    # A search target is not a publication clock. Verify the returned capture itself.
    target = item.request_payload["filing_date"].replace("-", "") + "235959"
    url = (
        "https://archive.org/wayback/available?url="
        + quote(official.source_url, safe="")
        + "&timestamp="
        + target
    )
    availability = fetch(
        db, url, "congress_archive_lookup", {"year": item.year, "document_id": item.report_key}
    )
    db.commit()
    if availability.metadata_json.get("http_status") in (403, 429):
        raise SourceAccessDenied("Archive access denied/rate-limited; automatic requests stopped")
    try:
        if availability.metadata_json["http_status"] != 200:
            raise ValueError("archive lookup HTTP failure")
        candidate = json.loads(availability.body).get("archived_snapshots", {}).get("closest", {})
        capture = candidate.get("timestamp", "")
        if (
            not candidate.get("available")
            or candidate.get("status") != "200"
            or not re.fullmatch(r"[0-9]{14}", capture)
        ):
            raise ValueError("no successful archival capture returned")
        stamp = datetime.strptime(capture, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        if stamp > datetime.now(UTC):
            raise ValueError("capture lies in the future")
        replay = fetch(
            db,
            f"https://web.archive.org/web/{capture}id_/{official.source_url}",
            "house_ptr_replay",
            {"year": item.year, "document_id": item.report_key, "capture": capture},
            max_bytes=32_000_000,
        )
        item.replay_artifact_id = replay.id
        if replay.metadata_json.get("http_status") in (403, 429):
            db.commit()
            raise SourceAccessDenied(
                "Archive replay denied/rate-limited; automatic requests stopped"
            )
        _, findings = public_bound(official, replay)
        item.clock_status = "unavailable" if findings else "verified"
        if findings:
            item.error = "; ".join(findings)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        item.clock_status = "unavailable"
        item.error = str(exc)[:1000]
    db.commit()
