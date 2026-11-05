from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

Json = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Strategy(Identity, Base):
    __tablename__ = "strategies"
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    archived: Mapped[bool] = mapped_column(default=False)
    draft: Mapped[dict] = mapped_column(Json)
    draft_revision: Mapped[int] = mapped_column(default=1)
    parent_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    llm_metadata: Mapped[dict | None] = mapped_column(Json, nullable=True)


class StrategyVersion(Identity, Base):
    __tablename__ = "strategy_versions"
    __table_args__ = (UniqueConstraint("strategy_id", "number"),)
    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategies.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    config: Mapped[dict] = mapped_column(Json)
    config_hash: Mapped[str] = mapped_column(String(64))
    schema_version: Mapped[int] = mapped_column(default=1)
    parent_version_id: Mapped[str | None] = mapped_column(ForeignKey("strategy_versions.id"))
    change_summary: Mapped[str] = mapped_column(Text, default="")
    llm_metadata: Mapped[dict | None] = mapped_column(Json, nullable=True)


class Profile(Identity, Base):
    __tablename__ = "backtest_profiles"
    name: Mapped[str] = mapped_column(String(160))
    config: Mapped[dict] = mapped_column(Json)


class Dataset(Identity, Base):
    __tablename__ = "market_datasets"
    name: Mapped[str] = mapped_column(String(160))
    provider: Mapped[str] = mapped_column(String(80))
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    synthetic: Mapped[bool] = mapped_column(default=False)
    metadata_json: Mapped[dict] = mapped_column(Json)


class Candle(Identity, Base):
    __tablename__ = "candles"
    __table_args__ = (UniqueConstraint("dataset_id", "symbol", "session_date"),)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("market_datasets.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    session_date: Mapped[datetime] = mapped_column(Date, index=True)
    payload: Mapped[dict] = mapped_column(Json)


class FXRate(Identity, Base):
    __tablename__ = "fx_rates"
    __table_args__ = (UniqueConstraint("dataset_id", "observed_at", "available_at"),)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("market_datasets.id"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[dict] = mapped_column(Json)


class CorporateAction(Identity, Base):
    __tablename__ = "corporate_actions"
    dataset_id: Mapped[str] = mapped_column(ForeignKey("market_datasets.id"), index=True)
    payload: Mapped[dict] = mapped_column(Json)


class Experiment(Identity, Base):
    __tablename__ = "experiment_groups"
    name: Mapped[str] = mapped_column(String(160))
    profile_snapshot: Mapped[dict] = mapped_column(Json)
    dataset_id: Mapped[str] = mapped_column(ForeignKey("market_datasets.id"))


class BacktestRun(Identity, Base):
    __tablename__ = "backtest_runs"
    strategy_version_id: Mapped[str] = mapped_column(ForeignKey("strategy_versions.id"))
    profile_id: Mapped[str] = mapped_column(ForeignKey("backtest_profiles.id"))
    dataset_id: Mapped[str] = mapped_column(ForeignKey("market_datasets.id"))
    experiment_id: Mapped[str | None] = mapped_column(ForeignKey("experiment_groups.id"))
    profile_snapshot: Mapped[dict] = mapped_column(Json)
    provenance: Mapped[dict] = mapped_column(Json)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    progress: Mapped[int] = mapped_column(default=0)
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    worker_token: Mapped[str | None] = mapped_column(String(36))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    result: Mapped[dict | None] = mapped_column(Json, deferred=True)


class LLMProposal(Identity, Base):
    __tablename__ = "llm_proposals"
    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategies.id"))
    source_revision: Mapped[int] = mapped_column()
    config: Mapped[dict] = mapped_column(Json)
    metadata_json: Mapped[dict] = mapped_column(Json)
    accepted: Mapped[bool] = mapped_column(default=False)


class ContextSnapshot(Identity, Base):
    """Research-only source history; never exposed to the strategy interpreter."""

    __tablename__ = "context_snapshots"
    series_id: Mapped[str] = mapped_column(String(32), index=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    payload: Mapped[dict] = mapped_column(Json)


class StrategyInputRevision(Identity, Base):
    __tablename__ = "strategy_input_revisions"
    kind: Mapped[str] = mapped_column(String(16), index=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    payload: Mapped[dict] = mapped_column(Json)
