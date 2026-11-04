from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


Money = Annotated[Decimal, Field(ge=0, max_digits=24, decimal_places=10)]
Positive = Annotated[Decimal, Field(gt=0, max_digits=24, decimal_places=10)]
Fraction = Annotated[Decimal, Field(ge=0, le=1)]
Symbol = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9.\-]{0,15}$")]


class Constant(StrictModel):
    type: Literal["constant"]
    value: Decimal = Field(ge=-1_000_000_000, le=1_000_000_000)


class Price(StrictModel):
    type: Literal["price"]
    field: Literal["open", "high", "low", "close", "volume"] = "close"


class Indicator(StrictModel):
    type: Literal["indicator"]
    name: Literal["sma", "ema", "rsi", "momentum", "avg_volume", "rolling_high", "rolling_low"]
    period: int = Field(ge=2, le=500)
    field: Literal["open", "high", "low", "close", "volume"] = "close"


class Multiply(StrictModel):
    type: Literal["multiply"]
    left: Numeric
    right: Numeric


Numeric = Annotated[Constant | Price | Indicator | Multiply, Field(discriminator="type")]


class Compare(StrictModel):
    type: Literal["compare"]
    op: Literal["gt", "lt", "gte", "lte", "eq", "crosses_above", "crosses_below"]
    left: Numeric
    right: Numeric


class Group(StrictModel):
    type: Literal["all", "any"]
    conditions: list[Condition] = Field(min_length=1, max_length=10)


class Negate(StrictModel):
    type: Literal["not"]
    condition: Condition


class Always(StrictModel):
    type: Literal["always"]
    value: bool


Condition = Annotated[Compare | Group | Negate | Always, Field(discriminator="type")]
for _model in (Multiply, Group, Negate):
    _model.model_rebuild()


class Sizing(StrictModel):
    mode: Literal["equity_percent", "fixed_notional"] = "equity_percent"
    value: Positive = Decimal("0.1")

    @model_validator(mode="after")
    def percentage(self):
        if self.mode == "equity_percent" and self.value > 1:
            raise ValueError("equity_percent value must be <= 1")
        return self


class Risk(StrictModel):
    max_allocation: Fraction = Decimal("1")
    max_positions: int = Field(default=5, ge=1, le=100)
    stop_loss: Fraction | None = None
    take_profit: Fraction | None = None


class StrategyConfig(StrictModel):
    schema_version: Literal[1] = 1
    entry: Condition
    exit: Condition
    sizing: Sizing = Field(default_factory=Sizing)
    risk: Risk = Field(default_factory=Risk)

    @model_validator(mode="before")
    @classmethod
    def bounded_tree(cls, data):
        if isinstance(data, dict):
            count = 0
            stack = [(data, 0)]
            while stack:
                node, depth = stack.pop()
                count += 1
                if count > 500 or depth > 20:
                    raise ValueError("strategy exceeds 500 nodes or depth 20")
                if isinstance(node, dict):
                    stack.extend((v, depth + 1) for v in node.values())
                elif isinstance(node, list):
                    stack.extend((v, depth + 1) for v in node)
        return data


class ProfileConfig(StrictModel):
    starting_capital: Positive = Decimal("10000")
    account_currency: Literal["SGD", "USD"] = "SGD"
    start_date: date = date(2019, 1, 1)
    end_date: date = date(2022, 12, 31)
    symbols: list[Symbol] = Field(default=["SPY"], min_length=1, max_length=50)
    benchmark: Symbol = "SPY"
    calendar: Literal["XNYS"] = "XNYS"
    timeframe: Literal["1d"] = "1d"
    execution: Literal["next_open"] = "next_open"
    fx_policy: Literal["latest_available"] = "latest_available"
    max_fx_age_days: int = Field(default=7, ge=1, le=14)
    fixed_fee: Money = Decimal("2.50")
    commission_pct: Fraction = Decimal("0")
    slippage: Fraction = Decimal("0.0005")
    spread: Fraction = Decimal("0")
    fx_markup: Fraction = Decimal("0")
    fractional_shares: bool = False
    max_orders_per_day: int = Field(default=10, ge=1, le=1000)
    max_exposure: Fraction = Decimal("1")
    min_notional: Money = Decimal("1")
    min_holding_sessions: int = Field(default=0, ge=0, le=1000)
    max_positions: int = Field(default=5, ge=1, le=100)
    risk_free_rate: Fraction = Decimal("0")
    research_label: Literal["in_sample", "holdout"] = "in_sample"

    @model_validator(mode="after")
    def dates(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date must be <= end_date")
        if self.start_date < date(1990, 1, 1) or self.end_date > date(2035, 12, 31):
            raise ValueError("supported calendar range is 1990–2035")
        if (self.end_date - self.start_date).days > 7305:
            raise ValueError("a run may span at most 20 years")
        if len(self.symbols) != len(set(self.symbols)):
            raise ValueError("symbols must be unique")
        if self.slippage + self.spread / 2 >= 1:
            raise ValueError("execution costs must leave a positive sell price")
        return self


class Bar(StrictModel):
    symbol: Symbol
    session_date: date
    open: Positive
    high: Positive
    low: Positive
    close: Positive
    volume: Money
    available_at: AwareDatetime
    source_timestamp: AwareDatetime
    exchange: Literal["XNYS", "XNAS"] = "XNYS"
    currency: Literal["USD"] = "USD"
    quality: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def ohlc(self):
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise ValueError("OHLC values are outside high/low bounds")
        if self.low > self.high:
            raise ValueError("high must be >= low")
        return self


class FXObservation(StrictModel):
    pair: Literal["USD/SGD"] = "USD/SGD"
    observed_at: AwareDatetime
    available_at: AwareDatetime
    rate: Positive

    @model_validator(mode="after")
    def availability(self):
        if self.available_at < self.observed_at:
            raise ValueError("FX availability must not precede observation")
        return self


class Action(StrictModel):
    symbol: Symbol
    session_date: date
    available_at: AwareDatetime
    kind: Literal["split", "dividend"]
    value: Positive
    payment_date: date | None = None

    @model_validator(mode="after")
    def dividend_payment(self):
        if self.kind == "dividend" and (
            self.payment_date is None or self.payment_date < self.session_date
        ):
            raise ValueError("dividends require payment_date on or after the ex-date session_date")
        if self.kind == "split" and self.payment_date is not None:
            raise ValueError("splits do not have a payment_date")
        return self


class DatasetInput(StrictModel):
    name: str = Field(min_length=1, max_length=160)
    provider: str = Field(default="csv", min_length=1, max_length=80)
    synthetic: bool = False
    adjustment_policy: Literal["raw"] = "raw"
    dividends_complete: bool = False
    corporate_actions_reviewed: bool = False
    availability_policy: str = Field(default="source supplied timestamps", max_length=500)
    decision_time: Literal["close_plus_30m", "20:30_America/New_York"] = "close_plus_30m"
    bars: list[Bar] = Field(min_length=1, max_length=100_000)
    fx: list[FXObservation] = Field(default_factory=list, max_length=30_000)
    actions: list[Action] = Field(default_factory=list, max_length=10_000)


def canonical_hash(value: dict) -> str:
    import hashlib

    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def default_strategy() -> StrategyConfig:
    return StrategyConfig(
        entry=Always(type="always", value=True), exit=Always(type="always", value=False)
    )


class OrderRecord(StrictModel):
    id: int
    symbol: str
    side: Literal["buy", "sell"]
    type: Literal["market", "stop_loss", "take_profit"] = "market"
    submitted_at: datetime
    eligible_after: datetime
    quantity: Decimal | None = None
    status: Literal["pending", "filled", "rejected", "cancelled"] = "pending"
    executed_at: datetime | None = None
    execution_price: Decimal | None = None
    fees: Decimal = Decimal(0)
    reason: str
    rejection_reason: str | None = None
