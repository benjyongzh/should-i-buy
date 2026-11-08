"""Immutable source contracts for historical intraday, security states and events."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, Field, model_serializer, model_validator

from app.market_data.calendar import session_times
from app.schemas.domain import Bar, StrictModel, Symbol


class IntradayBar(Bar):
    start_at: AwareDatetime
    end_at: AwareDatetime

    @model_validator(mode="after")
    def completed(self):
        opening, closing = session_times(self.session_date)
        if not opening <= self.start_at < self.end_at <= closing:
            raise ValueError("intraday interval must lie inside the regular exchange session")
        if not self.end_at <= self.source_timestamp <= self.available_at:
            raise ValueError(
                "intraday bar must be completed before source/publication availability"
            )
        return self


class SecurityState(StrictModel):
    symbol: Symbol
    instrument_id: str = Field(min_length=1, max_length=80)
    effective_at: AwareDatetime
    available_at: AwareDatetime
    listed: bool
    sector: str = Field(min_length=1, max_length=120)
    industry: str | None = Field(default=None, max_length=160)
    source_url: str = Field(pattern=r"^https?://", max_length=1000)


class HistoricalEvent(StrictModel):
    event_id: str = Field(min_length=1, max_length=160)
    published_at: AwareDatetime
    available_at: AwareDatetime
    category: str = Field(min_length=1, max_length=80)
    tags: list[str] = Field(default_factory=list, max_length=30)
    symbols: list[Symbol] = Field(default_factory=list, max_length=50)
    sectors: list[str] = Field(default_factory=list, max_length=30)
    score: Decimal | None = Field(default=None, ge=-1_000_000, le=1_000_000)
    score_available_at: AwareDatetime | None = None
    title: str = Field(min_length=1, max_length=1000)
    source_url: str = Field(pattern=r"^https?://", max_length=1000)
    original_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    derivation: str = Field(min_length=1, max_length=500)
    access: Literal["public", "subscription"] = "public"
    supersedes_event_id: str | None = Field(default=None, max_length=160)
    details: NewsDetails | AnalystDetails | CongressDetails | EconomicDetails | None = Field(
        default=None, discriminator="type"
    )

    @model_validator(mode="after")
    def clocks(self):
        if self.available_at < self.published_at:
            raise ValueError("event availability precedes original publication")
        if self.score is not None and (
            self.score_available_at is None or self.score_available_at < self.published_at
        ):
            raise ValueError("scores require their own publication/derivation availability")
        if isinstance(self.details, CongressDetails) and (
            self.published_at != self.details.public_at
            or self.available_at < self.details.public_at
        ):
            raise ValueError(
                "Congress events must use public disclosure availability, never transaction date"
            )
        if (
            isinstance(self.details, NewsDetails)
            and self.available_at < self.details.version_available_at
        ):
            raise ValueError(
                "current/revised article text cannot be backdated before its version became available"
            )
        if (
            isinstance(self.details, AnalystDetails)
            and self.available_at < self.details.report_available_at
        ):
            raise ValueError("analyst information cannot precede the rating/report publication")
        if isinstance(self.details, EconomicDetails) and (
            self.published_at != self.details.release_at
            or self.available_at < self.details.release_at
        ):
            raise ValueError("economic event must use the actual public release clock")
        return self


class NewsDetails(StrictModel):
    type: Literal["news"]
    article_id: str = Field(min_length=1, max_length=160)
    version_available_at: AwareDatetime
    text: str = Field(default="", max_length=30000)
    keyword_tags: dict[str, list[str]] = Field(default_factory=dict, max_length=30)


class AnalystDetails(StrictModel):
    type: Literal["analyst"]
    firm: str = Field(min_length=1, max_length=160)
    analyst: str | None = Field(default=None, max_length=160)
    action: Literal[
        "upgrade", "downgrade", "initiate", "reiterate", "resume", "suspend", "price_target"
    ]
    rating_before: str | None = Field(default=None, max_length=80)
    rating_after: str | None = Field(default=None, max_length=80)
    target_before: Decimal | None = Field(default=None, ge=0)
    target_after: Decimal | None = Field(default=None, ge=0)
    currency: Literal["USD"] = "USD"
    report_available_at: AwareDatetime


class CongressDetails(StrictModel):
    type: Literal["congress"]
    chamber: Literal["house", "senate"]
    filing_id: str = Field(min_length=1, max_length=160)
    reporter: str = Field(min_length=1, max_length=160)
    owner: Literal["self", "spouse", "dependent", "joint", "unknown"] = "unknown"
    transaction: Literal[
        "purchase", "sale", "exchange", "option_exercise", "charitable_transfer", "unknown"
    ]
    transaction_date: date
    filed_at: AwareDatetime | None = None
    public_at: AwareDatetime
    amount_min: Decimal = Field(ge=0)
    amount_max: Decimal | None = Field(default=None, ge=0)

    instrument: Literal["equity", "call_option", "put_option", "other", "unknown"] | None = None
    canonical_transaction_id: str | None = Field(default=None, min_length=1, max_length=100)
    observation_id: str | None = Field(default=None, min_length=1, max_length=100)
    reported_transaction_code: Literal["P", "S", "S (partial)", "E"] | None = None

    @model_serializer(mode="wrap")
    def preserve_legacy_payload(self, handler):
        payload = handler(self)
        for key in (
            "instrument",
            "canonical_transaction_id",
            "observation_id",
            "reported_transaction_code",
        ):
            if payload.get(key) is None:
                payload.pop(key, None)
        return payload

    @model_validator(mode="after")
    def ranges(self):
        metadata = (
            self.instrument,
            self.canonical_transaction_id,
            self.observation_id,
            self.reported_transaction_code,
        )
        if any(value is not None for value in metadata) or self.transaction in (
            "option_exercise",
            "charitable_transfer",
            "unknown",
        ):
            if not all(value is not None for value in metadata):
                raise ValueError(
                    "canonical Congress details require instrument, identity and reported-code provenance"
                )
            if self.transaction == "option_exercise" and self.instrument not in (
                "call_option",
                "put_option",
            ):
                raise ValueError(
                    "option exercise cannot be represented as an ordinary equity instrument"
                )
        if self.amount_max is not None and self.amount_max < self.amount_min:
            raise ValueError("invalid disclosed amount range")
        from zoneinfo import ZoneInfo

        if self.transaction_date > self.public_at.astimezone(
            ZoneInfo("America/New_York")
        ).date() or (self.filed_at is not None and self.filed_at > self.public_at):
            raise ValueError("disclosure chronology is inconsistent")
        return self


class EconomicDetails(StrictModel):
    type: Literal["economic"]
    release_at: AwareDatetime
    reference_period: str = Field(min_length=1, max_length=80)
    units: str = Field(min_length=1, max_length=80)
    actual: Decimal = Field(ge=-1_000_000_000, le=1_000_000_000)
    consensus: Decimal | None = Field(default=None, ge=-1_000_000_000, le=1_000_000_000)
    consensus_available_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def consensus_clock(self):
        if self.consensus is not None and (
            self.consensus_available_at is None or self.consensus_available_at > self.release_at
        ):
            raise ValueError("surprise requires a contemporaneous pre-release consensus")
        return self


HistoricalEvent.model_rebuild()


class StrategyInput(StrictModel):
    kind: Literal["intraday", "universe", "events"]
    name: str = Field(min_length=1, max_length=160)
    source: str = Field(min_length=1, max_length=160)
    source_url: str = Field(pattern=r"^https?://", max_length=1000)
    availability_policy: str = Field(min_length=20, max_length=2000)
    synthetic: bool = False
    coverage_start: AwareDatetime
    coverage_end: AwareDatetime
    symbols: list[Symbol] = Field(default_factory=list, max_length=100)
    complete: bool = False
    reviewed: bool = False
    review_note: str = Field(default="", max_length=2000)
    parent_id: str | None = None
    parent_hash: str | None = None
    bar_minutes: Literal[1, 5, 15, 30, 60] | None = None
    stream_id: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]{0,31}$")
    access_coverage: Literal["public_only", "any_licensed"] = "public_only"
    bars: list[IntradayBar] = Field(default_factory=list, max_length=100_000)
    states: list[SecurityState] = Field(default_factory=list, max_length=100_000)
    events: list[HistoricalEvent] = Field(default_factory=list, max_length=100_000)
    source_hashes: list[str] = Field(default_factory=list, max_length=1000)
    category_catalog: list[str] = Field(default_factory=list, max_length=1000)

    @model_validator(mode="after")
    def contents(self):
        if self.coverage_start >= self.coverage_end:
            raise ValueError("source coverage must be a nonempty time interval")
        if len(self.symbols) != len(set(self.symbols)):
            raise ValueError("duplicate declared coverage symbol")
        if self.kind == "intraday":
            if (
                self.bar_minutes is None
                or not self.bars
                or self.states
                or self.events
                or self.stream_id
            ):
                raise ValueError("intraday inputs require only bars and a bar_minutes resolution")
            keys = [(b.symbol, b.start_at) for b in self.bars]
            if len(keys) != len(set(keys)):
                raise ValueError("duplicate intraday interval")
            for bar in self.bars:
                opening, closing = session_times(bar.session_date)
                offset = (bar.start_at - opening).total_seconds()
                duration = (bar.end_at - bar.start_at).total_seconds()
                if offset % (60 * self.bar_minutes) or duration != min(
                    60 * self.bar_minutes, (closing - bar.start_at).total_seconds()
                ):
                    raise ValueError("intraday bars must follow exchange-open-aligned intervals")
                if not self.coverage_start <= bar.start_at < bar.end_at <= self.coverage_end:
                    raise ValueError("intraday bar lies outside declared coverage")
        elif self.kind == "universe":
            if not self.states or self.bars or self.events or self.stream_id or self.bar_minutes:
                raise ValueError("universe inputs require only historical security states")
            keys = [(s.symbol, s.effective_at, s.available_at) for s in self.states]
            if len(keys) != len(set(keys)):
                raise ValueError("duplicate historical security state")
        else:
            if not self.stream_id or self.bars or self.states or self.bar_minutes:
                raise ValueError("event inputs require a stream_id and only event records")
            if len({e.event_id for e in self.events}) != len(self.events):
                raise ValueError("duplicate event identity")
            if any(
                not self.coverage_start <= e.published_at <= self.coverage_end for e in self.events
            ):
                raise ValueError("event publication lies outside declared coverage")
            known = {e.category for e in self.events} | {tag for e in self.events for tag in e.tags}
            if self.category_catalog and not known.issubset(self.category_catalog):
                raise ValueError("event category/tag is outside the source's declared catalog")
            if not self.category_catalog:
                self.category_catalog = sorted(known)
        records = (
            self.bars if self.kind == "intraday" else self.states if self.kind == "universe" else []
        )
        if any(row.symbol not in self.symbols for row in records):
            raise ValueError("records must belong to declared coverage symbols")
        if self.reviewed and (
            not self.complete
            or not self.parent_id
            or not self.parent_hash
            or len(self.review_note) < 20
        ):
            raise ValueError(
                "review requires complete coverage, source lineage and an explicit note"
            )
        return self


def advanced(config, profile) -> bool:
    if (
        profile.timeframe != "1d"
        or config.execution_policy
        or config.universe
        or config.sizing_rules
    ):
        return True

    def visit(value):
        if isinstance(value, dict):
            return value.get("type") in {
                "market",
                "event",
                "corporate_action",
                "portfolio",
                "arithmetic",
                "calendar",
            } or any(visit(v) for v in value.values())
        return isinstance(value, list) and any(visit(v) for v in value)

    return visit(config.model_dump(mode="json"))
