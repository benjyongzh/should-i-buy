"""Bounded source retrieval; snapshots need explicit review before strategy use."""

import csv
import hashlib
import io
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

import httpx
from pydantic import AwareDatetime, Field, model_validator

from app.core.config import settings
from app.schemas.domain import StrictModel

SeriesID = Literal[
    "VIX",
    "DGS2",
    "DGS10",
    "DFF",
    "CPIAUCSL",
    "UNRATE",
    "DCOILWTICO",
    "DCOILBRENTEU",
    "DEXSIUS",
    "FEAR_GREED_US",
]
CATALOG = {
    "VIX": ("Cboe VIX close", "index points", "daily"),
    "DGS2": ("US 2-year Treasury yield", "percent", "daily"),
    "DGS10": ("US 10-year Treasury yield", "percent", "daily"),
    "DFF": ("Effective federal funds rate", "percent", "daily"),
    "CPIAUCSL": ("US CPI, seasonally adjusted", "index 1982–1984=100", "monthly"),
    "UNRATE": ("US unemployment rate", "percent", "monthly"),
    "DCOILWTICO": ("WTI crude oil spot price", "USD per barrel", "daily"),
    "DCOILBRENTEU": ("Brent crude oil spot price", "USD per barrel", "daily"),
    "DEXSIUS": ("USD/SGD published reference rate", "SGD per USD", "daily"),
    "FEAR_GREED_US": ("US equity Fear & Greed", "index 0–100", "daily"),
}
VIX_URL = "https://cdn-api.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"


class ContextFetch(StrictModel):
    series_id: SeriesID
    start: date = date(2018, 1, 1)
    end: date = date(2025, 12, 31)

    @model_validator(mode="after")
    def dates(self):
        if (
            self.start > self.end
            or self.start < date(1990, 1, 1)
            or self.end > datetime.now(UTC).date()
            or (self.end - self.start).days > 7305
        ):
            raise ValueError("Context date range must be historical, ordered and at most 20 years")
        return self


class ContextPoint(StrictModel):
    observation_date: date
    value: Decimal = Field(ge=-1_000_000_000, le=1_000_000_000)
    available_at: AwareDatetime | None = None
    release_date: date | None = None

    @model_validator(mode="after")
    def dates(self):
        if self.release_date is not None and self.release_date < self.observation_date:
            raise ValueError("Context release precedes observation")
        if self.available_at is not None and (
            self.release_date is None or self.available_at.date() < self.release_date
        ):
            raise ValueError("Context availability precedes release")
        return self


class ContextData(StrictModel):
    series_id: SeriesID
    name: str
    units: str
    frequency: str
    source: str
    source_url: str
    requested_start: date
    requested_end: date
    retrieved_at: AwareDatetime
    source_as_of: date | None = None
    vintage_windows: list[dict[str, str]] = Field(default_factory=list)
    availability_policy: str
    research_only: bool = True
    synthetic: bool = False
    source_snapshot_id: str | None = None
    source_snapshot_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    review_note: str | None = Field(default=None, min_length=20, max_length=2000)
    reviewed_at: AwareDatetime | None = None
    observations: list[ContextPoint] = Field(min_length=1, max_length=30000)
    missing_omitted: int = Field(ge=0)
    source_hashes: list[str]

    @model_validator(mode="after")
    def bounds(self):
        dates = [p.observation_date for p in self.observations]
        if len(dates) != len(set(dates)) or dates != sorted(dates):
            raise ValueError("Context observation dates must be unique and ordered")
        if any(not self.requested_start <= d <= self.requested_end for d in dates):
            raise ValueError("Context observation lies outside requested bounds")
        if self.series_id == "FEAR_GREED_US" and any(
            not 0 <= p.value <= 100 for p in self.observations
        ):
            raise ValueError("US Fear & Greed values must be between 0 and 100")
        if not self.research_only and (
            not self.source_snapshot_id
            or not self.source_snapshot_hash
            or not self.review_note
            or self.reviewed_at is None
        ):
            raise ValueError("Strategy input requires an explicit retained source review")
        return self


def request(client: httpx.Client, url: str, params: dict | None = None) -> httpx.Response:
    try:
        # Stream with a byte bound; never include query-string credentials in exceptions.
        with client.stream("GET", url, params=params) as response:
            if response.status_code != 200:
                raise ValueError(
                    f"Context provider returned HTTP {response.status_code}; check credentials/access"
                )
            chunks, size = [], 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > 10_000_000:
                    raise ValueError("Context provider response exceeds 10 MB")
                chunks.append(chunk)
            return httpx.Response(200, content=b"".join(chunks))
    except httpx.HTTPError:
        raise ValueError("Context provider connection failed; credentials suppressed") from None


def fetch_context(body: ContextFetch) -> ContextData:
    if body.series_id == "FEAR_GREED_US":
        raise ValueError(
            "No qualified automatic US Fear & Greed source is configured; import timestamped source CSV and review it"
        )
    points, hashes, missing = [], [], 0
    source_as_of = None
    windows = []
    with httpx.Client(timeout=60) as client:
        if body.series_id == "VIX":
            response = request(client, VIX_URL)
            hashes.append(hashlib.sha256(response.content).hexdigest())
            reader = csv.DictReader(io.StringIO(response.text.lstrip("\ufeff")))
            if not reader.fieldnames or not {"DATE", "CLOSE"} <= set(reader.fieldnames):
                raise ValueError("Cboe VIX CSV columns are unsupported")
            for row in reader:
                day = datetime.strptime(row["DATE"], "%m/%d/%Y").date()
                if body.start <= day <= body.end:
                    if Decimal(row["CLOSE"]) < 0:
                        raise ValueError("Cboe VIX level cannot be negative")
                    points.append(ContextPoint(observation_date=day, value=row["CLOSE"]))
            source, url = "Cboe latest historical CSV", VIX_URL
            policy = "Current revised history. Original publication timestamps/vintages unverified; availability is unknown (null). Retrospective context only; never a trading input."
        else:
            key = settings().fred_api_key.get_secret_value()
            if not key:
                raise ValueError("Set FRED_API_KEY on the server to retrieve macro context")
            source, url = (
                "ALFRED initial-release observations",
                "https://api.stlouisfed.org/fred/series/observations",
            )
            # FRED's "today" follows its US calendar, which can lag UTC's date.
            source_as_of = datetime.now(ZoneInfo("America/Chicago")).date()
            cursor = body.start
            while cursor <= source_as_of:
                finish = min(source_as_of, date(cursor.year + 3, 12, 31))
                windows.append({"realtime_start": str(cursor), "realtime_end": str(finish)})
                cursor = finish + timedelta(days=1)
            # Output type 4 includes only first releases in each vintage window, even
            # when observation dates are older. Nonoverlapping windows preserve late
            # first releases without exceeding FRED's 2,000-vintage JSON ceiling.
            for window in windows:
                offset = 0
                for _ in range(20):
                    response = request(
                        client,
                        url,
                        {
                            "api_key": key,
                            "series_id": body.series_id,
                            "file_type": "json",
                            "observation_start": str(body.start),
                            "observation_end": str(body.end),
                            **window,
                            "output_type": 4,
                            "limit": 10000,
                            "offset": offset,
                        },
                    )
                    hashes.append(hashlib.sha256(response.content).hexdigest())
                    payload = response.json()
                    if payload.get("output_type") != 4 or payload.get("offset") != offset:
                        raise ValueError("FRED returned unexpected vintage or pagination metadata")
                    rows = payload["observations"]
                    for row in rows:
                        if (
                            not window["realtime_start"]
                            <= row["realtime_start"]
                            <= window["realtime_end"]
                        ):
                            raise ValueError("FRED initial release lies outside its vintage window")
                        if row["value"] == ".":
                            missing += 1
                            continue
                        release = date.fromisoformat(row["realtime_start"])
                        points.append(
                            ContextPoint(
                                observation_date=row["date"],
                                value=row["value"],
                                release_date=release,
                                available_at=datetime.combine(
                                    release + timedelta(days=1),
                                    datetime.min.time(),
                                    ZoneInfo("America/New_York"),
                                ),
                            )
                        )
                        if len(points) > 30000:
                            raise ValueError("Context observation limit exceeded")
                    offset += len(rows)
                    if offset >= payload["count"]:
                        break
                    if not rows:
                        raise ValueError("FRED pagination ended before declared count")
                else:
                    raise ValueError("FRED context pagination limit exceeded")
            policy = "Initial-release values only, not all later revisions. Conservative midnight New York AFTER FRED release date; actual publication clock not certified. Observation dates are not release dates. Missing values omitted. Research context only; not supplied to strategies or FX accounting."
    name, units, frequency = CATALOG[body.series_id]
    return ContextData(
        series_id=body.series_id,
        name=name,
        units=units,
        frequency=frequency,
        source=source,
        source_url=url,
        requested_start=body.start,
        requested_end=body.end,
        retrieved_at=datetime.now(UTC),
        source_as_of=source_as_of,
        vintage_windows=windows,
        availability_policy=policy,
        observations=sorted(points, key=lambda p: p.observation_date),
        missing_omitted=missing,
        source_hashes=hashes,
    )
