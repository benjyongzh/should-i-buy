from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.session import Base, get_db, make_engine
from app.main import app
from app.market_data.calendar import session_times, sessions
from app.schemas.domain import Bar, DatasetInput, FXObservation


@pytest.fixture(autouse=True)
def isolate_external_providers(monkeypatch):
    """Developer credentials must never enable live providers during automated tests."""
    for variable in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY", "LLM_API_KEY", "LLM_MODEL"):
        monkeypatch.setenv(variable, "")
    settings.cache_clear()

    def blocked_request(*args, **kwargs):
        raise AssertionError("Unmocked outbound HTTP is disabled in tests; use MockTransport")

    async def blocked_async_request(*args, **kwargs):
        blocked_request()

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", blocked_request)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", blocked_async_request)
    yield
    settings.cache_clear()


def fixture_data(start=date(2020, 1, 2), end=date(2020, 6, 30), prices=None):
    bars, fx = [], []
    days = sessions(start, end)
    for index, day in enumerate(days):
        opening, close = session_times(day)
        value = (
            Decimal(str(prices[index])) if prices else Decimal(100 + (index % 30) - (index % 11))
        )
        bars.append(
            Bar(
                symbol="SPY",
                session_date=day,
                open=value,
                high=value + 2,
                low=value - 2,
                close=value,
                volume=10000,
                source_timestamp=close,
                available_at=close,
            )
        )
        fx.append(
            FXObservation(
                observed_at=opening - timedelta(hours=1),
                available_at=opening - timedelta(minutes=30),
                rate="1.35",
            )
        )
    return DatasetInput(name="SYNTHETIC test fixture", synthetic=True, bars=bars, fx=fx)


@pytest.fixture
def data():
    return fixture_data()


@pytest.fixture
def database(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture
def client(database):
    def db_override():
        with database() as db:
            yield db

    app.dependency_overrides[get_db] = db_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
