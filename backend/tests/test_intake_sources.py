"""Retained SEC source checks, capacity limits and append-only migrations."""

import json
from datetime import UTC, date, datetime
from types import SimpleNamespace

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import make_engine
from app.models.entities import CompanyPackage, IntakeArtifact, IntakeReport
from app.onboarding.contracts import IntakeRequest
from app.onboarding.evidence import retain_artifact
from app.onboarding.jobs import enqueue
from app.onboarding.sources import SourceClient, resolve_identity, sec_filings
from app.schemas.domain import canonical_hash


def assert_immutable_evidence(factory):
    """Shared SQLite/PostgreSQL assertions; only test-owned rows are created."""
    with factory() as db:
        intake = enqueue(
            db,
            IntakeRequest(
                symbol="NVDA",
                start="2020-01-02",
                end="2020-01-10",
                idempotency_key="migration-intake-test",
            ),
        )
        artifact = retain_artifact(
            db,
            intake.id,
            "https://example.invalid/test",
            "issuer_evidence",
            b"SYNTHETIC test evidence",
            {"symbol": "NVDA"},
        )
        report = IntakeReport(
            intake_id=intake.id,
            content_hash=canonical_hash({"report": "SYNTHETIC"}),
            payload={"report": "SYNTHETIC"},
        )
        db.add(report)
        db.flush()
        package = CompanyPackage(
            intake_id=intake.id,
            report_id=report.id,
            content_hash=canonical_hash({"package": "SYNTHETIC"}),
            payload={"package": "SYNTHETIC"},
        )
        db.add(package)
        db.commit()
        intake.status = "running"
        db.commit()  # Mutable job lifecycle is allowed.
        for field, value in [
            ("request_hash", "f" * 64),
            ("request_payload", {}),
            ("idempotency_key", "changed-request-key"),
        ]:
            setattr(intake, field, value)
            with pytest.raises(DatabaseError, match="[Ii]mmutable"):
                db.commit()
            db.rollback()
        rows = [
            (artifact, "body", b"altered"),
            (report, "payload", {}),
            (package, "payload", {}),
            (db.get(IntakeArtifact, (intake.id, artifact.id)), "artifact_id", "different"),
        ]
        for row, field, value in rows:
            setattr(row, field, value)
            with pytest.raises(DatabaseError, match="[Ii]mmutable"):
                db.commit()
            db.rollback()
            db.delete(row)
            with pytest.raises(DatabaseError, match="[Ii]mmutable"):
                db.commit()
            db.rollback()


def test_intake_sqlite_migrations_drift_and_immutable_evidence(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    settings.cache_clear()
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.check(config)
    engine = make_engine(url)
    try:
        assert_immutable_evidence(sessionmaker(engine, expire_on_commit=False))
        command.downgrade(config, "004_strategy_inputs")
        command.upgrade(config, "head")
        command.check(config)
    finally:
        engine.dispose()
        settings.cache_clear()


def test_source_host_and_byte_limits(database, monkeypatch):
    with database() as db:
        row = enqueue(
            db,
            IntakeRequest(
                symbol="NVDA",
                start="2020-01-02",
                end="2020-01-10",
                idempotency_key="bounded-intake-test",
            ),
        )
        client = SourceClient(db, row.id, lambda: None)
        for url in [
            "https://localhost/private",
            "https://www.sec.gov.evil.invalid/a",
            "https://data.alpaca.markets@evil.invalid/a",
        ]:
            with pytest.raises(ValueError, match="unsupported source host"):
                client.get(url, "test")
        monkeypatch.setenv("INTAKE_MAX_ARTIFACT_BYTES", "10")
        settings.cache_clear()
        with pytest.raises(ValueError, match="artifact size"):
            client.store("https://www.sec.gov/test", "test", b"x" * 11, {})
        monkeypatch.setenv("INTAKE_MAX_BYTES", "5")
        settings.cache_clear()
        with pytest.raises(ValueError, match="budget"):
            client.store("https://www.sec.gov/test", "test", b"123456", {})


class SECFixture:
    def __init__(self, attack=None):
        self.attack = attack
        self.calls = []

    def get(self, url, kind, **kwargs):
        self.calls.append(url)
        metadata = kwargs.get("metadata", {})
        if kind == "sec_identity":
            data = {
                "fields": ["cik", "name", "ticker", "exchange"],
                "data": [[1, "SYNTHETIC issuer", "NVDA", "Nasdaq"]],
            }
        elif kind == "sec_inventory":
            recent = {
                "form": ["8-K"],
                "accessionNumber": ["0000000001-20-000001"],
                "acceptanceDateTime": ["2020-01-02T21:05:00Z"],
                "filingDate": ["2020-01-02"],
                "primaryDocument": ["test.htm"],
                "items": ["2.02"],
            }
            data = {"filings": {"recent": recent, "files": []}}
        else:
            values = {
                "time": "20200102160500",
                "accession": "0000000001-20-000001",
                "cik": "0000000001",
                "form": "8-K",
                "item": "Item 2.02",
                "file": "test.htm",
            }
            if self.attack:
                values[self.attack] = {
                    "time": "20200102160501",
                    "accession": "0000000001-20-000002",
                    "cik": "0000000002",
                    "form": "10-K",
                    "item": "Item 9.01",
                    "file": "other.htm",
                }[self.attack]
            body = (
                f"<SEC-HEADER>\n<ACCEPTANCE-DATETIME>{values['time']}\nACCESSION NUMBER: {values['accession']}\nCENTRAL INDEX KEY: {values['cik']}\n</SEC-HEADER>"
                f"<DOCUMENT>\n<TYPE>{values['form']}\n<FILENAME>{values['file']}\n<TEXT><p>{values['item']} SYNTHETIC earnings</p></TEXT>\n</DOCUMENT>"
            ).encode()
            return SimpleNamespace(
                id="fixture", content_hash="a" * 64, body=body, metadata_json=metadata
            )
        return SimpleNamespace(
            id="fixture",
            content_hash="a" * 64,
            body=json.dumps(data).encode(),
            metadata_json=metadata,
        )


def test_sec_inventory_next_session_close_and_no_hindsight_tags():
    client = SECFixture()
    identity = resolve_identity(client, "NVDA")
    source, docs = sec_filings(
        client,
        identity,
        date(2020, 1, 1),
        date(2020, 1, 4),
        datetime(2020, 1, 1, tzinfo=UTC),
        datetime(2020, 1, 5, tzinfo=UTC),
        10,
    )
    event = source.events[0]
    assert event.available_at == datetime(2020, 1, 3, 21, tzinfo=UTC)
    assert event.published_at == event.available_at
    assert event.tags == ["sec_item_2_02"]
    assert not source.reviewed and not source.complete
    assert len(docs) == 1
    with pytest.raises(ValueError, match="unique current SEC"):
        resolve_identity(client, "MISSING")
    with pytest.raises(ValueError, match="exceeding requested"):
        sec_filings(
            client,
            identity,
            date(2020, 1, 1),
            date(2020, 1, 4),
            source.coverage_start,
            source.coverage_end,
            0,
        )


@pytest.mark.parametrize("attack", ["time", "accession", "cik", "form", "item", "file"])
def test_sec_primary_submission_mismatches_block(attack):
    client = SECFixture(attack)
    with pytest.raises(ValueError):
        sec_filings(
            client,
            resolve_identity(client, "NVDA"),
            date(2020, 1, 1),
            date(2020, 1, 4),
            datetime(2020, 1, 1, tzinfo=UTC),
            datetime(2020, 1, 5, tzinfo=UTC),
            10,
        )
