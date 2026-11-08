"""Explicitly synthetic adversarial fixtures for retail-source qualification."""

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.market_data.platform_providers import NewsFetch, normalize_news
from app.retail.qualification import audit_news, insider_event, inventory_rows


def news_fixture():
    request = NewsFetch(symbols=["AAPL"], start="2020-01-02", end="2020-01-02")
    row = {
        "id": 1,
        "created_at": "2020-01-02T15:00:00Z",
        "updated_at": "2020-01-03T17:00:00Z",
        "headline": "SYNTHETIC revised news",
        "symbols": ["AAPL"],
        "url": "https://fixture.invalid/article",
    }
    return request, row


def normalize(request, row):
    pages = [json.dumps({"news": [row], "next_page_token": None}).encode()]
    candidate = normalize_news(
        request, [json.loads(pages[0], parse_float=Decimal)], [hashlib.sha256(pages[0]).hexdigest()]
    )
    return pages, candidate


@pytest.mark.parametrize(
    "change",
    [
        {"updated_at": None},
        {"updated_at": "2020-01-03T17:00:00"},
        {"created_at": "2020-01-03T00:00:00Z"},
        {"updated_at": "2020-01-02T14:59:59Z"},
        {"symbols": ["MSFT"]},
    ],
)
def test_news_requires_explicit_version_clock_and_requested_scope(change):
    request, row = news_fixture()
    with pytest.raises(ValueError):
        normalize(request, {**row, **change})


def test_updated_article_remains_unavailable_in_earlier_period_and_body_stays_missing():
    request, row = news_fixture()
    pages, source = normalize(request, row)
    event = source.events[0]
    assert event.published_at == datetime(2020, 1, 2, 15, tzinfo=UTC)
    assert event.available_at == datetime(2020, 1, 3, 17, tzinfo=UTC)
    assert event.details.text == "" and event.score is None
    audit = audit_news(request, pages, source)
    assert audit["available_after_requested_period"] == 1 and audit["headline_only"] == 1
    assert not source.reviewed and not source.complete and not audit["automatically_approved"]
    assert not audit["original_vintages_certified"]


def test_news_audit_rejects_truncated_pagination_and_changed_candidate():
    request, row = news_fixture()
    pages, source = normalize(request, row)
    with pytest.raises(ValueError, match="differs"):
        audit_news(request, pages, source.model_copy(update={"events": []}))
    partial = json.dumps({"news": [row], "next_page_token": "synthetic-more"}).encode()
    candidate = normalize_news(
        request, [json.loads(partial)], [hashlib.sha256(partial).hexdigest()]
    )
    with pytest.raises(ValueError, match="incomplete"):
        audit_news(request, [partial], candidate)


def ownership_fixture(form="4", code="P", transaction_date="2020-01-02", price=""):
    row = {
        "form": form,
        "accessionNumber": "0000000001-20-000001",
        "primaryDocument": "ownership.xml",
        "acceptanceDateTime": "2020-01-03T21:05:00Z",
    }
    xml = f"""<ownershipDocument><documentType>{form}</documentType><issuer><issuerCik>1</issuerCik><issuerTradingSymbol>AAPL</issuerTradingSymbol></issuer><reportingOwner><reportingOwnerId><rptOwnerName>SYNTHETIC owner</rptOwnerName></reportingOwnerId></reportingOwner><nonDerivativeTable><nonDerivativeTransaction><transactionDate><value>{transaction_date}</value></transactionDate><transactionCoding><transactionCode>{code}</transactionCode></transactionCoding><transactionAmounts><transactionShares><value>10.0000</value></transactionShares><transactionPricePerShare><value>{price}</value></transactionPricePerShare><transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts></nonDerivativeTransaction></nonDerivativeTable><derivativeTable><derivativeTransaction/></derivativeTable></ownershipDocument>"""
    raw = f"""<SEC-HEADER>\n<ACCEPTANCE-DATETIME>20200103160500\nACCESSION NUMBER: 0000000001-20-000001\n</SEC-HEADER><DOCUMENT>\n<TYPE>{form}\n<FILENAME>ownership.xml\n<XML>{xml}</XML></DOCUMENT>""".encode()
    return raw, row


def insider(raw, row):
    return insider_event(raw, row, "AAPL", "1", "https://fixture.invalid/filing")


def test_insider_disclosure_uses_filing_delivery_not_trade_date_and_preserves_missing_price():
    raw, row = ownership_fixture()
    event, summary = insider(raw, row)
    # Friday filing: declared conservative delivery is the following Monday close.
    assert event.available_at == datetime(2020, 1, 6, 21, tzinfo=UTC)
    assert event.published_at == datetime(2020, 1, 3, 21, 5, tzinfo=UTC)
    assert summary["transactions"][0]["price_per_share"] is None
    assert summary["transactions"][0]["shares"] == "10.0000"
    assert summary["derivative_rows_not_normalized"] == 1
    assert event.tags == ["insider.form4", "insider.reported_purchase"]
    assert event.original_content_hash == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("form,code", [("4/A", "P"), ("4", "A"), ("4", "M")])
def test_amendments_awards_and_exercises_do_not_become_new_purchase_signals(form, code):
    event, summary = insider(*ownership_fixture(form=form, code=code))
    assert "insider.reported_purchase" not in event.tags
    if form == "4/A":
        assert summary["amendment_lineage_reviewed"] is False


@pytest.mark.parametrize("mutation", ["clock", "issuer", "future", "nonfinite", "identity"])
def test_insider_rejects_conflicting_or_invalid_original_evidence(mutation):
    raw, row = ownership_fixture()
    if mutation == "clock":
        row["acceptanceDateTime"] = "2020-01-03T16:05:00Z"
    elif mutation == "issuer":
        raw = raw.replace(b"<issuerCik>1", b"<issuerCik>2")
    elif mutation == "future":
        raw = raw.replace(b"2020-01-02", b"2020-01-06")
    elif mutation == "nonfinite":
        raw = raw.replace(b">10.0000<", b">NaN<")
    else:
        raw = raw.replace(b"ACCESSION NUMBER: 0000000001-20-000001", b"ACCESSION NUMBER: wrong")
    with pytest.raises(ValueError):
        insider(raw, row)


def test_sec_inventory_does_not_silently_truncate_parallel_columns():
    table = {
        key: [value]
        for key, value in {**ownership_fixture()[1], "filingDate": "2020-01-03"}.items()
    }
    assert inventory_rows(table)[0]["form"] == "4"
    table["filingDate"] = []
    with pytest.raises(ValueError, match="different lengths"):
        inventory_rows(table)


def test_old_article_updated_in_query_is_retained_in_audit_without_new_publication_signal():
    request, row = news_fixture()
    row.update(created_at="2019-01-01T15:00:00Z", updated_at="2020-01-02T17:00:00Z")
    pages, source = normalize(request, row)
    audit = audit_news(request, pages, source)
    assert source.events == []
    assert audit["rows_checked"] == 1
    assert audit["older_publications_updated_in_window_excluded"] == 1


def test_sec_capture_does_not_decode_gzip_twice(tmp_path, monkeypatch):
    import gzip

    import httpx
    from pydantic import SecretStr

    from app.core.config import Settings
    from scripts import retail_information_pilot as pilot

    transport = httpx.MockTransport(
        lambda r: httpx.Response(
            200,
            content=gzip.compress(b"SYNTHETIC original SEC body"),
            headers={"Content-Encoding": "gzip", "Content-Type": "text/plain"},
        )
    )
    client_type = httpx.Client
    monkeypatch.setattr(pilot.httpx, "Client", lambda **kw: client_type(transport=transport, **kw))
    monkeypatch.setattr(
        pilot,
        "settings",
        lambda: Settings(
            data_source_contact_email="fixture@example.invalid",
            alpaca_api_key=SecretStr("synthetic"),
        ),
    )
    evidence = pilot.Evidence(tmp_path)
    raw = evidence.sec("https://data.sec.gov/submissions/CIK0000000001.json")
    assert raw == b"SYNTHETIC original SEC body"
    assert (tmp_path / evidence.entries[0]["path"]).read_bytes() == raw
    assert evidence.entries[0]["sha256"] == hashlib.sha256(raw).hexdigest()


def test_sec_rendering_prefix_maps_only_to_the_matching_original_xml_filename():
    raw, row = ownership_fixture()
    row["primaryDocument"] = "xslF345X03/ownership.xml"
    event, _ = insider(raw, row)
    assert event.tags == ["insider.form4", "insider.reported_purchase"]
    row["primaryDocument"] = "../ownership.xml"
    with pytest.raises(ValueError, match="rendering path"):
        insider(raw, row)


def test_reused_evidence_retains_original_capture_clock_and_rejects_modified_bytes(tmp_path):
    import httpx

    from scripts.retail_information_pilot import Evidence

    previous = Evidence(tmp_path / "previous")
    previous.capture(
        httpx.Response(
            200,
            content=b"SYNTHETIC retained SEC body",
            request=httpx.Request("GET", "https://data.sec.gov/submissions/CIK0000000001.json"),
        )
    )
    entry = previous.entries[0]
    replay = Evidence(tmp_path / "replay", tmp_path / "previous")
    assert replay.sec(entry["source_url"]) == b"SYNTHETIC retained SEC body"
    assert replay.entries[0]["retrieved_at"] == entry["retrieved_at"]
    assert replay.entries[0]["reused_from"].endswith(entry["path"])
    (previous.root / entry["path"]).write_bytes(b"SYNTHETIC altered bytes")
    with pytest.raises(ValueError, match="hash/status mismatch"):
        Evidence(tmp_path / "bad-replay", previous.root).sec(entry["source_url"])
