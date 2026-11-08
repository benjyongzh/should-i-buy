from datetime import date, datetime, timedelta
from typing import Literal

from pydantic import AwareDatetime, Field, model_validator

from app.schemas.domain import Action, StrictModel, Symbol

Capability = Literal[
    "daily_accounting",
    "sec_filings",
    "intraday",
    "historical_sectors",
    "company_news",
    "analyst_ratings",
    "congress_trades",
]
SUPPORTED = {"daily_accounting", "sec_filings"}


class IntakeRequest(StrictModel):
    symbol: Symbol
    benchmark: Symbol = "SPY"
    start: date
    end: date
    warmup_days: int = Field(default=730, ge=0, le=1096)
    event_lookback_days: int = Field(default=1, ge=1, le=366)
    capabilities: list[Capability] = Field(
        default=["daily_accounting", "sec_filings"], min_length=1, max_length=7
    )
    account_currency: Literal["USD", "SGD"] = "SGD"
    max_fx_age_days: int = Field(default=14, ge=1, le=14)
    max_sec_documents: int = Field(default=100, ge=1, le=200)
    refresh: bool = False
    idempotency_key: str = Field(min_length=8, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")

    @model_validator(mode="after")
    def bounds(self):
        if self.start > self.end or self.start < date(1990, 1, 1):
            raise ValueError("request requires ordered historical dates from 1990 onward")
        if self.end >= datetime.now().date():
            raise ValueError("use completed historical dates before today")
        if (self.end - self.start).days + self.warmup_days > 5000:
            raise ValueError("intake including warm-up is limited to 5000 calendar days")
        if self.start - timedelta(days=self.warmup_days) < date(1990, 1, 1):
            raise ValueError("warm-up must remain within the supported historical calendar")
        if len(set(self.capabilities)) != len(self.capabilities):
            raise ValueError("duplicate requested capability")
        return self


class EvidenceUpload(StrictModel):
    symbol: Symbol
    source_url: str = Field(pattern=r"^https://", max_length=1000)
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=30, max_length=500_000)
    available_at: AwareDatetime
    clock_policy: str = Field(min_length=20, max_length=1000)


class ActionEvidence(StrictModel):
    action: Action
    artifact_id: str = Field(min_length=1, max_length=36)
    quote: str = Field(min_length=20, max_length=5000)


class IntakeReview(StrictModel):
    expected_report_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    approve_capabilities: list[Literal["daily_accounting", "sec_filings"]] = Field(
        min_length=1, max_length=2
    )
    acknowledge_policies: Literal[True]
    attest_historical_identity: Literal[True]
    attest_action_coverage: bool = False
    note: str = Field(min_length=30, max_length=2000)
    actions: list[ActionEvidence] = Field(default_factory=list, max_length=1000)

    @model_validator(mode="after")
    def unique(self):
        if len(set(self.approve_capabilities)) != len(self.approve_capabilities):
            raise ValueError("duplicate capability approval")
        return self
