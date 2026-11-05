from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from platform_fixtures import (
    event,
    event_source,
    platform_data,
    platform_profile,
    platform_strategy,
)

from app.llm.client import CompatibleAuthor, StrategyPlan
from app.market_data.input_book import InputBook, SignalView
from app.market_data.strategy_inputs import HistoricalEvent
from app.models.entities import BacktestRun
from app.schemas.domain import EventValue
from app.services.jobs import process_one


def value(book, clock, **kwargs):
    view = SignalView(book, "SPY", clock, clock - timedelta(minutes=5), "intraday", {}, {})
    return view.evaluate(EventValue(type="event", stream_id="NEWS", **kwargs))


def news_record(**changes):
    body = event()
    body.update(changes)
    return body


def test_source_csv_roundtrip_handles_optional_cells_and_preserves_details(client):
    import csv
    import io
    import json

    template = client.get("/api/strategy-input-templates/congress").json()
    rows = template.pop("events")
    template.pop("bars")
    template.pop("states")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                key: (
                    "|".join(value)
                    if isinstance(value, list)
                    else json.dumps(value)
                    if isinstance(value, dict)
                    else ""
                    if value is None
                    else value
                )
                for key, value in row.items()
            }
        )
    response = client.post(
        "/api/strategy-inputs/import-csv",
        json={"metadata": template, "rows_csv": output.getvalue()},
    )
    assert response.status_code == 201, response.text
    saved = client.get("/api/strategy-inputs/" + response.json()["id"] + "/export").json()["data"]
    assert saved["events"][0]["details"]["amount_min"] == "1001"
    assert not saved["reviewed"] and saved["synthetic"]
    assert client.get("/api/strategy-capabilities").json()["configured"] == {
        "alpaca": False,
        "fred": False,
        "llm": False,
        "benzinga": False,
    }


def test_original_news_version_and_later_amendment_never_backdate_text_or_labels():
    data, bars = platform_data()
    first = news_record(
        event_id="original",
        published_at="2020-01-02T15:00:00Z",
        available_at="2020-01-02T15:00:00Z",
        category="positive",
        details={
            "type": "news",
            "article_id": "one",
            "version_available_at": "2020-01-02T15:00:00Z",
            "text": "SYNTHETIC original text",
        },
    )
    amended = news_record(
        event_id="amended",
        published_at="2020-01-02T17:00:00Z",
        available_at="2020-01-02T17:00:00Z",
        category="negative",
        supersedes_event_id="original",
        details={
            "type": "news",
            "article_id": "one",
            "version_available_at": "2020-01-02T17:00:00Z",
            "text": "SYNTHETIC revised text",
        },
    )
    book = InputBook(data, [bars, event_source([first, amended])])
    assert value(book, datetime(2020, 1, 2, 16, tzinfo=UTC), categories=["positive"]) == 1
    assert value(book, datetime(2020, 1, 2, 16, tzinfo=UTC), categories=["negative"]) == 0
    assert value(book, datetime(2020, 1, 2, 18, tzinfo=UTC), categories=["positive"]) == 0
    assert value(book, datetime(2020, 1, 2, 18, tzinfo=UTC), categories=["negative"]) == 1
    invalid = {**first, "available_at": "2020-01-02T14:00:00Z"}
    with pytest.raises(ValueError, match="availability precedes"):
        HistoricalEvent.model_validate(invalid)


def test_public_investor_cannot_see_or_be_affected_by_private_revision():
    data, bars = platform_data()
    first = news_record(
        event_id="public", published_at="2020-01-02T15:00:00Z", available_at="2020-01-02T15:00:00Z"
    )
    private = news_record(
        event_id="subscriber",
        published_at="2020-01-02T16:00:00Z",
        available_at="2020-01-02T16:00:00Z",
        access="subscription",
        supersedes_event_id="public",
        category="premium",
    )
    book = InputBook(data, [bars, event_source([first, private], access_coverage="any_licensed")])
    clock = datetime(2020, 1, 2, 17, tzinfo=UTC)
    assert value(book, clock, categories=["news"]) == 1
    assert value(book, clock, categories=["premium"]) == 0
    assert value(book, clock, categories=["premium"], access="any_licensed") == 1


def test_analyst_target_and_actor_filters_require_actual_report_publication():
    data, bars = platform_data()
    record = news_record(
        category="analyst.upgrade",
        details={
            "type": "analyst",
            "firm": "SYNTHETIC research firm",
            "action": "upgrade",
            "rating_before": "Hold",
            "rating_after": "Buy",
            "target_after": "150",
            "report_available_at": "2020-01-02T15:30:00Z",
        },
    )
    book = InputBook(data, [bars, event_source([record])])
    assert value(book, datetime(2020, 1, 2, 15, tzinfo=UTC)) == 0
    assert (
        value(
            book,
            datetime(2020, 1, 2, 16, tzinfo=UTC),
            measure="latest_score",
            value_field="analyst_target_after",
        )
        == 150
    )
    assert value(book, datetime(2020, 1, 2, 16, tzinfo=UTC), actors=["Another firm"]) == 0
    with pytest.raises(ValueError, match="rating/report publication"):
        HistoricalEvent.model_validate(
            {
                **record,
                "details": {**record["details"], "report_available_at": "2020-01-02T17:00:00Z"},
            }
        )


def test_congress_trade_occurs_only_at_public_disclosure_and_preserves_amount_bounds():
    data, bars = platform_data()
    record = news_record(published_at="2020-01-03T16:00:00Z", available_at="2020-01-03T16:00:00Z")
    record.update(
        category="congress.purchase",
        details={
            "type": "congress",
            "chamber": "house",
            "filing_id": "SYNTHETIC-123",
            "reporter": "SYNTHETIC Representative",
            "owner": "spouse",
            "transaction": "purchase",
            "transaction_date": "2019-12-20",
            "filed_at": "2020-01-02T20:00:00Z",
            "public_at": "2020-01-03T16:00:00Z",
            "amount_min": "1001",
            "amount_max": "15000",
        },
    )
    book = InputBook(data, [bars, event_source([record])])
    assert value(book, datetime(2020, 1, 2, 20, tzinfo=UTC)) == 0
    assert (
        value(book, datetime(2020, 1, 3, 17, tzinfo=UTC), actors=["SYNTHETIC Representative"]) == 1
    )
    assert (
        value(
            book,
            datetime(2020, 1, 3, 17, tzinfo=UTC),
            measure="latest_score",
            value_field="congress_amount_min",
        )
        == 1001
    )
    assert (
        value(
            book,
            datetime(2020, 1, 3, 17, tzinfo=UTC),
            measure="latest_score",
            value_field="congress_amount_max",
        )
        == 15000
    )
    with pytest.raises(ValueError, match="public disclosure"):
        HistoricalEvent.model_validate({**record, "published_at": "2019-12-20T16:00:00Z"})


def test_economic_surprise_cannot_use_post_release_consensus():
    data, bars = platform_data()
    record = news_record(
        details={
            "type": "economic",
            "release_at": "2020-01-02T15:30:00Z",
            "reference_period": "2019-12",
            "units": "SYNTHETIC units",
            "actual": "3.1",
            "consensus": "3.0",
            "consensus_available_at": "2020-01-02T15:00:00Z",
        }
    )
    book = InputBook(data, [bars, event_source([record])])
    assert value(
        book,
        datetime(2020, 1, 2, 16, tzinfo=UTC),
        measure="latest_score",
        value_field="economic_surprise",
    ) == Decimal(".1")
    with pytest.raises(ValueError, match="pre-release consensus"):
        HistoricalEvent.model_validate(
            {
                **record,
                "details": {**record["details"], "consensus_available_at": "2020-01-02T16:00:00Z"},
            }
        )


def setup_run(client, data, source):
    dataset = client.post("/api/market-data/import", json=data.model_dump(mode="json")).json()
    config = platform_strategy(60)
    strategy = client.post(
        "/api/strategies",
        json={"name": "SYNTHETIC platform integration", "config": config.model_dump(mode="json")},
    ).json()
    version = client.post(
        f"/api/strategies/{strategy['id']}/publish", json={"expected_revision": 1}
    ).json()
    p = client.post(
        "/api/backtest-profiles",
        json={
            "name": "SYNTHETIC intraday profile",
            "config": platform_profile(data).model_dump(mode="json"),
        },
    ).json()
    raw_source = source.model_copy(
        update={"reviewed": False, "parent_id": None, "parent_hash": None, "review_note": ""}
    )
    raw = client.post("/api/strategy-inputs/import", json=raw_source.model_dump(mode="json"))
    assert raw.status_code == 201, raw.text
    raw = raw.json()
    approved = client.post(
        f"/api/strategy-inputs/{raw['id']}/approve",
        json={
            "acknowledge_publication_policy": True,
            "attest_complete_coverage": True,
            "review_note": "SYNTHETIC source reviewed for this financial test only.",
        },
    )
    assert approved.status_code == 201, approved.text
    approved = approved.json()
    body = {
        "strategy_version_ids": [version["id"]],
        "profile_id": p["id"],
        "dataset_id": dataset["id"],
        "strategy_input_ids": [approved["id"]],
        "acknowledge_synthetic": True,
    }
    return strategy, raw, approved, body


def test_source_review_and_frozen_worker_manifest_exact_repeat(client, database):
    data, source = platform_data()
    _, raw, approved, body = setup_run(client, data, source)
    assert raw["id"] != approved["id"] and raw["reviewed"] is False
    assert (
        client.get(f"/api/strategy-inputs/{raw['id']}/export").json()["data"]["reviewed"] is False
    )
    blocked = client.post("/api/backtests", json={**body, "strategy_input_ids": [raw["id"]]})
    assert blocked.status_code == 422 and "review" in blocked.text
    first = client.post("/api/backtests", json=body)
    assert first.status_code == 202, first.text
    first = first.json()[0]
    assert first["provenance"]["strategy_inputs"][0]["content_hash"] == approved["content_hash"]
    process_one(database)
    status = client.get(f"/api/backtests/{first['id']}").json()
    assert status["status"] == "completed", status
    result = client.get(f"/api/backtests/{first['id']}/results").json()
    again = client.post("/api/backtests", json=body).json()[0]
    process_one(database)
    assert client.get(f"/api/backtests/{again['id']}/results").json() == result
    ready = client.post(
        "/api/strategy-definitions/requirements",
        json={
            "config": platform_strategy(60).model_dump(mode="json"),
            "profile_id": body["profile_id"],
            "dataset_id": body["dataset_id"],
            "strategy_input_ids": [approved["id"]],
        },
    ).json()
    assert ready["ready_to_run"] is True and ready["requirements"]["intraday"] is True


def test_manifest_tampering_fails_before_simulation(client, database):
    data, source = platform_data()
    _, _, _, body = setup_run(client, data, source)
    run = client.post("/api/backtests", json=body).json()[0]
    with database() as db:
        row = db.get(BacktestRun, run["id"])
        row.provenance = {**row.provenance, "strategy_input_hash": "f" * 64}
        db.commit()
    process_one(database)
    result = client.get(f"/api/backtests/{run['id']}").json()
    assert result["status"] == "failed" and "manifest" in result["error"]


def test_templates_and_raw_import_cannot_claim_reviewed_status(client):
    for kind in ["intraday", "universe", "news", "analyst", "congress", "economic"]:
        response = client.get("/api/strategy-input-templates/" + kind)
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["synthetic"] and not payload["reviewed"]
        assert client.post("/api/strategy-inputs/import", json=payload).status_code == 201
        payload.update(
            reviewed=True,
            complete=True,
            parent_id="fake",
            parent_hash="a" * 64,
            review_note="Fake direct review is not an authorized source approval",
        )
        assert client.post("/api/strategy-inputs/import", json=payload).status_code == 422


def test_capability_aware_proposal_isolated_blocked_until_supported_and_separately_published(
    client, monkeypatch
):
    config = platform_strategy(60)
    draft = client.post(
        "/api/strategies",
        json={"name": "SYNTHETIC proposal draft", "config": config.model_dump(mode="json")},
    ).json()
    blocked = StrategyPlan(
        config=None,
        interpretation="Unsupported request is explicitly reported",
        unsupported_requests=["Live brokerage execution is outside this historical application"],
    )
    monkeypatch.setattr(CompatibleAuthor, "plan", lambda *args: blocked)
    response = client.post(
        "/api/llm/plan-strategy", json={"strategy_id": draft["id"], "prompt": "Execute live trades"}
    )
    assert response.status_code == 200, response.text
    proposal = response.json()
    assert proposal["metadata_json"]["blocked"] is True
    assert client.post(f"/api/llm/proposals/{proposal['id']}/accept").status_code == 422
    assert client.get(f"/api/strategies/{draft['id']}").json()["draft_revision"] == 1
    supported = StrategyPlan(
        config=config,
        interpretation="Evaluate completed bars from one hour after exchange open; execute at next strictly later interval open.",
        data_requirements=["Historical intraday bars and FX/action coverage"],
    )
    monkeypatch.setattr(CompatibleAuthor, "plan", lambda *args: supported)
    proposal = client.post(
        "/api/llm/plan-strategy",
        json={"strategy_id": draft["id"], "prompt": "Buy one hour after open onwards"},
    ).json()
    assert not proposal["metadata_json"]["blocked"]
    assert client.get(f"/api/strategies/{draft['id']}/versions").json() == []
    accepted = client.post(f"/api/llm/proposals/{proposal['id']}/accept").json()
    assert accepted["draft_revision"] == 2
    assert client.get(f"/api/strategies/{draft['id']}/versions").json() == []
    version = client.post(f"/api/strategies/{draft['id']}/publish", json={"expected_revision": 2})
    assert version.status_code == 201, version.text
