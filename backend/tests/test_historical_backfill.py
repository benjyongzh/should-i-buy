"""SYNTHETIC original-source parsing, quarantine and immutable resume receipts."""

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.market_data.platform_providers import NewsFetch
from app.retail.backfill_receipts import checked_partition
from app.retail.earnings_history import earnings_source, quarterly_pair
from app.retail.earnings_tables import numeric_cells, selected_income_statement
from app.retail.news_backfill import normalize_partition


def statement():
    return b"<table><tr><td>Total net sales (1)</td><td>$</td><td>76,000</td><td>70,000</td><td>300,000</td></tr><tr><td>Diluted</td><td>$(0.82)</td><td>0.50</td><td>5.00</td></tr><tr><td>Diluted</td><td>20,000</td><td>21,000</td></tr></table>"


def fixture_pair():
    text = b"Microsoft results for quarter ended December 31, 2017. "
    sec = (
        b"<SEC-HEADER>\nACCESSION NUMBER: 0000000001-18-000001\n<ACCEPTANCE-DATETIME>20180131163023\n</SEC-HEADER><DOCUMENT>\n<TYPE>EX-99.1\n<FILENAME>synthetic.htm\n<TEXT>"
        + text
        + statement()
        + b"</TEXT></DOCUMENT>"
    )
    issuer = b"REDMOND Microsoft results for December 31, 2017: revenue $76.0 billion; GAAP diluted loss per share $(0.82); adjusted EPS $0.96."
    return [
        sec,
        issuer,
        "MSFT",
        "0000000001-18-000001",
        "synthetic.htm",
        "https://fixture.invalid/issuer",
        "https://fixture.invalid/sec",
    ]


def test_current_quarter_gaap_eps_never_becomes_share_count_adjusted_or_annual():
    rows = selected_income_statement(statement())
    assert rows[0]["revenue_columns"] == ["76000", "70000", "300000"]
    assert rows[0]["diluted_eps_columns"] == ["-0.82", "0.50", "5.00"]
    record = quarterly_pair(*fixture_pair())
    assert record["gaap_diluted_eps_usd"] == "-0.82"
    assert record["revenue_usd_millions"] == "76000"
    assert record["fiscal_quarter"] == 2 and record["fiscal_year"] == 2018
    assert record["verified_public_at"] is None
    assert datetime.fromisoformat(record["modeled_available_at"]) > datetime.fromisoformat(
        record["sec_accepted_at"]
    )
    assert record["modeled_available_at"].startswith("2018-02-01T21:00:00")


def test_statement_values_must_be_in_same_table_and_ambiguity_is_rejected():
    separated = b"<table><tr><td>Total revenue</td><td>76,000</td></tr></table><table><tr><td>Diluted</td><td>0.82</td></tr></table>"
    assert not selected_income_statement(separated)
    args = fixture_pair()
    args[0] = args[0].replace(statement(), statement() * 2)
    with pytest.raises(ValueError, match="ambiguous"):
        quarterly_pair(*args)


@pytest.mark.parametrize(
    "mutation", ["accession", "exhibit", "issuer_period", "revenue", "gaap_eps"]
)
def test_quarterly_pair_requires_matching_original_and_issuer(mutation):
    args = fixture_pair()
    if mutation == "accession":
        args[3] = "0000000001-18-000002"
    if mutation == "exhibit":
        args[4] = "other.htm"
    if mutation == "issuer_period":
        args[1] = args[1].replace(b"December 31", b"December 30")
    if mutation == "revenue":
        args[1] = args[1].replace(b"$76.0", b"$77.0")
    if mutation == "gaap_eps":
        args[1] = args[1].replace(b"$(0.82)", b"$0.96")
    with pytest.raises(ValueError):
        quarterly_pair(*args)


def test_source_does_not_assert_missing_earnings_coverage():
    record = quarterly_pair(*fixture_pair())
    with pytest.raises(ValueError, match="four original"):
        earnings_source([record])
    with pytest.raises(ValueError, match="duplicate"):
        earnings_source([record, record])
    assert numeric_cells(["Diluted", "$", "(1,234.50)", "−0.82"]) == [
        Decimal("-1234.50"),
        Decimal("-0.82"),
    ]


def news(identity, title="SYNTHETIC valid news", created="2020-01-02T15:00:00Z"):
    return {
        "id": identity,
        "headline": title,
        "created_at": created,
        "updated_at": "2020-01-03T15:00:00Z",
        "symbols": ["AAPL"],
        "url": "https://fixture.invalid/news",
        "content": "SYNTHETIC",
    }


def test_bad_and_duplicate_news_are_quarantined_without_fabricating_missing_titles():
    body = NewsFetch(symbols=["AAPL"], start="2020-01-01", end="2020-01-31", access="subscription")
    rows = [news(1), news(2, ""), news(3), news(3), news(4, created="2019-12-31T15:00:00Z")]
    candidate, audit = normalize_partition(body, [{"news": rows}], ["a" * 64])
    assert len(candidate.events) == 1 and candidate.events[0].title == "SYNTHETIC valid news"
    assert len(audit["quarantined"]) == 3 and len(audit["excluded_older_versions"]) == 1
    assert not candidate.reviewed and not candidate.complete
    assert not audit["original_vintages_certified"]
    assert candidate.events[0].available_at > candidate.events[0].published_at
    assert candidate.events[0].access == "subscription"


def receipt_fixture(folder: Path):
    attempt = folder / "attempt-synthetic"
    attempt.mkdir()
    raw = b'{"news": []}'
    sha = hashlib.sha256(raw).hexdigest()
    (attempt / "raw.json").write_bytes(raw)
    (attempt / "responses.json").write_text(
        json.dumps([{"path": "raw.json", "bytes": len(raw), "sha256": sha, "http_status": 200}])
    )
    payload = json.dumps({"source_hashes": [sha]})
    (folder / "news-unreviewed.json").write_text(payload)
    audit = {
        "attempt": "/container/path/attempt-synthetic",
        "candidate_file_sha256": hashlib.sha256(payload.encode()).hexdigest(),
    }
    (folder / "audit.json").write_text(json.dumps(audit))
    return attempt


def test_resume_relocates_container_mount_and_checks_exact_retained_raw_bytes(tmp_path):
    attempt = receipt_fixture(tmp_path)
    assert checked_partition(tmp_path)[1].exists()
    (attempt / "raw.json").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="raw response changed"):
        checked_partition(tmp_path)


def test_resume_rejects_tampered_candidate_and_raw_receipt_paths(tmp_path):
    attempt = receipt_fixture(tmp_path)
    (tmp_path / "news-unreviewed.json").write_text("{}")
    with pytest.raises(ValueError, match="candidate changed"):
        checked_partition(tmp_path)
    audit = json.loads((tmp_path / "audit.json").read_text())
    audit["candidate_file_sha256"] = hashlib.sha256(b"{}").hexdigest()
    (tmp_path / "audit.json").write_text(json.dumps(audit))
    rows = json.loads((attempt / "responses.json").read_text())
    rows[0]["path"] = "../outside"
    (attempt / "responses.json").write_text(json.dumps(rows))
    with pytest.raises(ValueError, match="unsafe"):
        checked_partition(tmp_path)


def test_earnings_presence_and_gaap_values_are_unavailable_before_proxy_clock():
    from datetime import timedelta

    from platform_fixtures import event, event_source, platform_data

    from app.market_data.input_book import InputBook
    from app.schemas.domain import EventValue

    record = quarterly_pair(*fixture_pair())
    clock = datetime.fromisoformat(record["modeled_available_at"])
    row = event(
        clock=clock.isoformat(),
        category="earnings.gaap_eps",
        symbols=["MSFT"],
        details={
            "type": "economic",
            "release_at": clock.isoformat(),
            "reference_period": "SYNTHETIC FY2018Q2",
            "units": "USD/share GAAP diluted EPS",
            "actual": record["gaap_diluted_eps_usd"],
        },
    )
    data, _ = platform_data()
    source = event_source([row], stream="ISSUER_EARNINGS")
    book = InputBook(data, [source])
    count = EventValue(
        type="event", stream_id="ISSUER_EARNINGS", categories=["earnings.gaap_eps"], scope="symbol"
    )
    value = count.model_copy(update={"measure": "latest_score", "value_field": "economic_actual"})
    before = clock - timedelta(microseconds=1)
    assert book.event_value(count, "MSFT", before)[0] == 0
    assert book.event_value(value, "MSFT", before)[0] is None
    assert book.event_value(count, "MSFT", clock)[0] == 1
    assert book.event_value(value, "MSFT", clock)[0] == Decimal("-0.82")
    assert book.event_value(count, "AAPL", clock)[0] == 0
    changed = event_source(
        [{**row, "details": {**row["details"], "actual": "9999"}}], stream="ISSUER_EARNINGS"
    )
    assert InputBook(data, [changed]).event_value(value, "MSFT", before)[0] is None
