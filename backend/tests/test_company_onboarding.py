"""Synthetic, network-isolated intake workflow and adversarial review checks."""

from datetime import date, timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select, update

from app.core.config import settings
from app.market_data.strategy_inputs import StrategyInput
from app.models.entities import (
    CompanyIntake,
    CompanyPackage,
    Dataset,
    IntakeReport,
    SourceArtifact,
    utcnow,
)
from app.onboarding import collect as collector
from app.onboarding.contracts import IntakeRequest
from app.onboarding.jobs import claim, enqueue, process_intake_one
from app.schemas.domain import canonical_hash
from app.services.datasets import import_dataset, load_dataset
from app.services.strategy_inputs import resolve_inputs

QUOTE = "SYNTHETIC issuer declares a cash dividend of $0.16 per share, payable January 10, 2020."


def request(**changes):
    return {
        "symbol": "NVDA",
        "start": "2020-01-02",
        "end": "2020-01-10",
        "warmup_days": 0,
        "account_currency": "USD",
        "idempotency_key": str(uuid4()),
        **changes,
    }


@pytest.fixture
def mock_sources(monkeypatch, data, database):
    # Financial fixture remains visibly named SYNTHETIC; false flag exercises real-data gates only.
    sample = data.model_copy(deep=True)
    sample.bars = [b for b in sample.bars if b.session_date <= date(2020, 1, 10)]
    sample.fx = []
    sample.synthetic = False
    sample.corporate_actions_reviewed = sample.dividends_complete = True
    with database() as db:
        import_dataset(db, sample)
    raw = sample.model_copy(deep=True)
    raw.bars.extend(b.model_copy(update={"symbol": "NVDA"}) for b in sample.bars)
    raw.corporate_actions_reviewed = raw.dividends_complete = False

    def identity(client, symbol):
        artifact = client.store(
            "https://www.sec.gov/files/company_tickers_exchange.json",
            "sec_identity",
            b'{"SYNTHETIC":true}',
            {},
        )
        return {
            "symbol": symbol,
            "cik": "0000000001",
            "name": "SYNTHETIC issuer",
            "exchange": "Nasdaq",
            "artifact_id": artifact.id,
        }

    def prices(provider, *args, **kwargs):
        provider.response_observer(
            httpx.Response(
                200,
                json={"SYNTHETIC": True},
                request=httpx.Request("GET", "https://data.alpaca.markets/v2/stocks/bars"),
            )
        )
        return raw

    def filings(client, identity, start, end, coverage_start, coverage_end, limit):
        client.store(
            "https://www.sec.gov/Archives/SYNTHETIC.txt",
            "sec_submission",
            QUOTE.encode(),
            {"symbol": identity["symbol"], "available_at": "2020-01-03T21:00:00+00:00"},
        )
        return StrategyInput(
            kind="events",
            name="SYNTHETIC intake filings",
            source="SYNTHETIC SEC fixture",
            source_url="https://example.invalid/fixture",
            availability_policy="SYNTHETIC next-session-close policy",
            symbols=[identity["symbol"]],
            stream_id="SEC_FILINGS",
            coverage_start=coverage_start,
            coverage_end=coverage_end,
        ), []

    monkeypatch.setattr(collector, "resolve_identity", identity)
    monkeypatch.setattr(collector.AlpacaProvider, "fetch", prices)
    monkeypatch.setattr(collector, "sec_filings", filings)
    monkeypatch.setattr(
        collector,
        "alpaca_actions",
        lambda *args: [
            {
                "kind": "cash_dividends",
                "artifact_id": "fixture",
                "record": {
                    "id": "SYNTHETIC-dividend",
                    "symbol": "NVDA",
                    "ex_date": "2020-01-08",
                    "rate": "0.16",
                    "payable_date": "2020-01-10",
                },
            }
        ],
    )
    return raw


def collected(client, database, **changes):
    created = client.post("/api/company-intakes", json=request(**changes))
    assert created.status_code == 201, created.text
    identifier = created.json()["id"]
    assert "worker_token" not in created.json()
    assert process_intake_one(database) == identifier
    detail = client.get(f"/api/company-intakes/{identifier}").json()
    assert detail["status"] == "awaiting_review", detail
    return identifier, detail


def review_body(detail):
    return {
        "expected_report_hash": detail["report"]["content_hash"],
        "approve_capabilities": ["daily_accounting", "sec_filings"],
        "acknowledge_policies": True,
        "attest_historical_identity": True,
        "attest_action_coverage": True,
        "note": "SYNTHETIC test review of identity, issuer records, nominal basis and complete interval.",
        "actions": [
            {k: p[k] for k in ["action", "artifact_id", "quote"]}
            for p in detail["report"]["payload"]["action_proposals"]
        ],
    }


def test_collection_is_not_approval_and_review_keeps_blocked_capabilities(
    client, database, mock_sources
):
    identifier, detail = collected(
        client, database, capabilities=["daily_accounting", "sec_filings", "historical_sectors"]
    )
    report = detail["report"]["payload"]
    assert report["capabilities"]["historical_sectors"]["state"] == "blocked"
    assert not detail["packages"]
    with database() as db:
        assert not load_dataset(
            db, db.get(Dataset, report["candidate_dataset_id"])
        ).corporate_actions_reviewed
        assert db.scalar(select(func.count()).select_from(CompanyPackage)) == 0
    body = review_body(detail)
    result = client.post(f"/api/company-intakes/{identifier}/approve", json=body)
    assert result.status_code == 201, result.text
    package = result.json()
    assert package["payload"]["ready_capabilities"] == ["daily_accounting", "sec_filings"]
    assert package["payload"]["strategy_readiness_required"]
    with database() as db:
        final = load_dataset(db, db.get(Dataset, package["payload"]["dataset"]["id"]))
        assert final.corporate_actions_reviewed and final.dividends_complete
        assert str(final.actions[0].value) == "0.16"
        _, sources = resolve_inputs(db, [r["id"] for r in package["payload"]["strategy_inputs"]])
        assert sources[0].reviewed and sources[0].complete
        assert sources[0].parent_id == report["candidate_source_id"]
        assert not load_dataset(
            db, db.get(Dataset, report["candidate_dataset_id"])
        ).corporate_actions_reviewed
    again = client.post(f"/api/company-intakes/{identifier}/approve", json=body)
    assert again.json()["id"] == package["id"]
    assert (
        client.get(f"/api/company-intakes/{identifier}").json()["report"]["payload"][
            "capabilities"
        ]["historical_sectors"]["state"]
        == "blocked"
    )


@pytest.mark.parametrize(
    "attack",
    [
        "missing",
        "quote",
        "amount",
        "payment",
        "early",
        "late",
        "duplicate",
        "scope",
        "foreign",
        "stale",
        "coverage",
        "blocked",
        "identity",
        "policies",
    ],
)
def test_review_fails_closed(client, database, mock_sources, attack):
    identifier, detail = collected(
        client, database, capabilities=["daily_accounting", "sec_filings", "company_news"]
    )
    body = review_body(detail)
    proof = body["actions"][0]
    if attack == "missing":
        body["actions"] = []
    elif attack == "quote":
        proof["quote"] = "Invented issuer quotation that never appeared in the retained document."
    elif attack == "amount":
        proof["action"]["value"] = "0.17"
    elif attack == "payment":
        proof["action"]["payment_date"] = "2020-01-13"
    elif attack == "early":
        proof["action"]["available_at"] = "2020-01-02T21:00:00Z"
    elif attack == "late":
        proof["action"]["available_at"] = "2020-01-08T21:00:00Z"
    elif attack == "duplicate":
        body["actions"].append(proof)
    elif attack == "scope":
        proof["action"]["symbol"] = "MSFT"
    elif attack == "foreign":
        proof["artifact_id"] = str(uuid4())
    elif attack == "stale":
        body["expected_report_hash"] = "f" * 64
    elif attack == "coverage":
        body["attest_action_coverage"] = False
    elif attack == "blocked":
        body["approve_capabilities"] = ["company_news"]
    elif attack == "identity":
        body["attest_historical_identity"] = False
    elif attack == "policies":
        body["acknowledge_policies"] = False
    with database() as db:
        before = db.scalar(select(func.count()).select_from(Dataset))
    response = client.post(f"/api/company-intakes/{identifier}/approve", json=body)
    assert response.status_code == 422, response.text
    with database() as db:
        assert db.scalar(select(func.count()).select_from(CompanyPackage)) == 0
        assert db.scalar(select(func.count()).select_from(Dataset)) == before


def test_request_persistence_idempotency_cancel_retry_and_secret_free_configuration(
    client, database
):
    body = request()
    first = client.post("/api/company-intakes", json=body).json()
    assert client.post("/api/company-intakes", json=body).json()["id"] == first["id"]
    assert client.post("/api/company-intakes", json={**body, "symbol": "MSFT"}).status_code == 422
    assert client.post(f"/api/company-intakes/{first['id']}/retry").status_code == 422
    with database() as db:
        row = db.get(CompanyIntake, first["id"])
        assert canonical_hash(row.request_payload) == row.request_hash
    assert client.post(f"/api/company-intakes/{first['id']}/cancel").json()["status"] == "cancelled"
    assert claim(database) is None
    retry = client.post(f"/api/company-intakes/{first['id']}/retry").json()
    assert retry["id"] != first["id"] and retry["request_payload"]["refresh"]
    assert len(client.get("/api/company-intakes").json()) == 2
    config = client.get("/api/company-intakes/configuration").json()
    assert isinstance(config["configured"]["alpaca"], bool)
    assert "api_key" not in str(config) and "@" not in str(config)


def test_cancellation_during_collection_and_expired_lease(database, monkeypatch):
    with database() as db:
        row = enqueue(db, IntakeRequest.model_validate(request()))
        identifier = row.id

    def cancel(db, intake_id, request, checkpoint):
        with database() as other:
            other.execute(
                update(CompanyIntake)
                .where(CompanyIntake.id == intake_id)
                .values(cancel_requested=True)
            )
            other.commit()
        checkpoint()

    monkeypatch.setattr("app.onboarding.jobs.collect", cancel)
    assert process_intake_one(database) == identifier
    with database() as db:
        assert db.get(CompanyIntake, identifier).status == "cancelled"
        assert db.scalar(select(IntakeReport)) is None
        row = enqueue(db, IntakeRequest.model_validate(request()))
        row.status, row.worker_token = "running", "expired"
        row.heartbeat_at = utcnow() - timedelta(seconds=settings().worker_lease_seconds + 1)
        other_id = row.id
        db.commit()
    assert claim(database) is None
    with database() as db:
        assert db.get(CompanyIntake, other_id).status == "failed"


def test_evidence_integrity_untrusted_urls_and_unsupported_request(client, database, mock_sources):
    identifier, detail = collected(client, database, capabilities=["historical_sectors"])
    assert detail["report"]["payload"]["capabilities"]["historical_sectors"]["state"] == "blocked"
    upload = {
        "symbol": "NVDA",
        "source_url": "https://127.0.0.1/private",
        "title": "SYNTHETIC transcript",
        "text": QUOTE,
        "available_at": "2020-01-03T21:00:00Z",
        "clock_policy": "SYNTHETIC reviewer supplied publication clock.",
    }
    response = client.post(f"/api/company-intakes/{identifier}/evidence", json=upload)
    assert response.status_code == 201  # No outbound request; URL is only a provenance label.
    artifact = response.json()
    downloaded = client.get(f"/api/company-intakes/{identifier}/artifacts/{artifact['id']}")
    assert downloaded.content.decode() == QUOTE
    assert "attachment" in downloaded.headers["content-disposition"]
    assert downloaded.headers["x-content-type-options"] == "nosniff"
    with database() as db:
        row = db.get(SourceArtifact, artifact["id"])
        row.body = b"tampered"
        db.commit()  # create_all fixture has no triggers; application must also verify hashes.
    assert (
        client.get(f"/api/company-intakes/{identifier}/artifacts/{artifact['id']}").status_code
        == 422
    )


def test_missing_fx_and_price_gaps_block_without_substitution(client, database, mock_sources):
    identifier, detail = collected(client, database, account_currency="SGD")
    assert detail["report"]["payload"]["capabilities"]["daily_accounting"]["state"] == "blocked"
    assert "FX" in detail["report"]["payload"]["capabilities"]["daily_accounting"]["reason"]
    body = review_body(detail)
    assert client.post(f"/api/company-intakes/{identifier}/approve", json=body).status_code == 422
    mock_sources.bars = [
        b for b in mock_sources.bars if b.symbol != "NVDA" or b.session_date != date(2020, 1, 6)
    ]
    _, detail = collected(client, database)
    assert (
        "Missing requested raw price sessions"
        in detail["report"]["payload"]["capabilities"]["daily_accounting"]["reason"]
    )


def test_split_evidence_requires_effective_date_and_ratio(
    client, database, mock_sources, monkeypatch
):
    from app.onboarding.contracts import ActionEvidence
    from app.onboarding.evidence import retain_artifact
    from app.onboarding.review import evidence_action

    identifier, detail = collected(client, database)
    text = "SYNTHETIC issuer: ten-for-one stock split, effective January 8, 2020."
    with database() as db:
        artifact = retain_artifact(
            db,
            identifier,
            "https://example.invalid/split",
            "issuer_evidence",
            text.encode(),
            {"symbol": "NVDA", "available_at": "2020-01-03T21:00:00Z"},
        )
        action = {
            "symbol": "NVDA",
            "kind": "split",
            "session_date": "2020-01-08",
            "value": "10",
            "available_at": "2020-01-03T21:00:00Z",
        }
        assert (
            evidence_action(
                db, identifier, ActionEvidence(action=action, artifact_id=artifact.id, quote=text)
            ).value
            == 10
        )
        for changes in [{"value": "4"}, {"session_date": "2020-01-09"}]:
            with pytest.raises(ValueError, match="split ratio and effective date"):
                evidence_action(
                    db,
                    identifier,
                    ActionEvidence(
                        action={**action, **changes}, artifact_id=artifact.id, quote=text
                    ),
                )


def test_request_bounds_and_credential_error_reports(client, database, monkeypatch):
    for changes in [
        {"warmup_days": 1097},
        {"start": "1989-01-01"},
        {"end": "2035-01-01"},
        {"capabilities": ["sec_filings", "sec_filings"]},
    ]:
        assert client.post("/api/company-intakes", json=request(**changes)).status_code == 422
    monkeypatch.setenv("DATA_SOURCE_CONTACT_EMAIL", "")
    settings.cache_clear()
    _, detail = collected(client, database)
    assert all(
        c["state"] == "blocked" for c in detail["report"]["payload"]["capabilities"].values()
    )
    assert "DATA_SOURCE_CONTACT_EMAIL" in detail["report"]["payload"]["findings"][0]["message"]


def test_package_publication_is_atomic_on_source_failure(
    client, database, mock_sources, monkeypatch
):
    identifier, detail = collected(client, database)
    with database() as db:
        before = db.scalar(select(func.count()).select_from(Dataset))

    def fail(*args, **kwargs):
        raise ValueError("SYNTHETIC source retention failure after accounting preflight")

    monkeypatch.setattr("app.onboarding.review.retain_input", fail)
    response = client.post(f"/api/company-intakes/{identifier}/approve", json=review_body(detail))
    assert response.status_code == 422
    with database() as db:
        assert db.scalar(select(func.count()).select_from(Dataset)) == before
        assert db.scalar(select(func.count()).select_from(CompanyPackage)) == 0


def test_expired_worker_cannot_publish_or_overwrite_new_owner(database, monkeypatch):
    with database() as db:
        identifier = enqueue(db, IntakeRequest.model_validate(request())).id

    def lose_lease(db, intake_id, request, checkpoint):
        with database() as other:
            other.execute(
                update(CompanyIntake)
                .where(CompanyIntake.id == intake_id)
                .values(worker_token="replacement-owner")
            )
            other.commit()
        checkpoint()

    monkeypatch.setattr("app.onboarding.jobs.collect", lose_lease)
    process_intake_one(database)
    with database() as db:
        row = db.get(CompanyIntake, identifier)
        assert row.status == "running" and row.worker_token == "replacement-owner"
        assert db.scalar(select(IntakeReport)) is None


def test_queue_capacity_preserves_existing_idempotent_requests(client, monkeypatch):
    monkeypatch.setenv("MAX_ACTIVE_JOBS", "1")
    settings.cache_clear()
    body = request()
    first = client.post("/api/company-intakes", json=body)
    assert first.status_code == 201
    assert client.post("/api/company-intakes", json=body).json()["id"] == first.json()["id"]
    assert client.post("/api/company-intakes", json=request()).status_code == 422


def test_collection_deadline_produces_no_report_or_package(database, monkeypatch):
    from types import SimpleNamespace

    with database() as db:
        identifier = enqueue(db, IntakeRequest.model_validate(request())).id
    ticks = iter([0.0, float(settings().intake_max_seconds + 1)])
    monkeypatch.setattr("app.onboarding.jobs.time", SimpleNamespace(monotonic=lambda: next(ticks)))
    monkeypatch.setattr(
        "app.onboarding.jobs.collect", lambda db, identifier, request, checkpoint: checkpoint()
    )
    process_intake_one(database)
    with database() as db:
        row = db.get(CompanyIntake, identifier)
        assert row.status == "failed" and "time limit" in row.error
        assert db.scalar(select(IntakeReport)) is None
        assert db.scalar(select(CompanyPackage)) is None
