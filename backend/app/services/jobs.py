import logging
import time
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select, update

from app.backtesting.engine import ENGINE_VERSION, Cancelled, simulate
from app.core.config import settings
from app.models.entities import BacktestRun, Dataset, StrategyVersion, utcnow
from app.schemas.domain import ProfileConfig, StrategyConfig, canonical_hash
from app.services.datasets import load_dataset

logger = logging.getLogger(__name__)


def expire_stale(factory) -> int:
    with factory() as db:
        result = db.execute(
            update(BacktestRun)
            .where(
                BacktestRun.status == "running",
                BacktestRun.heartbeat_at
                < utcnow() - timedelta(seconds=settings().worker_lease_seconds),
            )
            .values(
                status="failed",
                completed_at=utcnow(),
                error="Worker lease expired; execution interrupted. Submit a new run to retry.",
                worker_token=None,
            )
        )
        db.commit()
        return result.rowcount


def claim(factory) -> tuple[str, str] | None:
    with factory() as db:
        candidate = db.scalar(
            select(BacktestRun.id)
            .where(BacktestRun.status == "queued", BacktestRun.cancel_requested.is_(False))
            .order_by(BacktestRun.created_at, BacktestRun.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not candidate:
            return None
        token = str(uuid4())
        result = db.execute(
            update(BacktestRun)
            .where(BacktestRun.id == candidate, BacktestRun.status == "queued")
            .values(
                status="running", worker_token=token, heartbeat_at=utcnow(), started_at=utcnow()
            )
        )
        db.commit()
        return (candidate, token) if result.rowcount == 1 else None


def process_one(factory) -> str | None:
    expire_stale(factory)
    ownership = claim(factory)
    if ownership is None:
        return None
    run_id, token = ownership
    logger.info("backtest_started", extra={"run_id": run_id})
    last_check = 0.0
    started_clock = time.monotonic()

    def checkpoint(progress):
        nonlocal last_check
        if time.monotonic() - started_clock > settings().worker_max_run_seconds:
            raise ValueError("Backtest exceeded the configured execution time limit")
        if time.monotonic() - last_check < 0.5:
            return
        with factory() as db:
            run = db.get(BacktestRun, run_id)
            if run.worker_token != token or run.status != "running" or run.cancel_requested:
                raise Cancelled()
            db.execute(
                update(BacktestRun)
                .where(
                    BacktestRun.id == run_id,
                    BacktestRun.worker_token == token,
                    BacktestRun.status == "running",
                )
                .values(heartbeat_at=utcnow(), progress=max(run.progress, progress))
            )
            db.commit()
        last_check = time.monotonic()

    try:
        with factory() as db:
            run = db.get(BacktestRun, run_id)
            version = db.get(StrategyVersion, run.strategy_version_id)
            dataset = db.get(Dataset, run.dataset_id)
            if run.provenance["engine_version"] != ENGINE_VERSION:
                raise ValueError(
                    "queued run engine version differs from worker; resubmit explicitly"
                )
            data = load_dataset(db, dataset)
            config = StrategyConfig.model_validate(version.config)
            if canonical_hash(config.model_dump(mode="json")) != version.config_hash:
                raise ValueError("strategy configuration hash mismatch")
            profile = ProfileConfig.model_validate(run.profile_snapshot)
        result = simulate(config, profile, data, checkpoint)
        checkpoint(99)
        with factory() as db:
            run = db.scalar(select(BacktestRun).where(BacktestRun.id == run_id).with_for_update())
            if run.worker_token == token and run.status == "running":
                if run.cancel_requested:
                    run.status = "cancelled"
                else:
                    run.result = result
                    run.status = "completed"
                    run.progress = 100
                run.completed_at = utcnow()
                run.worker_token = None
                db.commit()
        logger.info("backtest_finished", extra={"run_id": run_id})
    except Exception as exc:
        with factory() as db:
            db.execute(
                update(BacktestRun)
                .where(
                    BacktestRun.id == run_id,
                    BacktestRun.worker_token == token,
                    BacktestRun.status == "running",
                )
                .values(
                    status="cancelled" if isinstance(exc, Cancelled) else "failed",
                    error=None if isinstance(exc, Cancelled) else str(exc)[:2000],
                    completed_at=utcnow(),
                    worker_token=None,
                )
            )
            db.commit()
        if not isinstance(exc, Cancelled):
            logger.exception("backtest_failed", extra={"run_id": run_id})
    return run_id
