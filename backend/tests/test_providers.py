from datetime import UTC, date, datetime

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.market_data import providers
from app.market_data.validation import validate_dataset
from app.market_data.view import DataView


def test_alpaca_pagination_raw_iex_and_extended_volume_availability(monkeypatch):
    requests = []

    def handle(request):
        requests.append(request)
        day = "2019-01-02" if len(requests) == 1 else "2019-01-03"
        return httpx.Response(
            200,
            json={
                "bars": {
                    "SPY": [
                        {"t": day + "T05:00:00Z", "o": 100, "h": 102, "l": 99, "c": 101, "v": 10000}
                    ]
                },
                "next_page_token": "next" if len(requests) == 1 else None,
            },
        )

    client_type = httpx.Client
    monkeypatch.setattr(
        providers.httpx,
        "Client",
        lambda **kwargs: client_type(transport=httpx.MockTransport(handle)),
    )
    monkeypatch.setattr(
        providers,
        "settings",
        lambda: Settings(
            alpaca_api_key=SecretStr("fixture"), alpaca_secret_key=SecretStr("fixture")
        ),
    )
    monkeypatch.setattr(providers.time, "sleep", lambda _: None)
    data = providers.AlpacaProvider().fetch(["SPY"], date(2019, 1, 2), date(2019, 1, 3))
    assert len(data.bars) == 2 and len(requests) == 2
    assert requests[0].url.params["adjustment"] == "raw"
    assert requests[0].url.params["feed"] == "iex"
    assert requests[1].url.params["page_token"] == "next"
    assert requests[0].url.host == "data.alpaca.markets"
    assert data.decision_time == "20:30_America/New_York"
    assert data.bars[0].available_at == datetime(2019, 1, 3, 1, 15, tzinfo=UTC)
    assert not DataView(data.bars, datetime(2019, 1, 2, 22, tzinfo=UTC)).history("SPY")
    assert not validate_dataset(data)["SPY"]["missing_sessions"]


def test_provider_failure_does_not_use_synthetic_data(monkeypatch):
    client_type = httpx.Client
    monkeypatch.setattr(
        providers.httpx,
        "Client",
        lambda **kwargs: client_type(
            transport=httpx.MockTransport(lambda request: httpx.Response(403))
        ),
    )
    monkeypatch.setattr(
        providers,
        "settings",
        lambda: Settings(
            alpaca_api_key=SecretStr("fixture"), alpaca_secret_key=SecretStr("fixture")
        ),
    )
    with pytest.raises(ValueError, match="HTTP 403"):
        providers.AlpacaProvider().fetch(["SPY"], date(2019, 1, 2), date(2019, 1, 3))
