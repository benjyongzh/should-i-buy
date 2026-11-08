"""SYNTHETIC full-inventory/access fixtures. All network responses are mocked."""

import io
from datetime import timedelta
from zipfile import ZipFile

import httpx
import pytest
from httpx import Client as HTTPClient
from pypdf import PdfWriter
from sqlalchemy import func, select
from sqlalchemy.exc import DatabaseError

from app.congress import evidence, jobs
from app.congress.collection_contracts import CollectionRequest
from app.congress.evidence import retain
from app.models.entities import (
    CongressCollection,
    SourceArtifact,
    StrategyInputRevision,
    utcnow,
)

ROOT = "/api/research/congress"


def index_bytes(year):
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(
            f"{year}FD.xml",
            f"<FinancialDisclosure><Member><First>SYNTHETIC Alice</First><Last>Fixture</Last><FilingType>P</FilingType><FilingDate>3/4/{year}</FilingDate><DocID>20000001</DocID><Year>{year}</Year></Member><Member><First>SYNTHETIC Bob</First><Last>Fixture</Last><FilingType>P</FilingType><FilingDate>3/5/{year}</FilingDate><DocID>8211111</DocID><Year>{year}</Year></Member><Member><First>SYNTHETIC Other</First><Last>Fixture</Last><FilingType>O</FilingType><FilingDate>3/5/{year}</FilingDate><DocID>10000001</DocID></Member></FinancialDisclosure>",
        )
    return buffer.getvalue()


def blank_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def mock_sources(monkeypatch, denied=False):
    real = HTTPClient
    calls = []

    def handler(request):
        calls.append(str(request.url))
        path = request.url.path
        if path.endswith("FD.zip"):
            return httpx.Response(200, content=index_bytes(int(path.rsplit("/", 1)[-1][:4])))
        if request.url.host == "efdsearch.senate.gov":
            return httpx.Response(403, text="SYNTHETIC access denied")
        if request.url.host == "archive.org":
            return httpx.Response(200, json={"archived_snapshots": {}})
        if path.endswith(".pdf"):
            return (
                httpx.Response(403, text="SYNTHETIC source refusal")
                if denied
                else httpx.Response(200, content=blank_pdf())
            )
        raise AssertionError(str(request.url))

    monkeypatch.setattr(
        evidence.httpx,
        "Client",
        lambda **kwargs: real(transport=httpx.MockTransport(handler), **kwargs),
    )
    monkeypatch.setattr(jobs, "REQUEST_PAUSE_SECONDS", 0)
    return calls


def create(client, **changes):
    payload = {
        "request_id": "SYNTHETIC-full-inventory",
        "start_year": 2018,
        "end_year": 2019,
        "chambers": ["house", "senate"],
        "supporting_years": [],
        "lookup_archives": True,
        "acknowledge_personal_noncommercial_use": True,
        **changes,
    }
    r = client.post(ROOT + "/collections", json=payload)
    assert r.status_code == 202, r.text
    return r.json(), payload


def finish(factory, maximum=20):
    for _ in range(maximum):
        if jobs.process_collection_one(factory) is None:
            return
    raise AssertionError("fixture acquisition did not reach terminal state")


def test_all_filers_seven_digit_ids_and_fail_closed_qualification(client, database, monkeypatch):
    calls = mock_sources(monkeypatch)
    row, body = create(client)
    assert client.post(ROOT + "/collections", json=body).json()["id"] == row["id"]
    finish(database)
    summary = client.get(ROOT + "/collections/" + row["id"]).json()
    assert (
        summary["status"] == "needs_review"
        and summary["total_discovered"] == 4
        and summary["documents_downloaded"] == 4
    )
    assert not summary["fully_qualified"] and summary["verified_archive_bounds"] == 0
    assert summary["state"]["senate_access"]["http_status"] == 403
    assert any("timestamp=20180304235959" in url for url in calls)
    items = client.get(ROOT + "/collections/" + row["id"] + "/items?limit=2").json()
    assert items["has_more"] and len(items["items"]) == 2
    filtered = client.get(ROOT + "/collections/" + row["id"] + "/items?reporter=Bob").json()
    assert len(filtered["items"]) == 2
    text = client.get(
        ROOT + "/collections/" + row["id"] + "/items/" + items["items"][0]["id"] + "/text"
    ).json()
    assert text["warnings"] and not text["transaction_rows_normalized"] and not text["reviewed"]
    with database() as db:
        assert db.scalar(select(func.count()).select_from(StrategyInputRevision)) == 0


def test_source_denial_stops_automatic_requests_and_resume_retains_evidence(
    client, database, monkeypatch
):
    calls = mock_sources(monkeypatch, denied=True)
    row, _ = create(client, start_year=2022, end_year=2022, chambers=["house"])
    finish(database)
    summary = client.get(ROOT + "/collections/" + row["id"]).json()
    assert summary["status"] == "blocked_access"
    assert len([u for u in calls if u.endswith(".pdf")]) == 1
    with database() as db:
        before = db.scalar(select(func.count()).select_from(SourceArtifact))
    mock_sources(monkeypatch)
    assert client.post(ROOT + "/collections/" + row["id"] + "/resume").status_code == 202
    finish(database)
    with database() as db:
        assert db.scalar(select(func.count()).select_from(SourceArtifact)) > before
    assert client.get(ROOT + "/collections/" + row["id"]).json()["documents_downloaded"] == 2


def test_cancel_and_request_scope_conflicts(client, database, monkeypatch):
    calls = mock_sources(monkeypatch)
    row, body = create(client)
    assert client.post(ROOT + "/collections", json={**body, "end_year": 2020}).status_code == 422
    assert (
        client.post(ROOT + "/collections/" + row["id"] + "/cancel").json()["status"] == "cancelled"
    )
    assert jobs.process_collection_one(database) is None and not calls
    assert client.post(ROOT + "/collections/" + row["id"] + "/resume").status_code == 202
    assert client.post(ROOT + "/collections/" + row["id"] + "/resume").status_code == 422


def test_stale_lease_resumes_and_rejects_mutated_queue_request(database, monkeypatch):
    mock_sources(monkeypatch)
    with database() as db:
        row = jobs.enqueue(
            db,
            CollectionRequest(
                request_id="SYNTHETIC-stale",
                start_year=2022,
                end_year=2022,
                chambers=["house"],
                acknowledge_personal_noncommercial_use=True,
            ),
        )
        row.status = "running"
        row.heartbeat_at = utcnow() - timedelta(minutes=10)
        row.worker_token = "old"
        db.commit()
        identifier = row.id
    claimed = jobs.claim(database)
    assert claimed and claimed[0] == identifier and claimed[1] != "old"
    with database() as db:
        row = db.get(CongressCollection, identifier)
        row.status = "queued"
        row.request_hash = "tampered"
        db.commit()
    jobs.process_collection_one(database)
    with database() as db:
        assert db.get(CongressCollection, identifier).status == "failed"


def test_senate_dom_import_never_assigns_historical_posting_time(client):
    packet = {
        "export_id": "SYNTHETIC-export",
        "part_number": 1,
        "total_parts": 1,
        "scope_note": "SYNTHETIC all-Senators PTR fixture2018–2025",
        "expected_report_count": 1,
        "pagination_complete": True,
        "search_pages": ["<table><tr><td>SYNTHETIC filer</td></tr></table>"],
        "reports": [
            {
                "url": "https://efdsearch.senate.gov/search/view/ptr/fixture-001/",
                "captured_at": "2026-01-01T00:00:00Z",
                "http_status": 200,
                "html": "<h1>SYNTHETIC Periodic Transaction Report</h1><table><tr><td>01/02/2020</td><td>SYNTHETIC asset</td></tr></table>",
            }
        ],
        "acknowledge_personal_noncommercial_use": True,
    }
    response = client.post(ROOT + "/senate-imports", json=packet)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert (
        not data["qualified"]
        and data["reports"][0]["public_at"] is None
        and len(data["blockers"]) == 2
    )
    assert client.post(ROOT + "/senate-imports", json=packet).json()["id"] == response.json()["id"]
    for html in [
        "<script>secret()</script>",
        '<input type="hidden" name="csrfmiddlewaretoken" value="SYNTHETIC">',
    ]:
        bad = {**packet, "search_pages": [html]}
        assert client.post(ROOT + "/senate-imports", json=bad).status_code == 422
    bad = {**packet, "reports": [{**packet["reports"][0], "url": "http://127.0.0.1/private"}]}
    assert client.post(ROOT + "/senate-imports", json=bad).status_code == 422


def test_cross_year_supporting_original_keeps_legacy_request_shape(client, database):
    from test_congress_ledger import packet

    from app.congress.contracts import LedgerRequest

    body = packet(database)
    assert "supporting_index_artifact_ids" not in LedgerRequest.model_validate(body).model_dump(
        mode="json"
    )
    with database() as db:
        original = db.get(SourceArtifact, body["observations"][0]["official_artifact_id"])
        archive = io.BytesIO()
        with ZipFile(archive, "w") as z:
            z.writestr(
                "2021FD.xml",
                "<FinancialDisclosure><Member><First>Fixture</First><Last>Filer</Last><FilingType>P</FilingType><FilingDate>2/28/2021</FilingDate><DocID>19999999</DocID></Member></FinancialDisclosure>",
            )
        prior = retain(
            db,
            "https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2021FD.zip",
            "house_fd_index",
            archive.getvalue(),
            {"year": 2021, "http_status": 200, "synthetic": True},
        )
        url = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2021/19999999.pdf"
        official = retain(
            db,
            url,
            "house_ptr",
            original.body,
            {"year": 2021, "document_id": "19999999", "http_status": 200, "synthetic": True},
        )
        capture = "20221023144300"
        archived = retain(
            db,
            f"https://web.archive.org/web/{capture}id_/{url}",
            "house_ptr_replay",
            original.body,
            {
                "year": 2021,
                "document_id": "19999999",
                "http_status": 200,
                "capture": capture,
                "memento_datetime": "Sun, 23 Oct 2022 14:43:00 GMT",
                "synthetic": True,
            },
        )
        db.commit()
        ids = (prior.id, official.id, archived.id)
    body["supporting_index_artifact_ids"] = [ids[0]]
    body["observations"][0].update(
        official_artifact_id=ids[1],
        replay_artifact_id=ids[2],
        filing_date="2021-02-28",
        transaction_date="2021-01-21",
        notification_date="2021-01-21",
    )
    body["observations"][1]["transaction_date"] = "2021-01-21"
    response = client.post(ROOT + "/ledgers", json=body)
    assert response.status_code == 201, response.text
    assert not response.json()["data"]["blockers"]
    assert len(response.json()["data"]["source"]["events"]) == 1
    body["supporting_index_artifact_ids"] = [body["index_artifact_id"]]
    assert client.post(ROOT + "/ledgers", json=body).status_code == 422


def test_text_failure_preserves_successful_raw_pdf(client, database, monkeypatch):
    from app.congress import documents

    mock_sources(monkeypatch)

    def broken(*args):
        raise ValueError("SYNTHETIC extraction failure")

    monkeypatch.setattr(documents, "extract_text", broken)
    row, _ = create(
        client, start_year=2022, end_year=2022, chambers=["house"], lookup_archives=False
    )
    finish(database)
    summary = client.get(ROOT + "/collections/" + row["id"]).json()
    assert summary["documents_downloaded"] == 2
    rows = client.get(ROOT + "/collections/" + row["id"] + "/items").json()["items"]
    assert all(
        r["official_artifact_id"] and not r["text_artifact_id"] and "Raw PDF retained" in r["error"]
        for r in rows
    )


def assert_postgres_collection_requests_immutable(factory):
    with factory() as db:
        row = jobs.enqueue(
            db,
            CollectionRequest(
                request_id="SYNTHETIC-PG-immutable",
                start_year=2022,
                end_year=2022,
                acknowledge_personal_noncommercial_use=True,
            ),
        )
        row.request_hash = "changed"
        with pytest.raises(DatabaseError, match="Immutable"):
            db.commit()
        db.rollback()
