"""Frozen, publication-gated external values. The interpreter receives no source history."""

from bisect import bisect_right
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, Field, model_validator

from app.market_data.calendar import decision_timestamp, sessions
from app.schemas.domain import DatasetInput, ProfileConfig, StrategyConfig, StrictModel

NY = ZoneInfo("America/New_York")


class FeaturePoint(StrictModel):
    observation_date: date
    available_at: AwareDatetime
    value: Decimal = Field(ge=-1_000_000_000, le=1_000_000_000)

    @model_validator(mode="after")
    def chronology(self):
        if self.available_at.astimezone(NY).date() < self.observation_date:
            raise ValueError("External value availability precedes its observation date")
        return self


class FeatureSeries(StrictModel):
    series_id: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,31}$")
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    synthetic: bool = False
    points: list[FeaturePoint] = Field(min_length=1, max_length=30000)

    @model_validator(mode="after")
    def unique_dates(self):
        dates = [p.observation_date for p in self.points]
        if len(dates) != len(set(dates)):
            raise ValueError("Duplicate external observation date")
        return self


class FeatureBook:
    def __init__(self, series: list[FeatureSeries]):
        if len(series) > 20 or sum(len(s.points) for s in series) > 100000:
            raise ValueError("External input limit exceeded")
        if len({s.series_id for s in series}) != len(series):
            raise ValueError("Choose only one snapshot per external series")
        self.__indices = {}
        for source in series:
            source = FeatureSeries.model_validate(source.model_dump())
            # Prefix maxima handle late publications of older observations without
            # replacing a newer observation which was already publicly available.
            rows = sorted(
                ((p.observation_date, p.available_at, p.value) for p in source.points),
                key=lambda p: (p[1], p[0]),
            )
            clocks, best = [], []
            for point in rows:
                clocks.append(point[1])
                best.append(max(best[-1], point, key=lambda p: (p[0], p[1])) if best else point)
            self.__indices[source.series_id] = (tuple(clocks), tuple(best))

    def materialize(self, now: datetime, previous: datetime) -> "FeatureView":
        if previous > now:
            raise ValueError("Future external cutoff requested")
        current, prior = {}, {}
        for series_id, (clocks, rows) in self.__indices.items():
            for clock, target in ((now, current), (previous, prior)):
                index = bisect_right(clocks, clock) - 1
                target[series_id] = rows[index] if index >= 0 else None
        return FeatureView(now, previous, current, prior)


class FeatureView:
    def __init__(self, now, previous, current, prior):
        self.__clocks = (now, previous)
        # Immutable scalar tuples; no reference to the source book or future rows.
        self.__points = (current, prior)

    def cutoff(self, offset: int = 0) -> datetime:
        if offset not in (0, 1):
            raise ValueError("Unsupported external history offset")
        return self.__clocks[offset]

    def value(self, series_id: str, max_age_days: int, offset: int = 0) -> Decimal:
        if offset not in (0, 1):
            raise ValueError("Unsupported external history offset")
        point = self.__points[offset].get(series_id)
        clock = self.__clocks[offset]
        if point is None:
            raise ValueError(f"No published external value for {series_id} at {clock.isoformat()}")
        observed, available, value = point
        if available > clock or observed > clock.astimezone(NY).date():
            raise ValueError("Future external observation blocked")
        if clock - datetime.combine(observed, time.min, NY) > timedelta(days=max_age_days):
            raise ValueError(f"Stale external value for {series_id} at {clock.isoformat()}")
        return value

    def audit(self, names: set[str]) -> dict:
        def dump(point):
            return (
                {
                    "observation_date": str(point[0]),
                    "available_at": point[1].isoformat(),
                    "value": str(point[2]),
                }
                if point
                else None
            )

        return {
            name: {
                "current": dump(self.__points[0].get(name)),
                "previous": dump(self.__points[1].get(name)),
            }
            for name in sorted(names)
        }


def requirements(config: StrategyConfig) -> set[tuple[str, int, bool]]:
    output = set()

    def visit(node, previous=False):
        if isinstance(node, dict):
            previous = previous or node.get("op") in ("crosses_above", "crosses_below")
            if node.get("type") == "external":
                output.add((node["series_id"], node["max_age_days"], previous))
            for value in node.values():
                visit(value, previous)
        elif isinstance(node, list):
            for value in node:
                visit(value, previous)

    visit(config.model_dump(mode="json"))
    return output


@lru_cache(maxsize=20000)
def decision_pair(day: date, policy: str) -> tuple[datetime, datetime]:
    previous_day = sessions(day - timedelta(days=14), day - timedelta(days=1))[-1]
    return decision_timestamp(day, policy), decision_timestamp(previous_day, policy)


def validate_features(
    config: StrategyConfig, book: FeatureBook, data: DatasetInput, profile: ProfileConfig
) -> None:
    needed = requirements(config)
    if not needed:
        return
    for day in sessions(profile.start_date, profile.end_date):
        view = book.materialize(*decision_pair(day, data.decision_time))
        for name, age, previous in needed:
            view.value(name, age)
            if previous:
                view.value(name, age, 1)
