from copy import deepcopy
from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DatabaseError

from app.core.config import Settings
from app.market_data import context
from app.market_data.context import ContextFetch, fetch_context
from app.models.entities import ContextSnapshot


def mock_source(monkeypatch, handler):
    original = httpx.Client
    monkeypatch.setattr(
        context.httpx,
        "Client",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )


def test_fred_context_preserves_initial_release_dates_missing_values_negative_oil_and_pagination(
    monkeypatch,
):
    monkeypatch.setattr(context, "settings", lambda: Settings(fred_api_key="fixture-key"))
    calls = []

    def provider(request):
        calls.append(dict(request.url.params))
        offset = int(request.url.params["offset"])
        assert request.url.params["output_type"] == "4"
        assert request.url.params["series_id"] == "DCOILWTICO"
        if request.url.params["realtime_start"] > "2020-04-01":
            return httpx.Response(
                200, json={"output_type": 4, "offset": 0, "count": 0, "observations": []}
            )
        rows = (
            [
                {"date": "2020-04-20", "value": "-36.98", "realtime_start": "2020-04-21"},
                {"date": "2020-04-21", "value": ".", "realtime_start": "2020-04-22"},
            ]
            if offset == 0
            else [{"date": "2020-04-22", "value": "13.64", "realtime_start": "2020-04-23"}]
        )
        return httpx.Response(
            200, json={"output_type": 4, "offset": offset, "count": 3, "observations": rows}
        )

    mock_source(monkeypatch, provider)
    result = fetch_context(
        ContextFetch(series_id="DCOILWTICO", start="2020-04-01", end="2020-04-30")
    )
    assert len(calls) == 3
    assert result.missing_omitted == 1
    assert result.observations[0].value == Decimal("-36.98")
    assert result.observations[0].available_at.isoformat() == "2020-04-22T00:00:00-04:00"
    assert result.research_only is True
    assert "fixture-key" not in result.model_dump_json()


def test_vix_history_never_invents_original_publication_timestamps(monkeypatch):
    mock_source(
        monkeypatch,
        lambda _: httpx.Response(
            200,
            text="DATE,OPEN,HIGH,LOW,CLOSE\n01/02/2018,10,11,9,10.25\n01/03/2018,10,11,9,9.15\n01/02/2019,10,11,9,20\n",
        ),
    )
    data = fetch_context(ContextFetch(series_id="VIX", start="2018-01-01", end="2018-12-31"))
    assert len(data.observations) == 2
    assert all(p.available_at is None for p in data.observations)
    assert "unverified" in data.availability_policy


def test_fred_realtime_end_uses_us_source_day_when_utc_is_already_tomorrow(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 5, 0, 30, tzinfo=UTC).astimezone(tz)

    monkeypatch.setattr(context, "datetime", Clock)
    monkeypatch.setattr(context, "settings", lambda: Settings(fred_api_key="fixture-key"))

    def provider(request):
        assert request.url.params["realtime_end"] == "2026-11-04"
        return httpx.Response(
            200,
            json={
                "output_type": 4,
                "offset": 0,
                "count": 1,
                "observations": [
                    {"date": "2026-01-01", "realtime_start": "2026-02-02", "value": "4.1"}
                ],
            },
        )

    mock_source(monkeypatch, provider)
    data = fetch_context(ContextFetch(series_id="UNRATE", start="2026-01-01", end="2026-01-31"))
    assert data.source_as_of == date(2026, 11, 4)


def test_fred_vintage_windows_retain_late_first_releases_without_backdating(monkeypatch):
    monkeypatch.setattr(context, "settings", lambda: Settings(fred_api_key="fixture-key"))
    calls = []

    def provider(request):
        params = dict(request.url.params)
        calls.append(params)
        begin = params["realtime_start"]
        rows = (
            [{"date": "2018-01-02", "value": "1.92", "realtime_start": "2022-01-03"}]
            if begin == "2022-01-01"
            else []
        )
        return httpx.Response(
            200, json={"output_type": 4, "offset": 0, "count": len(rows), "observations": rows}
        )

    mock_source(monkeypatch, provider)
    data = fetch_context(ContextFetch(series_id="DGS2", start="2018-01-01", end="2018-12-31"))
    assert data.observations[0].observation_date == date(2018, 1, 2)
    assert data.observations[0].available_at.year == 2022
    assert all(
        (date.fromisoformat(p["realtime_end"]) - date.fromisoformat(p["realtime_start"])).days
        < 1500
        for p in calls
    )
    assert all(p["observation_start"] == "2018-01-01" for p in calls)


def test_context_api_immutable_export_and_no_strategy_exposure(client, database, monkeypatch):
    mock_source(monkeypatch, lambda _: httpx.Response(200, text="DATE,CLOSE\n01/02/2018,10.25\n"))
    response = client.post(
        "/api/research/context/fetch",
        json={"series_id": "VIX", "start": "2018-01-01", "end": "2018-12-31"},
    )
    assert response.status_code == 201, response.text
    snapshot = response.json()
    assert snapshot["observation_count"] == 1
    assert "observations" not in snapshot
    exported = client.get(f"/api/research/context/{snapshot['id']}/export").json()
    assert exported["data"]["observations"][0]["value"] == "10.25"
    assert (
        client.post(
            "/api/research/context/fetch",
            json={"series_id": "VIX", "start": "2018-01-01", "end": "2018-12-31"},
        ).json()["id"]
        == snapshot["id"]
    )
    assert len(client.get("/api/research/context").json()) == 1
    assert client.get("/api/market-data/datasets").json() == []
    assert (
        client.patch(f"/api/research/context/{snapshot['id']}/export", json={}).status_code == 405
    )
    with database() as db:
        row = db.scalar(select(ContextSnapshot))
        # An older immutable snapshot can omit a later optional metadata field.
        legacy = {k: v for k, v in row.payload.items() if k != "source_as_of"}
        from app.schemas.domain import canonical_hash

        row.payload = legacy
        row.content_hash = canonical_hash({k: v for k, v in legacy.items() if k != "retrieved_at"})
        db.commit()
    assert client.get(f"/api/research/context/{snapshot['id']}/export").status_code == 200
    with database() as db:
        row = db.scalar(select(ContextSnapshot))
        row.payload = {**row.payload, "name": "tampered"}
        db.commit()
    assert client.get(f"/api/research/context/{snapshot['id']}/export").status_code == 422
    schema = client.get("/api/strategy-schema").json()
    assert "context" not in str(schema).lower()


def test_context_credentials_errors_and_bounded_inputs(client, monkeypatch):
    assert (
        client.post(
            "/api/research/context/fetch", json={"series_id": "https://internal/secret"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/research/context/fetch",
            json={"series_id": "VIX", "start": "2025-01-02", "end": "2024-01-01"},
        ).status_code
        == 422
    )
    assert (
        client.post("/api/research/context/fetch", json={"series_id": "DGS10"}).status_code == 422
    )
    mock_source(monkeypatch, lambda _: httpx.Response(403, text="sensitive-provider-body"))
    response = client.post("/api/research/context/fetch", json={"series_id": "VIX"})
    assert response.status_code == 422
    assert "sensitive-provider-body" not in response.text


def test_context_snapshot_database_triggers(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config

    from app.core.config import settings
    from app.db.session import make_engine

    url = f"sqlite:///{tmp_path / 'context.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    settings.cache_clear()
    command.upgrade(Config("alembic.ini"), "head")
    engine = make_engine(url)
    with engine.begin() as db:
        db.execute(
            text(
                "INSERT INTO context_snapshots(id, created_at, series_id, content_hash, payload) VALUES ('test', CURRENT_TIMESTAMP, 'VIX', 'hash', '{}')"
            )
        )
    for query in (
        "UPDATE context_snapshots SET series_id='DGS10'",
        "DELETE FROM context_snapshots",
    ):
        with engine.begin() as db:
            with pytest.raises(DatabaseError, match="Immutable"):
                db.execute(text(query))
    engine.dispose()


def test_periods_carry_previous_mark_and_do_not_mutate_saved_results():
    from app.analytics.periods import period_report

    result = {
        "equity": [
            {"date": "2019-12-30", "equity": "120"},
            {"date": "2019-12-31", "equity": "110"},
            {"date": "2020-01-02", "equity": "99"},
            {"date": "2020-01-03", "equity": "121"},
        ],
        "benchmark": {
            "equity": [
                {"date": "2019-12-30", "equity": "110"},
                {"date": "2019-12-31", "equity": "120"},
                {"date": "2020-01-02", "equity": "126"},
                {"date": "2020-01-03", "equity": "132"},
            ]
        },
        # UTC date is 2020, but this occurred on the NY 2019 session.
        "ledger": [
            {
                "kind": "buy",
                "timestamp": "2020-01-01T01:30:00+00:00",
                "fees": "2.50",
                "fx_cost": "0.20",
            }
        ],
    }
    original = deepcopy(result)
    reports = period_report(result, {"starting_capital": "100"})
    assert reports[0]["executed_orders"] == 1
    assert reports[1]["executed_orders"] == 0
    assert reports[1]["starting_equity"] == "110"
    assert reports[1]["return"] == "0.1"
    assert reports[1]["max_drawdown"] == "-0.1"
    assert reports[1]["benchmark_return"] == "0.1"
    assert result == original
    partial = period_report(
        result, {"starting_capital": "100"}, "month", date(2020, 1, 3), date(2020, 1, 3)
    )
    assert partial[0]["starting_equity"] == "99"
    assert partial[0]["ending_equity"] == "121"


def test_periods_zero_equity_and_invalid_ranges():
    from app.analytics.periods import period_report

    rows = period_report(
        {"equity": [{"date": "2019-12-31", "equity": "0"}, {"date": "2020-01-02", "equity": "0"}]},
        {"starting_capital": "100"},
    )
    assert rows[0]["return"] == "-1"
    assert rows[1]["return"] is None
    assert rows[1]["max_drawdown"] == "0"
    with pytest.raises(ValueError):
        period_report({}, {}, "year", date(2020, 1, 2), date(2020, 1, 1))


def test_period_endpoint_uses_completed_run_only_and_preserves_provenance(client, database, data):
    from app.services.jobs import process_one
    from tests.test_workflow import prepared

    dataset, _, version, profile = prepared(client, data)
    run = client.post(
        "/api/backtests",
        json={
            "strategy_version_ids": [version["id"]],
            "profile_id": profile["id"],
            "dataset_id": dataset["id"],
            "acknowledge_synthetic": True,
        },
    ).json()[0]
    assert client.get(f"/api/research/runs/{run['id']}/periods").status_code == 409
    process_one(database)
    result = client.get(f"/api/backtests/{run['id']}/results").json()
    report = client.get(f"/api/research/runs/{run['id']}/periods?frequency=quarter").json()
    assert report["provenance"]["dataset_hash"] == dataset["content_hash"]
    assert len(report["periods"]) == 2
    assert client.get(f"/api/backtests/{run['id']}/results").json() == result
