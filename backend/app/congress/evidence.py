"""Retain exact fixed-host responses. Neither dates nor user URLs become public clocks."""

import hashlib
import io
import json
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree
from zipfile import ZipFile

import httpx
from sqlalchemy import select

from app.congress.contracts import HouseDocument
from app.core.config import settings
from app.models.entities import SourceArtifact
from app.schemas.domain import canonical_hash

HOUSE = "https://disclosures-clerk.house.gov"
MAX_BYTES = 4_000_000


def retain(db, url: str, kind: str, body: bytes, metadata: dict, *, max_bytes: int = MAX_BYTES):
    if len(body) > max_bytes:
        raise ValueError("Congress evidence exceeds the artifact byte bound")
    metadata = {**metadata, "bytes": len(body)}
    digest = hashlib.sha256(body).hexdigest()
    fingerprint = canonical_hash({"url": url, "kind": kind, "hash": digest, "metadata": metadata})
    row = db.scalar(select(SourceArtifact).where(SourceArtifact.fingerprint == fingerprint))
    if row is None:
        row = SourceArtifact(
            source_url=url,
            kind=kind,
            body=body,
            metadata_json=metadata,
            content_hash=digest,
            fingerprint=fingerprint,
        )
        db.add(row)
        db.flush()
    return row


def checked(db, identifier: str, kind: str):
    row = db.get(SourceArtifact, identifier)
    if row is None or row.kind != kind:
        raise ValueError("required retained Congress evidence artifact not found")
    expected = canonical_hash(
        {
            "url": row.source_url,
            "kind": row.kind,
            "hash": row.content_hash,
            "metadata": row.metadata_json,
        }
    )
    if hashlib.sha256(row.body).hexdigest() != row.content_hash or expected != row.fingerprint:
        raise ValueError("Congress evidence bytes/metadata hash mismatch")
    return row


def fetch(db, url: str, kind: str, labels: dict, *, max_bytes: int = MAX_BYTES):
    # Callers construct fixed official/replay URLs. No redirects or user URL fetching.
    headers = {
        "User-Agent": "TradingLab-source-review/1.0"
        + (
            " " + settings().data_source_contact_email
            if settings().data_source_contact_email
            else ""
        )
    }
    with (
        httpx.Client(
            timeout=httpx.Timeout(30, connect=10), follow_redirects=False, headers=headers
        ) as client,
        client.stream("GET", url) as response,
    ):
        chunks = []
        size = 0
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > max_bytes:
                raise ValueError("Congress HTTP response exceeds the artifact byte bound")
            chunks.append(chunk)
        metadata = {
            **labels,
            "retrieved_at": datetime.now(UTC).isoformat(),
            "http_status": response.status_code,
            "content_type": response.headers.get("Content-Type"),
            "memento_datetime": response.headers.get("Memento-Datetime"),
            "last_modified": response.headers.get("Last-Modified"),
            "clock_origin": "exact response capture; not filing/signature/Last-Modified",
        }
        return retain(db, url, kind, b"".join(chunks), metadata, max_bytes=max_bytes)


def collect_document(db, request: HouseDocument):
    if request.year > datetime.now(UTC).year:
        raise ValueError("document year cannot be in the future")
    capture = (
        datetime.strptime(request.archive_capture, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        if request.archive_capture
        else None
    )
    if capture and capture > datetime.now(UTC):
        raise ValueError("archive capture cannot be in the future")
    url = f"{HOUSE}/public_disc/ptr-pdfs/{request.year}/{request.document_id}.pdf"
    labels = {"year": request.year, "document_id": request.document_id}
    official = fetch(db, url, "house_ptr", labels)
    # Commit successful acquisition even if the separate replay request fails.
    db.commit()
    replay = None
    error = None
    if request.archive_capture:
        try:
            replay = fetch(
                db,
                f"https://web.archive.org/web/{request.archive_capture}id_/{url}",
                "house_ptr_replay",
                {**labels, "capture": request.archive_capture},
            )
            db.commit()
        except (httpx.HTTPError, ValueError) as exc:
            error = type(exc).__name__ + ": replay acquisition failed; no public clock established"
    clock, findings = public_bound(official, replay)
    if error:
        findings.append(error)
    return {
        "official_artifact_id": official.id,
        "replay_artifact_id": replay.id if replay else None,
        "document_id": request.document_id,
        "verified_public_observation": clock.isoformat() if clock else None,
        "findings": findings,
        "policy": "Conservative observation of exact PDF bytes; not certified first-public publication.",
    }


def public_bound(official, replay):
    findings = []
    if official.metadata_json.get("http_status") != 200 or not official.body.lstrip().startswith(
        b"%PDF-"
    ):
        findings.append("Official response is not a successful PDF")
    expected = f"{HOUSE}/public_disc/ptr-pdfs/{official.metadata_json.get('year')}/{official.metadata_json.get('document_id')}.pdf"
    if official.source_url != expected:
        findings.append("Official document identity/URL mismatch")
    if replay is None:
        return None, [
            *findings,
            "No verified archival observation; filing dates are not public clocks",
        ]
    if (
        replay.metadata_json.get("http_status") != 200
        or replay.content_hash != official.content_hash
        or replay.body != official.body
    ):
        findings.append("Replay must be HTTP200 and exactly match retained official PDF bytes")
    capture = replay.metadata_json.get("capture", "")
    try:
        stamp = datetime.strptime(capture, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        memento = parsedate_to_datetime(replay.metadata_json.get("memento_datetime") or "")
        if memento.tzinfo is None or memento != stamp or stamp > datetime.now(UTC):
            findings.append("Replay Memento clock does not match the historical capture")
    except (ValueError, TypeError, OverflowError):
        stamp = None
        findings.append("Missing or invalid replay capture/Memento clock")
    if replay.source_url != f"https://web.archive.org/web/{capture}id_/{expected}" or any(
        replay.metadata_json.get(k) != official.metadata_json.get(k)
        for k in ("year", "document_id")
    ):
        findings.append("Replay document identity/URL mismatch")
    return (None if findings else stamp), findings


def index_rows(row):
    if (
        row.metadata_json.get("http_status") != 200
        or row.source_url
        != f"{HOUSE}/public_disc/financial-pdfs/{row.metadata_json.get('year')}FD.zip"
    ):
        raise ValueError("official House index identity/response mismatch")
    with ZipFile(io.BytesIO(row.body)) as archive:
        name = f"{row.metadata_json['year']}FD.xml"
        info = archive.getinfo(name)
        if info.file_size > 8_000_000 or len(archive.infolist()) > 10:
            raise ValueError("House index exceeds archive limits")
        body = archive.read(info)
    if b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise ValueError("House index DTD/entity declarations are unsupported")
    root = ElementTree.fromstring(body)
    return [{child.tag: child.text or "" for child in record} for record in root]


def artifact_summary(row):
    return {
        "id": row.id,
        "kind": row.kind,
        "source_url": row.source_url,
        "content_hash": row.content_hash,
        "metadata": row.metadata_json,
    }


def json_bytes(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
