"""Source preparation/review and explicit strategy capability/readiness reports."""

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import Field
from sqlalchemy.orm import Session

from app.api.routes import dump, get
from app.backtesting.advanced_validation import requirements, validate_advanced
from app.core.config import settings
from app.db.session import get_db
from app.market_data.analyst_provider import AnalystFetch, fetch_ratings
from app.market_data.platform_providers import IntradayFetch, NewsFetch, fetch_intraday, fetch_news
from app.market_data.providers import csv_records
from app.market_data.strategy_inputs import StrategyInput
from app.models.entities import Dataset, Profile, StrategyInputRevision
from app.schemas.domain import ProfileConfig, StrategyConfig, StrictModel
from app.services.datasets import load_dataset
from app.services.feature_inputs import resolve_features
from app.services.strategy_inputs import checked_input, input_catalog, resolve_inputs, retain_input

router = APIRouter(prefix="/api")


@router.get("/strategy-capabilities")
def capabilities():
    config = settings()
    return {
        "engine_version": "2.0.0",
        "historical_only": True,
        "intraday_minutes": [1, 5, 15, 30, 60],
        "features": [
            "exchange-relative windows",
            "calendar conditions",
            "daily/intraday completed operands",
            "historical sector/membership selection",
            "ranked preferences",
            "conditional sizing",
            "company news versions",
            "analyst rating changes",
            "economic release surprises",
            "Congress public disclosures",
        ],
        "configured": {
            "alpaca": bool(
                config.alpaca_api_key.get_secret_value()
                and config.alpaca_secret_key.get_secret_value()
            ),
            "fred": bool(config.fred_api_key.get_secret_value()),
            "benzinga": bool(config.benzinga_api_key.get_secret_value()),
            "llm": bool(config.llm_api_key.get_secret_value() and config.llm_model),
        },
        "limits": {
            "symbols_per_profile": 50,
            "rows_per_source_partition": 100000,
            "total_source_rows_per_run": 1000000,
            "execution_intervals_per_run": 200000,
            "signal_records_per_run": 500000,
        },
        "data_notes": [
            "Provider configuration is not proof of historical entitlements or publication-vintage coverage.",
            "Daily bars cannot supply intraday fills; missing required intervals fail.",
            "News feeds are source-specific, not all news a human could read.",
            "Ratings require original nominal targets and report availability, not current consensus or future-adjusted targets.",
            "Congress amount ranges are retained; public disclosure time, not transaction/filing date, controls visibility.",
            "Original source files can be imported without any additional API key.",
        ],
    }


def summary(row):
    data = checked_input(row)
    return {
        **dump(row, {"payload"}),
        **{
            k: v
            for k, v in data.model_dump(mode="json").items()
            if k not in {"bars", "states", "events"}
        },
        "row_count": len(data.bars) + len(data.states) + len(data.events),
    }


@router.get("/strategy-inputs")
def list_inputs(db: Session = Depends(get_db)):
    return input_catalog(db)


@router.get("/strategy-inputs/schema")
def input_schema():
    return StrategyInput.model_json_schema()


@router.post("/strategy-inputs/import", status_code=201)
def import_input(body: StrategyInput, db: Session = Depends(get_db)):
    if body.reviewed or body.parent_id or body.parent_hash:
        raise ValueError(
            "import raw inputs, then use explicit source review to create an eligible revision"
        )
    return summary(retain_input(db, body))


class SourceCSV(StrictModel):
    metadata: dict
    rows_csv: str = Field(min_length=1, max_length=20_000_000)


@router.post("/strategy-inputs/import-csv", status_code=201)
def import_csv(body: SourceCSV, db: Session = Depends(get_db)):
    import json

    kind = body.metadata.get("kind")
    field = {"intraday": "bars", "universe": "states", "events": "events"}.get(kind)
    if field is None:
        raise ValueError("CSV metadata requires kind intraday, universe or events")
    if any(k in body.metadata for k in ("bars", "states", "events")):
        raise ValueError("CSV metadata must not contain a second row payload")
    rows = [
        {key: value for key, value in row.items() if value != ""}
        for row in csv_records(body.rows_csv)
    ]
    for row in rows:
        for key in ("symbols", "sectors", "tags"):
            if key in row:
                row[key] = [item.strip() for item in row[key].split("|") if item.strip()]
        if "details" in row:
            row["details"] = json.loads(row["details"])
    return import_input(StrategyInput.model_validate({**body.metadata, field: rows}), db)


@router.post("/strategy-inputs/alpaca-intraday", status_code=201)
def prepare_intraday(body: IntradayFetch, db: Session = Depends(get_db)):
    return summary(retain_input(db, fetch_intraday(body)))


@router.post("/strategy-inputs/alpaca-news", status_code=201)
def prepare_news(body: NewsFetch, db: Session = Depends(get_db)):
    return summary(retain_input(db, fetch_news(body)))


@router.post("/strategy-inputs/benzinga-ratings", status_code=201)
def prepare_ratings(body: AnalystFetch, db: Session = Depends(get_db)):
    return summary(retain_input(db, fetch_ratings(body)))


class Review(StrictModel):
    acknowledge_publication_policy: Literal[True]
    attest_complete_coverage: Literal[True]
    review_note: str = Field(min_length=20, max_length=2000)


@router.post("/strategy-inputs/{identifier}/approve", status_code=201)
def approve(identifier: str, body: Review, db: Session = Depends(get_db)):
    parent = get(db, StrategyInputRevision, identifier)
    data = checked_input(parent)
    if data.reviewed:
        raise ValueError("this source revision is already eligible; retain it unchanged")
    payload = data.model_dump(mode="json")
    payload.update(
        reviewed=True,
        complete=True,
        parent_id=parent.id,
        parent_hash=parent.content_hash,
        review_note=body.review_note,
    )
    return summary(retain_input(db, StrategyInput.model_validate(payload)))


@router.get("/strategy-inputs/{identifier}/export")
def export(identifier: str, db: Session = Depends(get_db)):
    row = get(db, StrategyInputRevision, identifier)
    checked_input(row)
    return {**dump(row, {"payload"}), "data": row.payload}


class ReadinessRequest(StrictModel):
    config: StrategyConfig
    profile_id: str | None = None
    dataset_id: str | None = None
    strategy_input_ids: list[str] = Field(default_factory=list, max_length=100)
    context_snapshot_ids: list[str] = Field(default_factory=list, max_length=20)


def describe_capabilities(config, profile=None):
    context = profile or ProfileConfig()
    needed = requirements(config, context)
    policy = config.execution_policy
    return {
        "schema_supported": True,
        "requirements": needed,
        "interpretation": {
            "execution": policy.model_dump(mode="json")
            if policy
            else "Profile default: daily close or completed intraday intervals; next strictly later eligible open",
            "universe": config.universe.model_dump(mode="json")
            if config.universe
            else "Profile's permitted symbols",
            "sizing": config.sizing.model_dump(mode="json"),
            "conditional_sizing": [r.model_dump(mode="json") for r in config.sizing_rules or []],
            "publication": "Proposal acceptance edits a draft; separate explicit publication creates the next immutable version",
            "information_clock": "Only completed observations and public/selected licensed records available at the simulation clock; later corrections and disclosure dates never backdate information",
        },
    }


@router.post("/strategy-definitions/requirements")
def readiness(body: ReadinessRequest, db: Session = Depends(get_db)):
    profile = (
        ProfileConfig.model_validate(get(db, Profile, body.profile_id).config)
        if body.profile_id
        else None
    )
    report = describe_capabilities(body.config, profile)
    report.update(ready_to_run=False, blockers=[])
    if profile is None or not body.dataset_id:
        report["blockers"].append(
            "Select a profile and immutable daily price/FX/action dataset to verify run-specific readiness"
        )
        return report
    try:
        _, sources = resolve_inputs(db, body.strategy_input_ids)
        _, features = resolve_features(db, body.context_snapshot_ids)
        data = load_dataset(db, get(db, Dataset, body.dataset_id))
        from app.market_data.strategy_inputs import advanced

        if advanced(body.config, profile):
            validate_advanced(body.config, profile, data, sources, features)
        else:
            from app.market_data.features import FeatureBook, validate_features
            from app.market_data.validation import validate_coverage

            validate_coverage(data, profile)
            validate_features(body.config, FeatureBook(features), data, profile)
        report["ready_to_run"] = True
    except ValueError as exc:
        report["blockers"].append(str(exc))
    return report


@router.get("/strategy-input-templates/{kind}")
def template(kind: Literal["intraday", "universe", "news", "analyst", "congress", "economic"]):
    base = {
        "kind": "events",
        "name": "SYNTHETIC schema example — replace with sourced records",
        "source": "SYNTHETIC fixture",
        "source_url": "https://example.invalid/source",
        "availability_policy": "SYNTHETIC example only; supply original source publication/version clocks",
        "synthetic": True,
        "coverage_start": "2020-01-01T00:00:00Z",
        "coverage_end": "2020-02-01T23:59:59Z",
        "symbols": ["SPY"],
        "stream_id": {
            "news": "COMPANY_NEWS",
            "analyst": "ANALYST_RATINGS",
            "congress": "CONGRESS_TRADES",
            "economic": "ECONOMIC_RELEASES",
        }.get(kind),
        "events": [],
    }
    event = {
        "event_id": "replace-with-stable-source-identity",
        "published_at": "2020-01-02T15:00:00Z",
        "available_at": "2020-01-02T15:00:00Z",
        "category": kind,
        "symbols": ["SPY"],
        "title": "SYNTHETIC example",
        "source_url": "https://example.invalid/document",
        "original_content_hash": "a" * 64,
        "derivation": "SYNTHETIC source data; no hindsight model classification",
    }
    details = {
        "news": {
            "type": "news",
            "article_id": "example",
            "version_available_at": event["available_at"],
            "text": "SYNTHETIC archived article text",
        },
        "analyst": {
            "type": "analyst",
            "firm": "SYNTHETIC firm",
            "action": "upgrade",
            "rating_before": "Hold",
            "rating_after": "Buy",
            "target_after": "120",
            "report_available_at": event["available_at"],
        },
        "congress": {
            "type": "congress",
            "chamber": "house",
            "filing_id": "SYNTHETIC-filing",
            "reporter": "SYNTHETIC filer",
            "owner": "unknown",
            "transaction": "purchase",
            "transaction_date": "2019-12-20",
            "public_at": event["published_at"],
            "amount_min": "1001",
            "amount_max": "15000",
        },
        "economic": {
            "type": "economic",
            "reference_period": "2019-12",
            "units": "example units",
            "actual": "2.0",
            "consensus": "1.9",
            "consensus_available_at": "2020-01-01T00:00:00Z",
            "release_at": event["published_at"],
        },
    }
    if kind in details:
        base["events"] = [{**event, "details": details[kind]}]
    elif kind == "universe":
        base.update(
            kind="universe",
            states=[
                dict(
                    symbol="SPY",
                    instrument_id="SYNTHETIC-SPY",
                    effective_at="2019-01-01T00:00:00Z",
                    available_at="2019-01-01T00:00:00Z",
                    listed=True,
                    sector="SYNTHETIC sector",
                    source_url=base["source_url"],
                )
            ],
        )
    else:
        base.update(
            kind="intraday",
            bar_minutes=5,
            bars=[
                dict(
                    symbol="SPY",
                    session_date="2020-01-02",
                    start_at="2020-01-02T14:30:00Z",
                    end_at="2020-01-02T14:35:00Z",
                    source_timestamp="2020-01-02T14:35:00Z",
                    available_at="2020-01-02T14:35:01Z",
                    open="100",
                    high="100",
                    low="100",
                    close="100",
                    volume="1000",
                )
            ],
        )
    if base["stream_id"] is None:
        base.pop("stream_id")
    return StrategyInput.model_validate(base).model_dump(mode="json")
