"""User-exported normal Senate sessions: capture provenance, never invented posting clocks."""

import base64
from datetime import UTC, datetime
from html.parser import HTMLParser
from urllib.parse import urlparse

from pydantic import AwareDatetime, Field, model_validator

from app.congress.documents import extract_text
from app.congress.evidence import json_bytes, retain
from app.schemas.domain import StrictModel

ORIGIN = "https://efdsearch.senate.gov"


class SafeHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.unsafe = False
        self.links = []
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" or (
            tag == "input"
            and (
                a.get("type", "").lower() in ("hidden", "password")
                or any(x in a.get("name", "").lower() for x in ("csrf", "token", "password"))
            )
        ):
            self.unsafe = True
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag == "tr":
            self.row = []
        if tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_data(self, text):
        if self.cell is not None:
            self.cell.append(text)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join(" ".join(self.cell).split()))
            self.cell = None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def report_url(value):
    import re

    u = urlparse(value)
    if (
        u.scheme != "https"
        or u.netloc != "efdsearch.senate.gov"
        or u.query
        or u.fragment
        or not re.fullmatch(r"/search/view/(?:ptr|paper)/[A-Za-z0-9-]+/?", u.path)
    ):
        raise ValueError(
            "Senate report URL must be a normal same-origin PTR/paper report URL without tokens"
        )
    return value


class DOMReport(StrictModel):
    url: str = Field(max_length=1000)
    captured_at: AwareDatetime
    http_status: int = Field(ge=100, le=599)
    html: str | None = Field(default=None, max_length=2_000_000)
    pdf_base64: str | None = Field(default=None, max_length=5_400_000)

    @model_validator(mode="after")
    def origin_and_body(self):
        report_url(self.url)
        if self.captured_at > datetime.now(UTC):
            raise ValueError("browser capture time cannot be in the future")
        if (self.html is None) == (self.pdf_base64 is None):
            raise ValueError("supply exactly one sanitized HTML or PDF response body")
        return self


class SenateImport(StrictModel):
    export_id: str = Field(min_length=1, max_length=80)
    part_number: int = Field(ge=1, le=10000)
    total_parts: int = Field(ge=1, le=10000)
    scope_note: str = Field(min_length=20, max_length=4000)
    expected_report_count: int = Field(ge=0, le=100000)
    pagination_complete: bool
    search_pages: list[str] = Field(default_factory=list, max_length=200)
    reports: list[DOMReport] = Field(min_length=1, max_length=50)
    acknowledge_personal_noncommercial_use: bool

    @model_validator(mode="after")
    def bounds(self):
        if not self.acknowledge_personal_noncommercial_use:
            raise ValueError("source use acknowledgement required")
        if self.part_number > self.total_parts:
            raise ValueError("invalid export part numbering")
        if len({r.url for r in self.reports}) != len(self.reports):
            raise ValueError("duplicate report URLs in export part")
        return self


def import_dom(db, request: SenateImport):
    total = sum(len(x.encode()) for x in request.search_pages) + sum(
        len(r.html.encode()) if r.html is not None else len(r.pdf_base64) for r in request.reports
    )
    if total > 20_000_000:
        raise ValueError("Senate import exceeds20MB; export smaller parts")
    artifacts = []
    for html in request.search_pages:
        parser = SafeHTML()
        parser.feed(html)
        if parser.unsafe:
            raise ValueError("remove script/hidden/token fields before importing browser capture")
        row = retain(
            db,
            ORIGIN + "/search/",
            "senate_dom_search",
            html.encode(),
            {
                "origin": "user-exported sanitized browser DOM, not independently fetched",
                "export_id": request.export_id,
                "part_number": request.part_number,
                "public_at": None,
            },
        )
        artifacts.append(row.id)
    reports = []
    for report in request.reports:
        rows = []
        if report.html is not None:
            parser = SafeHTML()
            parser.feed(report.html)
            if parser.unsafe:
                raise ValueError(
                    "remove script/hidden/token fields before importing browser capture"
                )
            body = report.html.encode()
            kind = "senate_dom_report"
            rows = parser.rows
        else:
            body = base64.b64decode(report.pdf_base64, validate=True)
            kind = "senate_pdf"
            if not body.lstrip().startswith(b"%PDF-"):
                raise ValueError("paper report is not a PDF")
        row = retain(
            db,
            report.url,
            kind,
            body,
            {
                "origin": "user-exported normal Senate session; current capture only, not original posting",
                "export_id": request.export_id,
                "captured_at": report.captured_at.isoformat(),
                "http_status": report.http_status,
                "public_at": None,
                "reviewed": False,
            },
        )
        text_id = (
            extract_text(db, row).id if kind == "senate_pdf" and report.http_status == 200 else None
        )
        reports.append(
            {
                "artifact_id": row.id,
                "url": report.url,
                "http_status": report.http_status,
                "raw_table_rows_unreviewed": rows,
                "text_artifact_id": text_id,
                "public_at": None,
            }
        )
    payload = {
        "export_id": request.export_id,
        "part_number": request.part_number,
        "total_parts": request.total_parts,
        "scope_note": request.scope_note,
        "expected_report_count": request.expected_report_count,
        "pagination_complete": request.pagination_complete,
        "search_artifact_ids": artifacts,
        "reports": reports,
        "qualified": False,
        "blockers": [
            "Browser capture proves current access only; original historical posting clocks remain unknown",
            "All export parts, query scope, filer/issuer identities and original/amendment rows require review; no dates inferred from receipt/filing fields",
        ],
    }
    row = retain(
        db,
        ORIGIN + "/search/",
        "senate_import",
        json_bytes(payload),
        {"export_id": request.export_id, "part_number": request.part_number, "qualified": False},
    )
    db.commit()
    return {"id": row.id, "content_hash": row.content_hash, "data": payload}
