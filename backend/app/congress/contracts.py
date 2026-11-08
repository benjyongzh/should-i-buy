from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import AwareDatetime, Field, model_serializer, model_validator

from app.schemas.domain import StrictModel, Symbol

ID = r"^[A-Za-z0-9_-]{1,100}$"


class HouseDocument(StrictModel):
    year: int = Field(ge=2012, le=2035)
    document_id: str = Field(pattern=r"^[0-9]{7,8}$")
    archive_capture: str | None = Field(default=None, pattern=r"^[0-9]{14}$")


class HouseIndex(StrictModel):
    year: int = Field(ge=2012, le=2035)


class ReportReview(StrictModel):
    official_artifact_id: str
    replay_artifact_id: str | None = None
    disposition: Literal["selected_rows", "no_selected_symbols"]
    note: str = Field(min_length=20, max_length=2000)


class Observation(StrictModel):
    observation_id: str = Field(pattern=ID)
    canonical_transaction_id: str = Field(pattern=ID)
    official_artifact_id: str
    replay_artifact_id: str | None = None
    filing_date: date
    filing_kind: Literal["original", "amendment"]
    amends_observation_id: str | None = Field(default=None, pattern=ID)
    reporter: str = Field(min_length=2, max_length=160)
    owner: Literal["self", "spouse", "dependent", "joint", "unknown"]
    symbol: Symbol
    issuer_cik: str = Field(pattern=r"^[0-9]{10}$")
    identity_evidence_url: str = Field(pattern=r"^https://", max_length=1000)
    instrument: Literal["equity", "call_option", "put_option", "other", "unknown"]
    action: Literal[
        "purchase", "sale", "exchange", "option_exercise", "charitable_transfer", "unknown"
    ]
    reported_transaction_code: Literal["P", "S", "S (partial)", "E"]
    reported_asset_type: str = Field(min_length=1, max_length=20)
    transaction_date: date
    notification_date: date | None = None
    amount_min: Decimal | None = Field(default=None, ge=0, max_digits=24, decimal_places=8)
    amount_max: Decimal | None = Field(default=None, ge=0, max_digits=24, decimal_places=8)
    shares: Decimal | None = Field(default=None, gt=0, max_digits=24, decimal_places=8)
    option_contracts: Decimal | None = Field(default=None, gt=0, max_digits=24, decimal_places=8)
    strike_usd: Decimal | None = Field(default=None, gt=0, max_digits=24, decimal_places=8)
    row_reference: str = Field(min_length=1, max_length=160)
    row_transcript: str = Field(min_length=20, max_length=6000)
    reconciliation_note: str = Field(min_length=20, max_length=2000)

    @model_validator(mode="after")
    def dates_and_actions(self):
        if self.transaction_date > self.filing_date or (
            self.notification_date and self.notification_date > self.filing_date
        ):
            raise ValueError("transaction/notification date cannot follow filing date")
        if self.amount_max is not None and (
            self.amount_min is None or self.amount_max < self.amount_min
        ):
            raise ValueError("invalid disclosed amount range")
        if (self.filing_kind == "amendment") != bool(self.amends_observation_id):
            raise ValueError("an amendment must identify its retained predecessor")
        if self.action == "option_exercise" and self.instrument not in (
            "call_option",
            "put_option",
        ):
            raise ValueError("an option exercise must retain its option instrument")
        if (
            self.action in ("purchase", "sale", "exchange")
            and self.reported_transaction_code
            != {"purchase": "P", "sale": "S", "exchange": "E"}[self.action]
            and not (self.action == "sale" and self.reported_transaction_code == "S (partial)")
        ):
            raise ValueError("reported transaction code conflicts with classified action")
        return self


class LedgerRequest(StrictModel):
    name: str = Field(min_length=5, max_length=160)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    filing_start: date
    filing_end: date
    coverage_start: AwareDatetime
    coverage_end: AwareDatetime
    symbols: list[Symbol] = Field(min_length=1, max_length=20)
    stream_id: str = Field(pattern=r"^HOUSE_[A-Z0-9_]{1,25}$")
    index_artifact_id: str
    supporting_index_artifact_ids: list[str] = Field(default_factory=list, max_length=4)
    report_reviews: list[ReportReview] = Field(min_length=1, max_length=100)
    observations: list[Observation] = Field(default_factory=list, max_length=500)
    synthetic: bool = False

    @model_serializer(mode="wrap")
    def preserve_legacy_request(self, handler):
        payload = handler(self)
        if not payload.get("supporting_index_artifact_ids"):
            payload.pop("supporting_index_artifact_ids", None)
        return payload

    @model_validator(mode="after")
    def scope_bounds(self):
        if self.filing_start > self.filing_end or self.filing_start.year != self.filing_end.year:
            raise ValueError("one ledger covers an ordered filing domain within one calendar year")
        if (
            self.coverage_start >= self.coverage_end
            or (self.coverage_end - self.coverage_start).days > 366
        ):
            raise ValueError("declared observation coverage must be nonempty and at most366 days")
        if len(self.symbols) != len(set(self.symbols)):
            raise ValueError("duplicate scope symbol")
        if any(o.symbol not in self.symbols for o in self.observations):
            raise ValueError("observation symbol is outside the declared review scope")
        if self.filing_end > datetime.now().date():
            raise ValueError("filing domain must be historical")
        return self


class LedgerApproval(StrictModel):
    acknowledge_conservative_observation_clocks: Literal[True]
    attest_inventory_and_all_selected_rows: Literal[True]
    attest_identity_taxonomy_and_amendments: Literal[True]
    review_note: str = Field(min_length=40, max_length=2000)
