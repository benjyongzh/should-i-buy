"""SYNTHETIC disclosure fixtures. No network or real financial outcomes invented."""

import io
from datetime import UTC, datetime
from email.utils import format_datetime
from zipfile import ZipFile

import httpx
import pytest

from app.congress import evidence
from app.congress.contracts import Observation
from app.congress.ledger import reconcile
from app.market_data.input_book import InputBook
from app.market_data.strategy_inputs import CongressDetails, StrategyInput
from app.schemas.domain import EventValue

BASE = "/api/research/congress"


def observation(**changes):
    return Observation.model_validate(
        {
            "observation_id": "original",
            "canonical_transaction_id": "fixture-transaction-one",
            "official_artifact_id": "official",
            "replay_artifact_id": "replay",
            "filing_date": "2022-02-28",
            "filing_kind": "original",
            "reporter": "Fixture Filer",
            "owner": "spouse",
            "symbol": "AAPL",
            "issuer_cik": "0000320193",
            "identity_evidence_url": "https://fixture.invalid/identity",
            "instrument": "call_option",
            "action": "option_exercise",
            "reported_transaction_code": "P",
            "reported_asset_type": "ST",
            "transaction_date": "2022-01-21",
            "notification_date": "2022-01-21",
            "amount_min": "1000001",
            "amount_max": "5000000",
            "shares": "10000",
            "option_contracts": "100",
            "strike_usd": "100",
            "row_reference": "SYNTHETIC row1",
            "row_transcript": "SYNTHETIC spouse option exercise, not a market purchase.",
            "reconciliation_note": "SYNTHETIC explicit canonical match against predecessor and row identity.",
            **changes,
        }
    )


def proof(clock, doc="10000001"):
    return {
        "clock": datetime.fromisoformat(clock.replace("Z", "+00:00")) if clock else None,
        "document_id": doc,
        "content_hash": "a" * 64,
        "replay_url": "https://fixture.invalid/archived.pdf",
    }


def amended(**changes):
    return observation(
        **{
            "observation_id": "amended",
            "filing_kind": "amendment",
            "filing_date": "2022-03-04",
            "notification_date": "2022-02-28",
            "amends_observation_id": "original",
            **changes,
        }
    )


def source(events):
    return StrategyInput(
        kind="events",
        name="SYNTHETIC canonical events",
        source="SYNTHETIC fixture",
        source_url="https://fixture.invalid",
        availability_policy="SYNTHETIC exact observation clocks; no real source certification.",
        synthetic=True,
        complete=True,
        reviewed=True,
        parent_id="fixture",
        parent_hash="a" * 64,
        review_note="SYNTHETIC reviewed fixture, not real source approval.",
        coverage_start="2022-01-01T00:00:00Z",
        coverage_end="2022-12-31T23:59:59Z",
        symbols=["AAPL"],
        stream_id="HOUSE_FIXTURE",
        events=events,
        category_catalog=[
            "congress_option_exercise",
            "congress_equity_purchase",
            "congress_equity_sale",
            "congress_charitable_transfer",
            *[tag for e in events for tag in e.tags],
        ],
    )


def value(data, events, clock, **kwargs):
    book = InputBook(data, [source(events)])
    node = EventValue(type="event", stream_id="HOUSE_FIXTURE", lookback_minutes=1440, **kwargs)
    return book.event_value(node, "AAPL", datetime.fromisoformat(clock.replace("Z", "+00:00")))[0]


def test_later_observed_original_cannot_duplicate_or_revert_amended_transaction(data):
    rows = [observation(), amended(amount_min="2000001")]
    events, audit, blockers = reconcile(
        rows,
        {
            "original": proof("2022-10-23T14:43:00Z"),
            "amended": proof("2022-03-07T20:36:50Z", "10000002"),
        },
    )
    assert not blockers and len(events) == 1
    event = events[0]
    assert event.published_at == datetime(2022, 3, 7, 20, 36, 50, tzinfo=UTC)
    assert event.details.transaction == "option_exercise" and event.details.amount_min == 2000001
    assert event.details.instrument == "call_option"
    assert (
        audit[-1]["disposition"] == "older_filing_observed_late" and audit[-1]["event_id"] is None
    )
    assert value(data, events, "2022-03-07T20:36:49Z", categories=["congress_option_exercise"]) == 0
    assert value(data, events, "2022-03-07T20:36:50Z", categories=["congress_option_exercise"]) == 1
    assert value(data, events, "2022-03-07T20:36:50Z", categories=["congress_equity_purchase"]) == 0
    assert value(data, events, "2022-10-23T14:43:01Z", categories=["congress_option_exercise"]) == 0


def test_metadata_only_amendment_does_not_restart_signal_lookback(data):
    events, audit, blockers = reconcile(
        [observation(), amended()],
        {
            "original": proof("2022-03-01T12:00:00Z"),
            "amended": proof("2022-03-07T20:36:50Z", "10000002"),
        },
    )
    assert len(events) == 1 and not blockers
    assert audit[-1]["disposition"] == "metadata_only_amendment"
    assert value(data, events, "2022-03-07T21:00:00Z", categories=["congress_option_exercise"]) == 0


def test_real_economic_correction_is_causal_supersession_with_stable_prefix(data):
    rows = [observation(), amended(amount_min="2000001")]
    proofs = {
        "original": proof("2022-03-07T12:00:00Z"),
        "amended": proof("2022-03-07T18:00:00Z", "10000002"),
    }
    first = reconcile(rows[:1], proofs)[0]
    events, _, _ = reconcile(rows, proofs)
    assert events[0].model_dump() == first[0].model_dump()
    assert events[1].supersedes_event_id == events[0].event_id
    assert (
        value(
            data,
            events,
            "2022-03-07T17:59:59Z",
            categories=["congress_option_exercise"],
            measure="latest_score",
            value_field="congress_amount_min",
        )
        == 1000001
    )
    assert (
        value(
            data,
            events,
            "2022-03-07T18:00:00Z",
            categories=["congress_option_exercise"],
            measure="latest_score",
            value_field="congress_amount_min",
        )
        == 2000001
    )
    assert value(data, events, "2022-03-07T18:00:00Z", categories=["congress_option_exercise"]) == 1


def test_two_identical_gifts_keep_distinct_canonical_identities(data):
    rows = [
        observation(
            observation_id="gift1",
            canonical_transaction_id="gift-one",
            instrument="equity",
            action="charitable_transfer",
            reported_transaction_code="S (partial)",
        ),
        observation(
            observation_id="gift2",
            canonical_transaction_id="gift-two",
            instrument="equity",
            action="charitable_transfer",
            reported_transaction_code="S (partial)",
        ),
    ]
    events, _, _ = reconcile(
        rows, {"gift1": proof("2022-03-01T12:00:00Z"), "gift2": proof("2022-03-01T12:00:00Z")}
    )
    assert len(events) == 2 and events[0].event_id != events[1].event_id
    assert all(e.details.transaction == "charitable_transfer" for e in events)
    assert (
        value(data, events, "2022-03-01T12:00:01Z", categories=["congress_charitable_transfer"])
        == 2
    )
    assert value(data, events, "2022-03-01T12:00:01Z", categories=["congress_equity_sale"]) == 0


@pytest.mark.parametrize(
    "change,match",
    [
        ({"amends_observation_id": "missing"}, "predecessor"),
        ({"canonical_transaction_id": "other"}, "retained original"),
        ({"issuer_cik": "0000789019"}, "different reporter/owner/issuer"),
    ],
)
def test_ambiguous_lineage_is_rejected(change, match):
    with pytest.raises(ValueError, match=match):
        reconcile(
            [observation(), amended(**change)],
            {
                "original": proof("2022-03-01T12:00:00Z"),
                "amended": proof("2022-03-07T12:00:00Z", "10000002"),
            },
        )


def test_branching_duplicate_roots_and_unknown_facts_never_silently_merge():
    p = {
        "original": proof("2022-03-01T12:00:00Z"),
        "amended": proof("2022-03-07T12:00:00Z", "10000002"),
        "fork": proof("2022-03-08T12:00:00Z", "10000003"),
    }
    with pytest.raises(ValueError, match="branching"):
        reconcile([observation(), amended(), amended(observation_id="fork")], p)
    cyclic_proofs = {
        **p,
        "cycle-a": proof("2022-03-07T12:00:00Z", "10000002"),
        "cycle-b": proof("2022-03-08T12:00:00Z", "10000003"),
    }
    with pytest.raises(ValueError, match="disconnected or cyclic"):
        reconcile(
            [
                observation(),
                amended(observation_id="cycle-a", amends_observation_id="cycle-b"),
                amended(observation_id="cycle-b", amends_observation_id="cycle-a"),
            ],
            cyclic_proofs,
        )
    with pytest.raises(ValueError, match="exactly one retained original"):
        reconcile([observation(), observation(observation_id="duplicate")], p)
    events, _, blockers = reconcile(
        [observation(action="unknown", amount_min=None, amount_max=None)], {"original": proof(None)}
    )
    assert not events and len(blockers) == 2


def test_legacy_congress_details_serialize_without_new_null_fields():
    legacy = {
        "type": "congress",
        "chamber": "house",
        "filing_id": "fixture",
        "reporter": "Fixture Filer",
        "owner": "spouse",
        "transaction": "purchase",
        "transaction_date": "2022-01-21",
        "filed_at": None,
        "public_at": "2022-03-01T12:00:00Z",
        "amount_min": "1001",
        "amount_max": "15000",
    }
    parsed = CongressDetails.model_validate(legacy)
    assert parsed.model_dump(mode="json") == legacy
    assert "instrument" not in parsed.model_dump(exclude_none=True)
    assert "instrument" not in parsed.model_dump(exclude={"instrument"})


def packet(database, *, missing_replay=False):
    """Retain visibly synthetic bytes in the same immutable artifact architecture."""
    with database() as db:
        archive = io.BytesIO()
        xml = "<FinancialDisclosure>"
        for doc, day in [
            ("10000001", "2/28/2022"),
            ("10000002", "3/4/2022"),
            ("10000003", "3/21/2022"),
        ]:
            xml += f"<Member><First>Fixture</First><Last>Filer</Last><FilingType>P</FilingType><FilingDate>{day}</FilingDate><DocID>{doc}</DocID><Year>2022</Year></Member>"
        xml += "</FinancialDisclosure>"
        with ZipFile(archive, "w") as z:
            z.writestr("2022FD.xml", xml)
        index = evidence.retain(
            db,
            evidence.HOUSE + "/public_disc/financial-pdfs/2022FD.zip",
            "house_fd_index",
            archive.getvalue(),
            {"year": 2022, "http_status": 200, "synthetic": True},
        )
        ids = []
        for doc, clock in [
            ("10000001", "20221023144300"),
            ("10000002", "20220307203650"),
            ("10000003", "20220718121410"),
        ]:
            body = b"%PDF-1.7\nSYNTHETIC fixture " + doc.encode()
            url = evidence.HOUSE + "/public_disc/ptr-pdfs/2022/" + doc + ".pdf"
            labels = {"year": 2022, "document_id": doc, "http_status": 200, "synthetic": True}
            official = evidence.retain(db, url, "house_ptr", body, labels)
            replay = evidence.retain(
                db,
                f"https://web.archive.org/web/{clock}id_/{url}",
                "house_ptr_replay",
                body,
                {
                    **labels,
                    "capture": clock,
                    "memento_datetime": format_datetime(
                        datetime.strptime(clock, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
                    ),
                },
            )
            ids.append((official.id, replay.id))
        db.commit()
    one = observation(official_artifact_id=ids[0][0], replay_artifact_id=ids[0][1]).model_dump(
        mode="json"
    )
    two = amended(
        official_artifact_id=ids[1][0], replay_artifact_id=None if missing_replay else ids[1][1]
    ).model_dump(mode="json")
    return {
        "name": "SYNTHETIC bounded House fixture",
        "first_name": "Fixture",
        "last_name": "Filer",
        "filing_start": "2022-03-01",
        "filing_end": "2022-03-31",
        "coverage_start": "2022-03-01T00:00:00Z",
        "coverage_end": "2022-12-31T23:59:59Z",
        "symbols": ["AAPL", "MSFT"],
        "stream_id": "HOUSE_FIXTURE",
        "index_artifact_id": index.id,
        "synthetic": True,
        "report_reviews": [
            {
                "official_artifact_id": ids[1][0],
                "replay_artifact_id": None if missing_replay else ids[1][1],
                "disposition": "selected_rows",
                "note": "SYNTHETIC direct review of amended Apple exercise.",
            },
            {
                "official_artifact_id": ids[2][0],
                "replay_artifact_id": ids[2][1],
                "disposition": "no_selected_symbols",
                "note": "SYNTHETIC report contains no selected-symbol rows.",
            },
        ],
        "observations": [one, two],
    }


APPROVAL = {
    "acknowledge_conservative_observation_clocks": True,
    "attest_inventory_and_all_selected_rows": True,
    "attest_identity_taxonomy_and_amendments": True,
    "review_note": "SYNTHETIC bounded fixture review; exact report cohort only, not real or all-Congress coverage.",
}


def test_api_immutable_raw_ledger_review_lineage_and_idempotency(client, database):
    body = packet(database)
    download = client.get(BASE + "/artifacts/" + body["observations"][0]["official_artifact_id"])
    assert download.headers["content-type"] == "application/pdf"
    assert download.content.startswith(b"%PDF-")
    r = client.post(BASE + "/ledgers", json=body)
    assert r.status_code == 201, r.text
    saved = r.json()
    assert not saved["data"]["blockers"]
    identifier = saved["id"]
    raw = saved["data"]["raw_source_id"]
    assert len(saved["data"]["source"]["events"]) == 1
    assert client.post(BASE + "/ledgers", json=body).json()["id"] == identifier
    raw_before = client.get("/api/strategy-inputs/" + raw + "/export").json()
    assert not raw_before["data"]["reviewed"] and raw_before["data"]["synthetic"]
    assert (
        client.post(
            BASE + "/ledgers/" + identifier + "/approve",
            json={**APPROVAL, "attest_inventory_and_all_selected_rows": False},
        ).status_code
        == 422
    )
    approved = client.post(BASE + "/ledgers/" + identifier + "/approve", json=APPROVAL)
    assert approved.status_code == 201, approved.text
    source_row = approved.json()["source"]
    assert source_row["reviewed"] and source_row["parent_id"] == raw and source_row["synthetic"]
    assert client.get("/api/strategy-inputs/" + raw + "/export").json() == raw_before
    assert (
        client.post(BASE + "/ledgers/" + identifier + "/approve", json=APPROVAL).json()["source"][
            "id"
        ]
        == source_row["id"]
    )
    renamed = client.post(
        BASE + "/ledgers", json={**body, "name": "SYNTHETIC another display name"}
    )
    assert renamed.status_code == 201, renamed.text
    assert renamed.json()["data"]["raw_source_id"] == raw
    assert (
        client.post(
            BASE + "/ledgers/" + renamed.json()["id"] + "/approve", json=APPROVAL
        ).status_code
        == 201
    )
    assert client.get(BASE + "/ledgers/" + identifier).json()["data"] == saved["data"]


def test_unknown_clocks_and_incomplete_inventory_block_approval(client, database):
    body = packet(database, missing_replay=True)
    r = client.post(BASE + "/ledgers", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["data"]["blockers"]
    assert (
        client.post(BASE + "/ledgers/" + r.json()["id"] + "/approve", json=APPROVAL).status_code
        == 422
    )
    missing = {**packet(database), "report_reviews": packet(database)["report_reviews"][:1]}
    result = client.post(BASE + "/ledgers", json=missing)
    assert result.status_code == 201, result.text
    assert any("inventory" in x for x in result.json()["data"]["blockers"])
    assert (
        client.post(
            BASE + "/ledgers/" + result.json()["id"] + "/approve", json=APPROVAL
        ).status_code
        == 422
    )


@pytest.mark.parametrize("bad", ["hash", "memento", "status"])
def test_replay_failures_never_use_filing_or_last_modified_as_clock(
    client, database, monkeypatch, bad
):
    original_client = httpx.Client
    payload = b"%PDF-1.7\nSYNTHETIC response"
    capture = "20220307203650"
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if request.url.host == "disclosures-clerk.house.gov":
            return httpx.Response(
                200, content=payload, headers={"Last-Modified": "Fri, 04 Mar 2022 18:12:57 GMT"}
            )
        return httpx.Response(
            403 if bad == "status" else 200,
            content=b"wrong" if bad == "hash" else payload,
            headers={
                "Memento-Datetime": "Mon, 07 Mar 2022 20:36:51 GMT"
                if bad == "memento"
                else "Mon, 07 Mar 2022 20:36:50 GMT"
            },
        )

    monkeypatch.setattr(
        evidence.httpx,
        "Client",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    r = client.post(
        BASE + "/house-documents",
        json={"year": 2022, "document_id": "10000002", "archive_capture": capture},
    )
    assert r.status_code == 201, r.text
    assert r.json()["verified_public_observation"] is None and r.json()["findings"]
    assert len(seen) == 2 and len(client.get(BASE + "/artifacts").json()) == 2
    assert (
        client.post(
            BASE + "/house-documents", json={"year": 2022, "document_id": "../secret"}
        ).status_code
        == 422
    )
    assert len(seen) == 2


def test_synthetic_artifacts_cannot_be_relabelled_real_and_row_dates_match_index(client, database):
    body = packet(database)
    rejected = client.post(BASE + "/ledgers", json={**body, "synthetic": False})
    assert rejected.status_code == 422 and "synthetic" in rejected.text
    body["observations"][0]["filing_date"] = "2022-02-27"
    rejected = client.post(BASE + "/ledgers", json=body)
    assert rejected.status_code == 422 and "filing date" in rejected.text


def test_large_cohort_evidence_requires_smaller_partition(client, database, monkeypatch):
    from app.congress import ledger

    body = packet(database)
    monkeypatch.setattr(ledger, "MAX_EVIDENCE_BYTES", 100)
    response = client.post(BASE + "/ledgers", json=body)
    assert response.status_code == 422 and "evidence budget" in response.text


def test_decimal_formatting_alone_is_not_a_new_economic_observation():
    events, audit, blockers = reconcile(
        [
            observation(),
            amended(
                amount_min="1000001.00",
                amount_max="5000000.000",
                shares="10000.0",
                option_contracts="100.00",
                strike_usd="100.000",
            ),
        ],
        {
            "original": proof("2022-03-01T12:00:00Z"),
            "amended": proof("2022-03-07T20:36:50Z", "10000002"),
        },
    )
    assert len(events) == 1 and not blockers
    assert audit[-1]["disposition"] == "metadata_only_amendment"
