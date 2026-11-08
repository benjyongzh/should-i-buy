"""SYNTHETIC source candidates: no guessed grades, currencies, clocks or public trades."""

import hashlib
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.market_data.strategy_inputs import HistoricalEvent
from app.retail.analyst_news import extract_action
from app.retail.congress_snapshot import stage_trade, verify_shard
from app.retail.earnings import EarningsSelection, normalize_pair

ISSUERS = {"AAPL": ("Apple",), "MSFT": ("Microsoft",)}


def article(title):
    return HistoricalEvent(
        event_id="synthetic-1",
        published_at="2020-01-02T15:00:00Z",
        available_at="2020-01-03T18:00:00Z",
        category="company_news",
        symbols=["AAPL"],
        title=title,
        source_url="https://fixture.invalid/article",
        original_content_hash="a" * 64,
        derivation="SYNTHETIC test article",
        access="subscription",
        details={
            "type": "news",
            "article_id": "synthetic-1",
            "version_available_at": "2020-01-03T18:00:00Z",
        },
    )


def test_literal_rating_target_keeps_actual_version_clock_and_missing_prior_values():
    parent = article("SYNTHETIC Firm Maintains Buy on Apple, Raises Price Target to $235")
    event, proof = extract_action(parent, ISSUERS)
    assert event.details.firm == "SYNTHETIC Firm"
    assert event.details.target_after == Decimal(235)
    assert event.details.rating_after == "Buy"
    assert event.details.target_before is None and event.details.rating_before is None
    assert event.available_at == datetime(2020, 1, 3, 18, tzinfo=UTC)
    assert event.details.report_available_at == event.available_at
    assert (
        event.access == "subscription"
        and event.original_content_hash == parent.original_content_hash
    )
    assert event.tags == ["analyst.price_target", "analyst.target_raise"]
    assert proof["article_id"] == parent.event_id and proof["status"] == "extracted_unreviewed"


@pytest.mark.parametrize(
    "title",
    [
        "10 Biggest Price Target Changes For Monday",
        "SYNTHETIC Firm Upgrades Spotify, Apple Faces Competition",
        "SYNTHETIC Firm Maintains Buy on Apple and Microsoft, Raises Price Target to $235",
        "SYNTHETIC Firm Maintains Buy on Apple, Raises Price Target to C$235",
        "SYNTHETIC Firm Maintains Mystery on Apple",
        "SYNTHETIC Firm Maintains Buy on Apple, Raises Price Target to $-5",
        "SYNTHETIC Firm Maintains Buy on Microsoftto Hold",
        "SYNTHETIC Firm Maintains Buy on Apple, Raises Price Target to $100 from $200",
    ],
)
def test_ambiguous_or_contradictory_headlines_remain_unresolved(title):
    event, proof = extract_action(article(title), ISSUERS)
    assert event is None and proof["status"] == "unresolved"


def test_explicit_prior_grade_is_preserved_and_unrequested_company_is_not_assigned():
    event, _ = extract_action(article("SYNTHETIC Firm Upgrades Apple from Neutral to Buy"), ISSUERS)
    assert event.details.rating_before == "Neutral" and event.details.rating_after == "Buy"
    bad = article("SYNTHETIC Firm Maintains Buy on Microsoft")
    event, _ = extract_action(bad, ISSUERS)
    assert event is None


def trade_fixture():
    filing = {
        "chamber": "house",
        "docId": "synthetic",
        "rawSha256": "a" * 64,
        "extractionStatus": "ok",
    }
    row = {
        **filing,
        "rowIndex": 0,
        "sourceUrl": "https://fixture.invalid/filing",
        "availableAt": "2022-03-05T04:59:59.999",
        "filingDate": "2022-03-04",
        "availabilitySource": "house_fd_index_filing_date",
        "amountLow": 1001.0,
        "amountHigh": 15000.0,
        "action": "purchase",
        "comment": "SYNTHETIC exercised call options",
    }
    return row, filing


def test_producer_filing_clock_and_purchase_word_never_become_public_equity_signal():
    row, filing = trade_fixture()
    candidate = stage_trade(row, filing)
    assert candidate["verified_public_at"] is None and candidate["strategy_eligible"] is False
    assert candidate["producer_assumed_available_at"] == row["availableAt"]
    assert candidate["reported_action"] == "purchase" and "call options" in candidate["comment"]
    assert len(candidate["blockers"]) == 2


@pytest.mark.parametrize(
    "change",
    [
        {"docId": "other"},
        {"rawSha256": "b" * 64},
        {"amountLow": 20000},
        {"amountHigh": float("inf")},
    ],
)
def test_snapshot_mismatches_or_impossible_amounts_fail(change):
    row, filing = trade_fixture()
    with pytest.raises(ValueError):
        stage_trade({**row, **change}, filing)


def test_shard_hash_size_and_path_are_all_checked():
    raw = b"SYNTHETIC shard"
    expected = {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    verify_shard("data/political_filings/2022.parquet", raw, expected)
    for path, body in [
        ("../secret", raw),
        ("data/political_filings/2022.parquet", raw + b"changed"),
    ]:
        with pytest.raises(ValueError):
            verify_shard(path, body, expected)


def earnings_fixture():
    selection = EarningsSelection(
        symbol="AAPL",
        issuer_name="SYNTHETIC Company",
        accession="0000000001-25-000001",
        fiscal_period="FY2025Q1",
        period_end_literal="December 28, 2024",
        revenue_usd_millions="124300",
        issuer_revenue_billions="124.3",
        diluted_eps_usd="2.40",
        issuer_eps_literal="diluted earnings per share of $2.40",
    )
    issuer = b"SYNTHETIC Company results for December 28, 2024; revenue $124.3 billion; diluted earnings per share of $2.40"
    sec = b"<SEC-HEADER>\nACCESSION NUMBER: 0000000001-25-000001\n<ACCEPTANCE-DATETIME>20250130163023\n</SEC-HEADER><DOCUMENT>\n<TYPE>EX-99.1\n<TEXT>SYNTHETIC Company December 28, 2024 Revenue 124,300 diluted EPS 2.40</TEXT></DOCUMENT>"
    return issuer, sec, selection


def test_earnings_pair_preserves_exact_table_precision_and_unknown_public_clock():
    result = normalize_pair(*earnings_fixture())
    assert result["revenue_usd_millions"] == "124300"
    assert result["diluted_eps_usd"] == "2.40"
    assert result["verified_public_at"] is None and result["strategy_eligible"] is False
    assert result["consensus"] is None and result["surprise"] is None
    assert result["assumed_daily_available_at"].startswith("2025-01-31T21:00:00")


@pytest.mark.parametrize("mutation", ["eps", "revenue", "accession", "separate_exhibits"])
def test_earnings_facts_require_both_originals_and_same_exhibit(mutation):
    issuer, sec, selection = earnings_fixture()
    if mutation == "eps":
        issuer = issuer.replace(b"$2.40", b"$2.50")
    elif mutation == "revenue":
        issuer = issuer.replace(b"$124.3", b"$125.3")
    elif mutation == "accession":
        sec = sec.replace(b"0000000001-25-000001", b"0000000001-25-000002")
    else:
        sec = sec.replace(
            b"diluted EPS 2.40",
            b"</TEXT></DOCUMENT><DOCUMENT>\n<TYPE>EX-99.2\n<TEXT>diluted EPS 2.40",
        )
    with pytest.raises(ValueError):
        normalize_pair(issuer, sec, selection)
