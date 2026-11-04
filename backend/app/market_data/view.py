from datetime import datetime, timedelta
from decimal import Decimal

from app.market_data.calendar import session_times
from app.schemas.domain import Bar, FXObservation


class DataView:
    """A strategy receives only a materialized, permissible history, never the source dataset."""

    def __init__(self, bars: list[Bar], now: datetime):
        self.now = now
        self.__history = tuple(
            b
            for b in bars
            if max(b.available_at, b.source_timestamp, session_times(b.session_date)[1]) <= now
        )

    def history(self, symbol: str, through: datetime | None = None) -> tuple[Bar, ...]:
        if through is not None and through > self.now:
            raise ValueError("future observation requested")
        cutoff = through or self.now
        return tuple(
            sorted(
                (
                    b
                    for b in self.__history
                    if b.symbol == symbol
                    and max(b.available_at, b.source_timestamp, session_times(b.session_date)[1])
                    <= cutoff
                ),
                key=lambda b: b.session_date,
            )
        )


def fx_at(fx: list[FXObservation], now: datetime, max_age_days: int = 7) -> Decimal:
    eligible = [r for r in fx if r.observed_at <= now and r.available_at <= now]
    if not eligible:
        raise ValueError(f"no historically available USD/SGD FX at {now.isoformat()}")
    latest = max(eligible, key=lambda r: (r.observed_at, r.available_at))
    if now - latest.observed_at > timedelta(days=max_age_days):
        raise ValueError(f"stale historical USD/SGD FX at {now.isoformat()}")
    return latest.rate


def require_mature_labels(label_available_at: list[datetime], cutoff: datetime) -> None:
    """Boundary for future trainers; no model training implementation is included."""
    if any(t > cutoff for t in label_available_at):
        raise ValueError("training label has not matured at cutoff")
