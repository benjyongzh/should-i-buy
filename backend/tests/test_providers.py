from datetime import UTC, date, datetime

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.market_data import providers
from app.market_data.validation import validate_dataset
from app.market_data.view import DataView


@pytest.mark.parametrize("feed", ["iex", "sip"])
def test_alpaca_pagination_raw_feed_and_extended_volume_availability(monkeypatch, feed):
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
    data = providers.AlpacaProvider().fetch(["SPY"], date(2019, 1, 2), date(2019, 1, 3), feed=feed)
    assert len(data.bars) == 2 and len(requests) == 2
    assert requests[0].url.params["adjustment"] == "raw"
    assert requests[0].url.params["feed"] == feed
    assert data.provider == f"alpaca-{feed}"
    assert f"{feed.upper()} feed" in data.availability_policy
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


def test_provider_rejects_unfinished_daily_bar(monkeypatch):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2019, 1, 2, 18, tzinfo=UTC)

    client_type = httpx.Client
    payload = {
        "bars": {
            "SPY": [
                {"t": "2019-01-02T05:00:00Z", "o": 100, "h": 102, "l": 99, "c": 101, "v": 10000}
            ]
        }
    }
    monkeypatch.setattr(providers, "datetime", FrozenDatetime)
    monkeypatch.setattr(
        providers.httpx,
        "Client",
        lambda **kwargs: client_type(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ),
    )
    monkeypatch.setattr(
        providers,
        "settings",
        lambda: Settings(
            alpaca_api_key=SecretStr("fixture"), alpaca_secret_key=SecretStr("fixture")
        ),
    )
    with pytest.raises(ValueError, match="unfinished daily session"):
        providers.AlpacaProvider().fetch(["SPY"], date(2019, 1, 2), date(2019, 1, 2))


def test_alpaca_import_retains_feed_actions_and_completeness(client, data, monkeypatch):
    from app.api import routes
    from app.schemas.domain import Action

    feeds = []

    def fetch(self, symbols, start, end, *, feed):
        feeds.append(feed)
        result = data.model_copy(deep=True)
        result.provider = f"alpaca-{feed}"
        return result

    monkeypatch.setattr(routes.AlpacaProvider, "fetch", fetch)
    action = Action(
        symbol="SPY",
        session_date=data.bars[1].session_date,
        available_at=data.bars[0].available_at,
        kind="dividend",
        value="1.25",
        payment_date=data.bars[2].session_date,
    )
    body = {
        "symbols": ["SPY"],
        "start": str(data.bars[0].session_date),
        "end": str(data.bars[-1].session_date),
        "feed": "sip",
        "corporate_actions_reviewed": True,
        "dividends_complete": True,
        "actions_csv": "symbol,session_date,available_at,kind,value,payment_date\n"
        + ",".join(
            str(getattr(action, k))
            for k in ["symbol", "session_date", "available_at", "kind", "value", "payment_date"]
        ),
    }
    response = client.post("/api/market-data/alpaca", json=body)
    assert response.status_code == 201, response.text
    revision = response.json()
    exported = client.get(f"/api/market-data/datasets/{revision['id']}/export").json()
    assert feeds == ["sip"]
    assert exported["provider"] == "alpaca-sip"
    assert exported["corporate_actions_reviewed"] and exported["dividends_complete"]
    assert exported["actions"] == [action.model_dump(mode="json")]
    body["dividends_complete"] = False
    second = client.post("/api/market-data/alpaca", json=body)
    assert second.status_code == 201, second.text
    assert second.json()["content_hash"] != revision["content_hash"]
    body["feed"] = "unsupported"
    assert client.post("/api/market-data/alpaca", json=body).status_code == 422
