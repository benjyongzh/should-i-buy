from collections.abc import Collection
from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.api.contracts import (
    CSVImport,
    DatasetOut,
    ExperimentOut,
    ProfileOut,
    ProfileWrite,
    Publish,
    RunOut,
    Schedule,
    StrategyCreate,
    StrategyEdit,
    StrategyOut,
    VersionOut,
)
from app.backtesting.engine import ENGINE_VERSION
from app.core.config import settings
from app.db.session import Base, get_db
from app.market_data.features import FeatureBook, validate_features
from app.market_data.providers import AlpacaProvider, csv_records
from app.market_data.validation import validate_coverage
from app.models.entities import (
    BacktestRun,
    Dataset,
    Experiment,
    Profile,
    Strategy,
    StrategyVersion,
    utcnow,
)
from app.schemas.domain import (
    Action,
    DatasetInput,
    FXObservation,
    ProfileConfig,
    StrategyConfig,
    StrictModel,
    Symbol,
    canonical_hash,
)
from app.services.datasets import import_dataset, load_dataset
from app.services.feature_inputs import context_content_hash, resolve_features
from app.services.strategy_inputs import resolve_inputs

router = APIRouter(prefix="/api")


def get[ModelType: Base](db: Session, model: type[ModelType], identifier: str) -> ModelType:
    row = db.get(model, identifier)
    if row is None:
        raise HTTPException(
            404, detail={"code": "not_found", "message": f"{model.__name__} not found"}
        )
    return row


def dump(row: Base, exclude: Collection[str] = ()) -> dict:
    def serialize(value: object) -> object:
        if isinstance(value, datetime) and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.isoformat() if hasattr(value, "isoformat") else value

    return {
        c.name: serialize(getattr(row, c.name))
        for c in row.__table__.columns
        if c.name not in exclude
    }


@router.get("/strategy-schema")
def strategy_schema() -> dict:
    return StrategyConfig.model_json_schema()


@router.post("/strategy-definitions/validate")
def validate_strategy(config: StrategyConfig) -> dict:
    return {
        "valid": True,
        "config": config.model_dump(mode="json"),
        "hash": canonical_hash(config.model_dump(mode="json")),
    }


@router.get("/strategies", response_model=list[StrategyOut])
def strategies(search: str = "", db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(
        select(Strategy)
        .where(Strategy.name.ilike(f"%{search[:160]}%"))
        .order_by(Strategy.created_at.desc())
        .limit(2000)
    )
    return [dump(s) for s in rows]


@router.post("/strategies", response_model=StrategyOut, status_code=201)
def create_strategy(body: StrategyCreate, db: Session = Depends(get_db)) -> dict:
    row = Strategy(
        name=body.name, description=body.description, draft=body.config.model_dump(mode="json")
    )
    db.add(row)
    db.commit()
    return dump(row)


@router.get("/strategies/{identifier}", response_model=StrategyOut)
def strategy(identifier: str, db: Session = Depends(get_db)) -> dict:
    return dump(get(db, Strategy, identifier))


@router.patch("/strategies/{identifier}", response_model=StrategyOut)
def edit_strategy(identifier: str, body: StrategyEdit, db: Session = Depends(get_db)) -> dict:
    source = get(db, Strategy, identifier)
    result = db.execute(
        update(Strategy)
        .where(Strategy.id == identifier, Strategy.draft_revision == body.expected_revision)
        .values(
            name=body.name,
            description=body.description,
            draft=body.config.model_dump(mode="json"),
            draft_revision=body.expected_revision + 1,
            llm_metadata={**source.llm_metadata, "manually_edited_after_acceptance": True}
            if source.llm_metadata
            else None,
        )
    )
    if result.rowcount != 1:
        raise HTTPException(409, "Draft changed; reload before saving")
    db.commit()
    return dump(db.get(Strategy, identifier, populate_existing=True))


@router.post("/strategies/{identifier}/archive")
def archive(identifier: str, db: Session = Depends(get_db)) -> dict:
    row = get(db, Strategy, identifier)
    row.archived = True
    db.commit()
    return dump(row)


@router.post("/strategies/{identifier}/restore")
def restore(identifier: str, db: Session = Depends(get_db)) -> dict:
    row = get(db, Strategy, identifier)
    row.archived = False
    db.commit()
    return dump(row)


@router.post("/strategies/{identifier}/clone", status_code=201)
def clone(identifier: str, db: Session = Depends(get_db)) -> dict:
    source = get(db, Strategy, identifier)
    row = Strategy(
        name=f"{source.name[:150]} copy",
        description=source.description,
        draft=source.draft,
        parent_version_id=source.parent_version_id,
    )
    db.add(row)
    db.commit()
    return dump(row)


@router.get("/strategies/{identifier}/versions", response_model=list[VersionOut])
def versions(identifier: str, db: Session = Depends(get_db)) -> list[dict]:
    get(db, Strategy, identifier)
    return [
        dump(v)
        for v in db.scalars(
            select(StrategyVersion)
            .where(StrategyVersion.strategy_id == identifier)
            .order_by(StrategyVersion.number.desc())
        )
    ]


@router.post("/strategies/{identifier}/publish", response_model=VersionOut, status_code=201)
def publish(identifier: str, body: Publish, db: Session = Depends(get_db)) -> dict:
    row = db.scalar(select(Strategy).where(Strategy.id == identifier).with_for_update())
    if not row:
        raise HTTPException(404, "Strategy not found")
    if row.archived or row.draft_revision != body.expected_revision:
        raise HTTPException(409, "Archived strategy or draft revision conflict")
    config = StrategyConfig.model_validate(row.draft).model_dump(mode="json")
    number = (
        db.scalar(
            select(func.max(StrategyVersion.number)).where(
                StrategyVersion.strategy_id == identifier
            )
        )
        or 0
    ) + 1
    version = StrategyVersion(
        strategy_id=identifier,
        number=number,
        config=config,
        config_hash=canonical_hash(config),
        schema_version=1,
        parent_version_id=row.parent_version_id,
        change_summary=body.change_summary,
        llm_metadata=row.llm_metadata,
    )
    db.add(version)
    db.flush()
    row.parent_version_id = version.id
    db.commit()
    return dump(version)


@router.get("/strategy-versions/{identifier}", response_model=VersionOut)
def version(identifier: str, db: Session = Depends(get_db)) -> dict:
    return dump(get(db, StrategyVersion, identifier))


@router.post("/strategy-versions/{identifier}/clone")
def from_version(identifier: str, db: Session = Depends(get_db)) -> dict:
    source = get(db, StrategyVersion, identifier)
    parent = get(db, Strategy, source.strategy_id)
    parent.draft = source.config
    parent.parent_version_id = source.id
    parent.draft_revision += 1
    parent.llm_metadata = source.llm_metadata
    db.commit()
    return dump(parent)


@router.get("/backtest-profiles", response_model=list[ProfileOut])
def profiles(db: Session = Depends(get_db)) -> list[dict]:
    return [dump(p) for p in db.scalars(select(Profile).order_by(Profile.created_at).limit(2000))]


@router.post("/backtest-profiles", response_model=ProfileOut, status_code=201)
def create_profile(body: ProfileWrite, db: Session = Depends(get_db)) -> dict:
    row = Profile(name=body.name, config=body.config.model_dump(mode="json"))
    db.add(row)
    db.commit()
    return dump(row)


@router.get("/backtest-profiles/defaults")
def profile_defaults() -> dict:
    return {"name": "US Equities Standard", "config": ProfileConfig().model_dump(mode="json")}


@router.get("/backtest-profiles/{identifier}", response_model=ProfileOut)
def profile(identifier: str, db: Session = Depends(get_db)) -> dict:
    return dump(get(db, Profile, identifier))


@router.patch("/backtest-profiles/{identifier}", response_model=ProfileOut)
def edit_profile(identifier: str, body: ProfileWrite, db: Session = Depends(get_db)) -> dict:
    row = get(db, Profile, identifier)
    row.name, row.config = body.name, body.config.model_dump(mode="json")
    db.commit()
    return dump(row)


@router.post("/backtest-profiles/{identifier}/clone", status_code=201)
def clone_profile(identifier: str, db: Session = Depends(get_db)) -> dict:
    source = get(db, Profile, identifier)
    return create_profile(ProfileWrite(name=f"{source.name[:150]} copy", config=source.config), db)


@router.get("/market-data/datasets", response_model=list[DatasetOut])
def datasets(db: Session = Depends(get_db)) -> list[dict]:
    return [
        dump(d) for d in db.scalars(select(Dataset).order_by(Dataset.created_at.desc()).limit(2000))
    ]


@router.get("/market-data/coverage")
def coverage(dataset_id: str, db: Session = Depends(get_db)) -> dict:
    return get(db, Dataset, dataset_id).metadata_json


@router.get("/market-data/symbols")
def symbols(dataset_id: str, db: Session = Depends(get_db)) -> list[str]:
    return sorted(get(db, Dataset, dataset_id).metadata_json["coverage"])


@router.post("/market-data/import", response_model=DatasetOut, status_code=201)
def ingest(body: DatasetInput, db: Session = Depends(get_db)) -> dict:
    return dump(import_dataset(db, body))


@router.post("/market-data/import-csv", response_model=DatasetOut, status_code=201)
def ingest_csv(body: CSVImport, db: Session = Depends(get_db)) -> dict:
    data = DatasetInput(
        **body.model_dump(exclude={"bars_csv", "fx_csv", "actions_csv"}),
        bars=csv_records(body.bars_csv),
        fx=csv_records(body.fx_csv) if body.fx_csv else [],
        actions=csv_records(body.actions_csv) if body.actions_csv else [],
    )
    return dump(import_dataset(db, data))


class ProviderImport(StrictModel):
    symbols: list[Symbol] = Field(min_length=1, max_length=20)
    start: date
    end: date
    feed: Literal["iex", "sip"] = "iex"
    fx: list[FXObservation] = Field(default_factory=list, max_length=30_000)
    fx_csv: str = Field(default="", max_length=3_000_000)
    actions_csv: str = Field(default="", max_length=1_000_000)
    corporate_actions_reviewed: bool = False
    dividends_complete: bool = False


@router.post("/market-data/alpaca", status_code=201)
def alpaca(body: ProviderImport, db: Session = Depends(get_db)) -> dict:
    if body.start > body.end or (body.end - body.start).days > 1827:
        raise ValueError("Alpaca import must span between 0 and 1827 days")
    data = AlpacaProvider().fetch(body.symbols, body.start, body.end, feed=body.feed)
    data.corporate_actions_reviewed = body.corporate_actions_reviewed
    data.dividends_complete = body.dividends_complete
    data.fx = (
        body.fx + [FXObservation.model_validate(r) for r in csv_records(body.fx_csv)]
        if body.fx_csv
        else body.fx
    )
    data.actions = (
        [Action.model_validate(r) for r in csv_records(body.actions_csv)]
        if body.actions_csv
        else []
    )
    return dump(import_dataset(db, data))


@router.post("/market-data/demo", status_code=201)
def demo(db: Session = Depends(get_db)) -> dict:
    from app.market_data.demo import synthetic_demo

    return dump(import_dataset(db, synthetic_demo()))


@router.get("/market-data/datasets/{identifier}/export")
def export_dataset(identifier: str, db: Session = Depends(get_db)) -> dict:
    return load_dataset(db, get(db, Dataset, identifier)).model_dump(mode="json")


@router.post("/backtests", response_model=list[RunOut], status_code=202)
def schedule(body: Schedule, db: Session = Depends(get_db)) -> list[dict]:
    profile = get(db, Profile, body.profile_id)
    dataset = get(db, Dataset, body.dataset_id)
    bindings, feature_data = resolve_features(db, body.context_snapshot_ids)
    source_bindings, source_data = resolve_inputs(db, body.strategy_input_ids)
    synthetic_inputs = (
        dataset.synthetic
        or any(source.synthetic for source in feature_data)
        or any(source.synthetic for source in source_data)
    )
    if synthetic_inputs and not body.acknowledge_synthetic:
        raise ValueError("Explicitly acknowledge synthetic demonstration data before running")
    if len(body.strategy_version_ids) != len(set(body.strategy_version_ids)):
        raise ValueError("duplicate strategy versions")
    config = ProfileConfig.model_validate(profile.config)
    data = load_dataset(db, dataset)
    from app.market_data.strategy_inputs import advanced

    # Serialize global queue admission, including requests using different profiles.
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(71899321)"))
    active = db.scalar(
        select(func.count())
        .select_from(BacktestRun)
        .where(BacktestRun.status.in_(["queued", "running"]))
    )
    if active + len(body.strategy_version_ids) > settings().max_active_jobs:
        raise HTTPException(429, "Active backtest queue capacity reached")
    experiment = Experiment(
        name=body.experiment_name or "Shared-profile comparison",
        profile_snapshot=config.model_dump(mode="json"),
        dataset_id=dataset.id,
    )
    db.add(experiment)
    db.flush()
    rows = []
    for identifier in body.strategy_version_ids:
        version = get(db, StrategyVersion, identifier)
        strategy_config = StrategyConfig.model_validate(version.config)
        if advanced(strategy_config, config):
            from app.backtesting.advanced_validation import validate_advanced

            validate_advanced(strategy_config, config, data, source_data, feature_data)
        else:
            validate_coverage(data, config)
            validate_features(strategy_config, FeatureBook(feature_data), data, config)
        provenance = {
            "engine_version": ENGINE_VERSION,
            "execution_model": "event-clock-next-strict-open-v1"
            if advanced(strategy_config, config)
            else "chronological-open-close-v2",
            "indicator_version": "streamed-decimal-wilder-macd-stoch-v1"
            if advanced(strategy_config, config)
            else "decimal-wilder-macd-stoch-v2",
            "strategy_hash": version.config_hash,
            "dataset_hash": dataset.content_hash,
            "profile_hash": canonical_hash(config.model_dump(mode="json")),
            "coverage": dataset.metadata_json,
            "synthetic": synthetic_inputs,
            "external_inputs": bindings,
            "external_input_hash": context_content_hash({"bindings": bindings}),
            "strategy_inputs": source_bindings,
            "strategy_input_hash": canonical_hash({"bindings": source_bindings}),
        }
        run = BacktestRun(
            strategy_version_id=identifier,
            profile_id=profile.id,
            dataset_id=dataset.id,
            experiment_id=experiment.id,
            profile_snapshot=config.model_dump(mode="json"),
            provenance=provenance,
        )
        db.add(run)
        rows.append(run)
    db.commit()
    return [dump(r, {"result", "worker_token", "heartbeat_at"}) for r in rows]


@router.get("/backtests", response_model=list[RunOut])
def backtests(db: Session = Depends(get_db)) -> list[dict]:
    return [
        dump(r, {"result", "worker_token", "heartbeat_at"})
        for r in db.scalars(select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(1000))
    ]


@router.get("/backtests/{identifier}", response_model=RunOut)
def backtest(identifier: str, db: Session = Depends(get_db)) -> dict:
    return dump(get(db, BacktestRun, identifier), {"result", "worker_token", "heartbeat_at"})


def completed(db, identifier) -> dict:
    run = get(db, BacktestRun, identifier)
    if run.status != "completed":
        raise HTTPException(409, f"Run is {run.status}, not completed")
    return run.result


@router.get("/backtests/{identifier}/results")
def results(identifier: str, db: Session = Depends(get_db)) -> dict:
    return completed(db, identifier)


@router.get("/backtests/{identifier}/trades")
def trades(
    identifier: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
) -> dict:
    return completed(db, identifier)["trades"][offset : offset + limit]


@router.get("/backtests/{identifier}/equity")
def equity(identifier: str, db: Session = Depends(get_db)) -> dict:
    return completed(db, identifier)["equity"]


@router.post("/backtests/{identifier}/cancel")
def cancel(identifier: str, db: Session = Depends(get_db)) -> dict:
    get(db, BacktestRun, identifier)
    db.execute(
        update(BacktestRun)
        .where(BacktestRun.id == identifier, BacktestRun.status == "queued")
        .values(status="cancelled", cancel_requested=True, completed_at=utcnow())
    )
    db.execute(
        update(BacktestRun)
        .where(BacktestRun.id == identifier, BacktestRun.status == "running")
        .values(cancel_requested=True)
    )
    db.commit()
    return {"id": identifier, "cancellation_requested": True}


@router.get("/experiments", response_model=list[ExperimentOut])
def experiments(db: Session = Depends(get_db)) -> list[dict]:
    return [
        dump(e)
        for e in db.scalars(select(Experiment).order_by(Experiment.created_at.desc()).limit(1000))
    ]


@router.post("/experiments", status_code=202)
def create_experiment(body: Schedule, db: Session = Depends(get_db)) -> list[dict]:
    return schedule(body, db)


@router.get("/experiments/{identifier}", response_model=ExperimentOut)
def experiment(identifier: str, db: Session = Depends(get_db)) -> dict:
    return dump(get(db, Experiment, identifier))


@router.get("/experiments/{identifier}/comparison")
def comparison(identifier: str, db: Session = Depends(get_db)) -> list[dict]:
    get(db, Experiment, identifier)
    return [
        {
            "run": dump(r, {"result", "worker_token", "heartbeat_at"}),
            "metrics": r.result["metrics"] if r.result else None,
            "equity": r.result["equity"] if r.result else [],
        }
        for r in db.scalars(select(BacktestRun).where(BacktestRun.experiment_id == identifier))
    ]
