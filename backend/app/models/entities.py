from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    event,
    text,
)
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


class StrategyChatTurn(Identity, Base):
    __tablename__ = "strategy_chat_turns"
    __table_args__ = (
        UniqueConstraint("strategy_id", "request_id"),
        Index("ix_chat_sequence", "strategy_id", "sequence", unique=True),
        Index(
            "ix_chat_one_stream",
            "strategy_id",
            unique=True,
            sqlite_where=text("status = 'streaming'"),
            postgresql_where=text("status = 'streaming'"),
        ),
    )
    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategies.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=1)
    request_id: Mapped[str] = mapped_column(String(80))
    source_revision: Mapped[int] = mapped_column()
    user_text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="streaming")
    context_json: Mapped[dict] = mapped_column(Json)
    reply_json: Mapped[dict | None] = mapped_column(Json, nullable=True)
    partial_text: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str | None] = mapped_column(Text)
    proposal_id: Mapped[str | None] = mapped_column(ForeignKey("llm_proposals.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StrategyConversation(Base):
    """Exactly one stable conversation resource for each strategy, including clones."""

    __tablename__ = "strategy_conversations"
    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategies.id"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class VersionConversation(Base):
    """Immutable publication-time transcript, separate from immutable version rows."""

    __tablename__ = "version_conversations"
    version_id: Mapped[str] = mapped_column(ForeignKey("strategy_versions.id"), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(
        ForeignKey("strategy_conversations.strategy_id"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    content_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(Json, deferred=True)


@event.listens_for(Strategy, "after_insert")
def create_strategy_conversation(mapper, connection, target):
    connection.execute(
        StrategyConversation.__table__.insert().values(
            strategy_id=target.id, created_at=target.created_at
        )
    )


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


class CompanyIntake(Identity, Base):
    __tablename__ = "company_intakes"
    idempotency_key: Mapped[str] = mapped_column(String(80), unique=True)
    request_hash: Mapped[str] = mapped_column(String(64), index=True)
    request_payload: Mapped[dict] = mapped_column(Json)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    progress: Mapped[int] = mapped_column(default=0)
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    worker_token: Mapped[str | None] = mapped_column(String(36))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)


class SourceArtifact(Identity, Base):
    __tablename__ = "source_artifacts"
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    source_url: Mapped[str] = mapped_column(String(1000))
    kind: Mapped[str] = mapped_column(String(32))
    metadata_json: Mapped[dict] = mapped_column(Json)
    body: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)


class IntakeArtifact(Base):
    __tablename__ = "intake_artifacts"
    intake_id: Mapped[str] = mapped_column(ForeignKey("company_intakes.id"), primary_key=True)
    artifact_id: Mapped[str] = mapped_column(ForeignKey("source_artifacts.id"), primary_key=True)


class IntakeReport(Identity, Base):
    __tablename__ = "intake_reports"
    intake_id: Mapped[str] = mapped_column(ForeignKey("company_intakes.id"), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    payload: Mapped[dict] = mapped_column(Json)


class CompanyPackage(Identity, Base):
    __tablename__ = "company_packages"
    intake_id: Mapped[str] = mapped_column(ForeignKey("company_intakes.id"), index=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("intake_reports.id"))
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    payload: Mapped[dict] = mapped_column(Json)


class ResearchStudy(Identity, Base):
    """Immutable research plan, independent of the simulation engine."""

    __tablename__ = "research_studies"
    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategies.id"), index=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("research_studies.id"))
    request_id: Mapped[str] = mapped_column(String(80), unique=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    content_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(Json)


class ResearchEvent(Identity, Base):
    """Append-only attempts and conclusions; failed runs remain in the record."""

    __tablename__ = "research_events"
    __table_args__ = (UniqueConstraint("study_id", "slot"),)
    study_id: Mapped[str] = mapped_column(ForeignKey("research_studies.id"), index=True)
    slot: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(20))
    content_hash: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(Json)


class CongressCollection(Identity, Base):
    __tablename__ = "congress_collections"
    request_id: Mapped[str] = mapped_column(String(80), unique=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    request_payload: Mapped[dict] = mapped_column(Json)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    phase: Mapped[str] = mapped_column(String(24), default="inventory")
    state: Mapped[dict] = mapped_column(Json, default=dict)
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    worker_token: Mapped[str | None] = mapped_column(String(36))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)


class CongressCollectionItem(Identity, Base):
    __tablename__ = "congress_collection_items"
    __table_args__ = (UniqueConstraint("collection_id", "chamber", "year", "report_key"),)
    collection_id: Mapped[str] = mapped_column(ForeignKey("congress_collections.id"), index=True)
    chamber: Mapped[str] = mapped_column(String(8))
    year: Mapped[int] = mapped_column(Integer)
    report_key: Mapped[str] = mapped_column(String(100))
    request_hash: Mapped[str] = mapped_column(String(64))
    request_payload: Mapped[dict] = mapped_column(Json)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    clock_status: Mapped[str] = mapped_column(String(24), default="unknown")
    official_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("source_artifacts.id"))
    replay_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("source_artifacts.id"))
    text_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("source_artifacts.id"))
    error: Mapped[str | None] = mapped_column(Text)
