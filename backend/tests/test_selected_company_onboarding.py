"""User-selected company contracts with explicit SYNTHETIC, offline provider fixtures.

Names/flags exercise the real-data review path; these fixtures qualify no real
company, historical source or financial performance.
"""

import json
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import func, select

from app.market_data.calendar import session_times, sessions
from app.market_data.strategy_inputs import StrategyInput
from app.models.entities import CompanyPackage, Dataset
from app.onboarding import collect as collector
from app.onboarding.sources import SourceClient
from app.schemas.domain import Action, canonical_hash
from app.services.datasets import import_dataset, load_dataset
from app.services.strategy_inputs import resolve_inputs
from tests.conftest import fixture_data
from tests.test_company_onboarding import collected, request, review_body

NY = ZoneInfo("America/New_York")


@pytest.fixture
def selected_sources(monkeypatch, database):
    calls = {"prices": [], "actions": [], "filings": []}
    # Reviewed benchmark fixtures let each requested company require its own review.
    baseline = fixture_data(date(2019, 12, 1), date(2020, 3, 31))
    baseline.name = "SYNTHETIC selected-company benchmark fixtures"
    baseline.bars.extend(b.model_copy(update={"symbol": "QQQ"}) for b in baseline.bars[:])
    baseline.synthetic = False
    baseline.fx = []
    baseline.corporate_actions_reviewed = baseline.dividends_complete = True
    baseline.actions = [
        Action(
            symbol=symbol,
            session_date="2020-01-15",
            kind="dividend",
            value="0.10",
            payment_date="2020-01-17",
            available_at="2020-01-02T21:00:00Z",
        )
        for symbol in ["SPY", "QQQ"]
    ]
    with database() as db:
        import_dataset(db, baseline)

    def identity_document(client, url, kind, **kwargs):
        assert kind == "sec_identity", "Every other external call must be explicitly mocked"
        payload = {
            "fields": ["cik", "name", "ticker", "exchange"],
            "data": [
                [index + 1, f"SYNTHETIC issuer {symbol}", symbol, "Nasdaq"]
                for index, symbol in enumerate(["AMD", "CVS", "BRK-B", "ZXQTEST"])
            ],
        }
        return client.store(url, kind, json.dumps(payload).encode(), {})

    def prices(provider, symbols, start, end, *, feed):
        calls["prices"].append({"symbols": symbols[:], "start": start, "end": end, "feed": feed})
        raw = fixture_data(start, end)
        raw.name = "SYNTHETIC selected-company price fixture"
        raw.synthetic, raw.fx = False, []
        raw.bars = [b.model_copy(update={"symbol": symbol}) for symbol in symbols for b in raw.bars]
        provider.response_observer(
            httpx.Response(
                200,
                json={"SYNTHETIC_symbols": symbols},
                request=httpx.Request("GET", "https://data.alpaca.markets/v2/stocks/bars"),
            )
        )
        return raw

    def actions(client, symbols, start, end):
        calls["actions"].append(symbols[:])
        return [
            {
                "kind": "cash_dividends",
                "artifact_id": "SYNTHETIC-broker-candidate",
                "record": {
                    "id": f"SYNTHETIC-{symbol}-{end}",
                    "symbol": symbol,
                    "ex_date": sessions(start, end)[-1].isoformat(),
                    "payable_date": end.isoformat(),
                    "rate": "0.16",
                },
            }
            for symbol in symbols
        ]

    def filings(client, identity, start, end, coverage_start, coverage_end, limit):
        symbol = identity["symbol"]
        calls["filings"].append(symbol)
        available = session_times(sessions(coverage_start.date(), coverage_end.date())[0])[1]
        text = f"SYNTHETIC issuer {symbol} declares a cash dividend of $0.16 per share payable {end.isoformat()}."
        artifact = client.store(
            f"https://example.invalid/SYNTHETIC/{symbol}/{end}",
            "sec_submission",
            text.encode(),
            {"symbol": symbol, "available_at": available.isoformat()},
        )
        return StrategyInput(
            kind="events",
            name=f"SYNTHETIC {symbol} source fixture",
            source="SYNTHETIC offline provider",
            source_url=artifact.source_url,
            availability_policy="SYNTHETIC explicit publication fixture; not real source qualification.",
            symbols=[symbol],
            stream_id="SEC_FILINGS",
            coverage_start=coverage_start,
            coverage_end=coverage_end,
            events=[
                {
                    "event_id": f"SYNTHETIC-{symbol}",
                    "published_at": available,
                    "available_at": available,
                    "category": "sec_8k",
                    "tags": ["sec_item_2_02"],
                    "symbols": [symbol],
                    "title": f"SYNTHETIC {symbol} filing",
                    "source_url": artifact.source_url,
                    "original_content_hash": artifact.content_hash,
                    "derivation": "SYNTHETIC literal filing-presence fixture; no real source qualification.",
                }
            ],
        ), []

    monkeypatch.setattr(SourceClient, "get", identity_document)
    monkeypatch.setattr(collector.AlpacaProvider, "fetch", prices)
    monkeypatch.setattr(collector, "alpaca_actions", actions)
    monkeypatch.setattr(collector, "sec_filings", filings)
    return calls


@pytest.mark.parametrize(
    "symbol,benchmark,start,end,warmup,lookback",
    [
        ("AMD", "SPY", "2020-01-06", "2020-01-17", 4, 1),
        ("CVS", "QQQ", "2020-02-03", "2020-02-14", 10, 7),
        ("BRK.B", "SPY", "2019-12-30", "2020-01-10", 7, 2),
        ("ZXQTEST", "QQQ", "2020-03-02", "2020-03-13", 14, 1),
    ],
)
def test_selected_company_dates_benchmark_and_evidence_reach_reviewed_package(
    client, database, selected_sources, symbol, benchmark, start, end, warmup, lookback
):
    identifier, detail = collected(
        client,
        database,
        symbol=symbol,
        benchmark=benchmark,
        start=start,
        end=end,
        warmup_days=warmup,
        event_lookback_days=lookback,
    )
    first = date.fromisoformat(start) - timedelta(days=warmup)
    assert selected_sources["prices"] == [
        {
            "symbols": sorted([symbol, benchmark]),
            "start": first,
            "end": date.fromisoformat(end),
            "feed": "sip",
        }
    ]
    assert selected_sources["actions"] == [[symbol]]
    assert selected_sources["filings"] == [symbol]
    report = detail["report"]["payload"]
    assert report["identity"]["symbol"] == symbol
    assert report["identity"]["sec_ticker"] == symbol.replace(".", "-")
    assert datetime.fromisoformat(report["coverage_start"]) == datetime.combine(
        sessions(date.fromisoformat(start), date.fromisoformat(end))[0] - timedelta(days=lookback),
        time(),
        NY,
    )
    response = client.post(f"/api/company-intakes/{identifier}/approve", json=review_body(detail))
    assert response.status_code == 201, response.text
    package = response.json()
    for key, value in {
        "symbol": symbol,
        "benchmark": benchmark,
        "start": start,
        "end": end,
        "warmup_days": warmup,
        "event_lookback_days": lookback,
    }.items():
        assert package["payload"]["scope"][key] == value
    with database() as db:
        output = load_dataset(db, db.get(Dataset, package["payload"]["dataset"]["id"]))
        assert {b.symbol for b in output.bars} == {symbol, benchmark}
        assert {b.session_date for b in output.bars} == set(
            sessions(first, date.fromisoformat(end))
        )
        assert {a.symbol for a in output.actions} <= {symbol, benchmark}
        assert {a.symbol for a in output.actions} >= {symbol}
        _, sources = resolve_inputs(db, [r["id"] for r in package["payload"]["strategy_inputs"]])
        assert sources[0].symbols == [symbol] and sources[0].events[0].symbols == [symbol]
    assert package["payload"]["strategy_readiness_required"]


def test_repeated_selection_reuses_reviewed_revisions_without_provider_refetch(
    client, database, selected_sources
):
    identifier, first = collected(client, database, symbol="CVS")
    body = review_body(first)
    approved = client.post(f"/api/company-intakes/{identifier}/approve", json=body).json()
    calls_before = {key: value[:] for key, value in selected_sources.items()}
    second_id, second = collected(client, database, symbol="CVS")
    assert second_id != identifier
    report = second["report"]["payload"]
    assert all(cap["state"] == "reviewed" for cap in report["capabilities"].values())
    assert report["candidate_dataset_id"] == approved["payload"]["dataset"]["id"]
    assert report["candidate_source_id"] == approved["payload"]["strategy_inputs"][0]["id"]
    assert selected_sources == calls_before
    result = client.post(f"/api/company-intakes/{second_id}/approve", json=review_body(second))
    assert result.status_code == 201, result.text
    assert result.json()["payload"]["dataset"] == approved["payload"]["dataset"]
    assert result.json()["payload"]["strategy_inputs"] == approved["payload"]["strategy_inputs"]
    assert client.get(f"/api/company-intakes/{identifier}").json()["report"] == first["report"]


def test_switching_companies_keeps_revisions_and_evidence_isolated(
    client, database, selected_sources
):
    first_id, first = collected(client, database, symbol="AMD")
    first_package = client.post(
        f"/api/company-intakes/{first_id}/approve", json=review_body(first)
    ).json()
    second_id, second = collected(client, database, symbol="CVS")
    body = review_body(second)
    body["actions"][0]["artifact_id"] = first["report"]["payload"]["action_proposals"][0][
        "artifact_id"
    ]
    assert client.post(f"/api/company-intakes/{second_id}/approve", json=body).status_code == 422
    response = client.post(f"/api/company-intakes/{second_id}/approve", json=review_body(second))
    assert response.status_code == 201, response.text
    second_package = response.json()
    assert second_package["payload"]["dataset"]["id"] != first_package["payload"]["dataset"]["id"]
    assert (
        second_package["payload"]["strategy_inputs"] != first_package["payload"]["strategy_inputs"]
    )
    assert client.get(f"/api/company-intakes/{first_id}").json()["packages"] == [first_package]
    with database() as db:
        first_data = load_dataset(db, db.get(Dataset, first_package["payload"]["dataset"]["id"]))
        second_data = load_dataset(db, db.get(Dataset, second_package["payload"]["dataset"]["id"]))
        assert {b.symbol for b in first_data.bars} == {"AMD", "SPY"}
        assert {b.symbol for b in second_data.bars} == {"CVS", "SPY"}
        assert {a.symbol for a in second_data.actions} == {"CVS"}


def test_selected_benchmark_can_equal_the_company_without_duplicate_fetches(
    client, database, selected_sources
):
    identifier, detail = collected(client, database, symbol="AMD", benchmark="AMD")
    assert selected_sources["prices"][0]["symbols"] == ["AMD"]
    response = client.post(f"/api/company-intakes/{identifier}/approve", json=review_body(detail))
    assert response.status_code == 201, response.text


@pytest.mark.parametrize("symbol", ["", "msft", "../MSFT", "NYSE:MSFT", "$AAPL", "AAPL;DROP"])
def test_invalid_user_selection_never_enters_the_queue(client, selected_sources, symbol):
    assert client.post("/api/company-intakes", json=request(symbol=symbol)).status_code == 422
    assert client.get("/api/company-intakes").json() == []
    assert all(not calls for calls in selected_sources.values())


def test_unresolved_company_stays_blocked_and_never_fetches_prices(
    client, database, selected_sources
):
    identifier, detail = collected(client, database, symbol="MISSING")
    report = detail["report"]["payload"]
    assert report["identity"] is None
    assert all(cap["state"] == "blocked" for cap in report["capabilities"].values())
    assert all(not calls for calls in selected_sources.values())
    assert (
        client.post(
            f"/api/company-intakes/{identifier}/approve", json=review_body(detail)
        ).status_code
        == 422
    )
    with database() as db:
        assert db.scalar(select(func.count()).select_from(CompanyPackage)) == 0
    assert canonical_hash(report) == detail["report"]["content_hash"]
