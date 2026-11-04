from datetime import date, timedelta
from decimal import Decimal

from app.market_data.calendar import session_times, sessions
from app.schemas.domain import Bar, DatasetInput, FXObservation


def synthetic_demo() -> DatasetInput:
    """Explicit opt-in fixture. These prices do not represent SPY's historical performance."""
    bars, fx = [], []
    previous = Decimal(200)
    for index, day in enumerate(sessions(date(2018, 1, 1), date(2022, 12, 31))):
        triangle = abs(index % 120 - 60) - 30
        close = Decimal(200) + Decimal(index) / 25 + Decimal(triangle) + Decimal(index % 9) / 5
        opening = previous + Decimal(index % 5 - 2) / 10
        opened_at, closed_at = session_times(day)
        bars.append(
            Bar(
                symbol="SPY",
                session_date=day,
                open=opening,
                high=max(opening, close) + 1,
                low=min(opening, close) - 1,
                close=close,
                volume=1_000_000 + index % 31 * 10000,
                source_timestamp=closed_at,
                available_at=closed_at,
                quality=["SYNTHETIC_DEMONSTRATION"],
            )
        )
        fx.append(
            FXObservation(
                observed_at=opened_at - timedelta(hours=2),
                available_at=opened_at - timedelta(hours=1),
                rate=Decimal("1.30") + Decimal(index % 70) / 1000,
            )
        )
        previous = close
    return DatasetInput(
        name="SYNTHETIC · SPY & USD/SGD · 2018–2022",
        provider="synthetic-demo-v1",
        synthetic=True,
        bars=bars,
        fx=fx,
        availability_policy="Deterministic synthetic fixture. Not real market data. No investment-performance inference is valid.",
    )
