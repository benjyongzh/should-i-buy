from typing import Any, Literal

from pydantic import Field

from app.schemas.domain import ProfileConfig, StrategyConfig, StrictModel


class StrategyCreate(StrictModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=5000)
    config: StrategyConfig


class StrategyEdit(StrictModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=5000)
    config: StrategyConfig
    expected_revision: int = Field(ge=1)


class Publish(StrictModel):
    expected_revision: int = Field(ge=1)
    change_summary: str = Field(default="", max_length=2000)


class ProfileWrite(StrictModel):
    name: str = Field(min_length=1, max_length=160)
    config: ProfileConfig


class Schedule(StrictModel):
    strategy_version_ids: list[str] = Field(min_length=1, max_length=20)
    profile_id: str
    dataset_id: str
    experiment_name: str = Field(default="", max_length=160)
    acknowledge_synthetic: bool = False


class CSVImport(StrictModel):
    name: str = Field(min_length=1, max_length=160)
    provider: str = Field(default="csv", max_length=80)
    synthetic: bool = False
    bars_csv: str = Field(min_length=1, max_length=20_000_000)
    fx_csv: str = Field(default="", max_length=3_000_000)
    actions_csv: str = Field(default="", max_length=1_000_000)
    dividends_complete: bool = False
    corporate_actions_reviewed: bool = False
    availability_policy: str = Field(default="source supplied timestamps", max_length=500)
    decision_time: Literal["close_plus_30m", "20:30_America/New_York"] = "close_plus_30m"


class RowOut(StrictModel):
    """Typed resource envelope with domain-specific fields retained in OpenAPI."""

    id: str
    created_at: str


class StrategyOut(RowOut):
    name: str
    description: str
    archived: bool
    draft: StrategyConfig
    draft_revision: int
    parent_version_id: str | None
    llm_metadata: dict | None


class ProfileOut(RowOut):
    name: str
    config: ProfileConfig


class RunOut(RowOut):
    strategy_version_id: str
    profile_id: str
    dataset_id: str
    experiment_id: str | None
    profile_snapshot: ProfileConfig
    provenance: dict[str, Any]
    status: str
    progress: int
    cancel_requested: bool
    started_at: str | None
    completed_at: str | None
    error: str | None


class VersionOut(RowOut):
    strategy_id: str
    number: int
    config: StrategyConfig
    config_hash: str
    schema_version: int
    parent_version_id: str | None
    change_summary: str
    llm_metadata: dict | None


class DatasetOut(RowOut):
    name: str
    provider: str
    content_hash: str
    synthetic: bool
    metadata_json: dict[str, Any]


class ExperimentOut(RowOut):
    name: str
    profile_snapshot: ProfileConfig
    dataset_id: str
