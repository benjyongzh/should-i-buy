import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import sessionmaker

from app.backtesting.engine import ENGINE_VERSION
from app.core.config import settings
from app.market_data.demo import synthetic_demo
from app.models.entities import (
    BacktestRun,
    ContextSnapshot,
    Dataset,
    Profile,
    Strategy,
    StrategyInputRevision,
    StrategyVersion,
)
from app.schemas.domain import ProfileConfig, TradingPolicy, canonical_hash, default_strategy
from app.services.datasets import import_dataset
from app.services.jobs import claim, process_one


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="TEST_POSTGRES_URL not configured")
def test_postgres_migrations_immutable_inputs_and_concurrent_claims(monkeypatch):
    url = os.environ["TEST_POSTGRES_URL"]
    admin = create_engine(url)
    schema = "lab_test_" + uuid4().hex
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    test_url = (
        make_url(url)
        .update_query_dict({"options": f"-csearch_path={schema}"})
        .render_as_string(hide_password=False)
    )
    monkeypatch.setenv("DATABASE_URL", test_url)
    settings.cache_clear()
    engine = create_engine(test_url)
    factory = sessionmaker(engine, expire_on_commit=False)
    try:
        config = Config("alembic.ini")
        command.upgrade(config, "head")
        command.check(config)
        with factory() as db:
            snapshot = ContextSnapshot(
                series_id="VIX", content_hash="test-context-hash", payload={}
            )
            db.add(snapshot)
            db.commit()
            snapshot.series_id = "DGS10"
            with pytest.raises(DatabaseError, match="Immutable"):
                db.commit()
            db.rollback()
            db.delete(snapshot)
            with pytest.raises(DatabaseError, match="Immutable"):
                db.commit()
            db.rollback()
        with factory() as db:
            source = StrategyInputRevision(
                kind="events", content_hash="test-strategy-source-hash", payload={}
            )
            db.add(source)
            db.commit()
            source.kind = "universe"
            with pytest.raises(DatabaseError, match="Immutable"):
                db.commit()
            db.rollback()
            db.delete(source)
            with pytest.raises(DatabaseError, match="Immutable"):
                db.commit()
            db.rollback()
        with factory() as db:
            data = synthetic_demo()
            data.bars, data.fx = data.bars[:5], data.fx[:5]
            dataset = import_dataset(db, data)
            funded_config = default_strategy()
            funded_config.trading = TradingPolicy(allow_additions=True)
            strategy = Strategy(
                name="PG concurrency test", draft=funded_config.model_dump(mode="json")
            )
            profile = Profile(
                name="PG profile",
                config=ProfileConfig(
                    monthly_contribution="500",
                    start_date=data.bars[0].session_date,
                    end_date=data.bars[-1].session_date,
                ).model_dump(mode="json"),
            )
            db.add_all([strategy, profile])
            db.flush()
            version = StrategyVersion(
                strategy_id=strategy.id,
                number=1,
                config=strategy.draft,
                config_hash=canonical_hash(strategy.draft),
                schema_version=1,
            )
            db.add(version)
            db.flush()
            for _ in range(8):
                db.add(
                    BacktestRun(
                        strategy_version_id=version.id,
                        profile_id=profile.id,
                        dataset_id=dataset.id,
                        profile_snapshot=profile.config,
                        provenance={"engine_version": ENGINE_VERSION},
                    )
                )
            db.commit()
            dataset_id = dataset.id
        with ThreadPoolExecutor(max_workers=8) as executor:
            claimed = list(executor.map(lambda _: claim(factory), range(8)))
        assert len({r[0] for r in claimed if r}) == 8
        assert claim(factory) is None
        with factory() as db:
            run = db.get(BacktestRun, claimed[0][0])
            run.status = "queued"
            run.worker_token = None
            db.commit()
        assert process_one(factory) == claimed[0][0]
        with factory() as db:
            run = db.get(BacktestRun, claimed[0][0])
            assert run.status == "completed", run.error
            assert len(run.result["equity"]) == 5
            assert run.result["metrics"]["total_contributions"] == "500"
        with factory() as db:
            row = db.get(Dataset, dataset_id)
            row.name = "Not allowed"
            with pytest.raises(DatabaseError, match="Immutable"):
                db.commit()
            db.rollback()
        command.downgrade(config, "base")
        command.upgrade(config, "head")
    finally:
        engine.dispose()
        with admin.begin() as connection:
            # Only this randomly named test-owned schema is removed.
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
        settings.cache_clear()
