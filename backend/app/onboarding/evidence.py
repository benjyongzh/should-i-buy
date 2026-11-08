import hashlib
import re
from datetime import datetime
from html.parser import HTMLParser

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import IntakeArtifact, SourceArtifact
from app.schemas.domain import canonical_hash


def retain_artifact(db: Session, intake_id: str, url: str, kind: str, body: bytes, metadata: dict):
    if len(body) > settings().intake_max_artifact_bytes:
        raise ValueError("source document exceeds intake artifact size limit")
    digest = hashlib.sha256(body).hexdigest()
    metadata = {**metadata, "bytes": len(body)}
    fingerprint = canonical_hash({"url": url, "kind": kind, "hash": digest, "metadata": metadata})
    row = db.scalar(select(SourceArtifact).where(SourceArtifact.fingerprint == fingerprint))
    if row is None:
        row = SourceArtifact(
            source_url=url,
            kind=kind,
            content_hash=digest,
            fingerprint=fingerprint,
            metadata_json=metadata,
            body=body,
        )
        db.add(row)
        db.flush()
    if db.get(IntakeArtifact, (intake_id, row.id)) is None:
        db.add(IntakeArtifact(intake_id=intake_id, artifact_id=row.id))
    db.commit()
    return row


def checked_artifact(db: Session, intake_id: str, identifier: str):
    if db.get(IntakeArtifact, (intake_id, identifier)) is None:
        raise ValueError("evidence artifact does not belong to this intake")
    row = db.get(SourceArtifact, identifier)
    if row is None or hashlib.sha256(row.body).hexdigest() != row.content_hash:
        raise ValueError("source artifact content hash mismatch")
    expected = canonical_hash(
        {
            "url": row.source_url,
            "kind": row.kind,
            "hash": row.content_hash,
            "metadata": row.metadata_json,
        }
    )
    if row.fingerprint != expected:
        raise ValueError("source artifact metadata hash mismatch")
    return row


class DocumentText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, value):
        if not self.hidden:
            self.parts.append(value)


def plain_text(body: bytes) -> str:
    parser = DocumentText()
    parser.feed(body.decode("utf-8", "replace"))
    return " ".join(" ".join(parser.parts).split())


def date_in_text(day, text):
    candidates = {
        day.isoformat(),
        f"{day:%B} {day.day}, {day.year}",
        f"{day:%b} {day.day}, {day.year}",
    }
    text = re.sub(r"\s*,\s*", ", ", text.replace("Sept.", "Sep").replace(".", ""))
    return any(candidate in text for candidate in candidates)


def source_available_at(artifact):
    value = artifact.metadata_json.get("available_at")
    return datetime.fromisoformat(value) if value else None
