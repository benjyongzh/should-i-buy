from datetime import date, timedelta

import httpx
import pytest
from platform_fixtures import platform_data
from pydantic import SecretStr

from app.core.config import Settings
from app.market_data import platform_providers as providers


def controlled(monkeypatch, handler):
    client_type = httpx.Client
    monkeypatch.setattr(
        providers.httpx,
        "Client",
        lambda **kwargs: client_type(transport=httpx.MockTransport(handler)),
    )
    monkeypatch.setattr(
        providers,
        "settings",
        lambda: Settings(
            alpaca_api_key=SecretStr("fixture-key"), alpaca_secret_key=SecretStr("fixture-secret")
        ),
    )


def minute_rows():
    _, source = platform_data(date(2020, 1, 2), date(2020, 1, 2), minute=1)
    return [
        {"t": b.start_at.isoformat(), "o": 100, "h": 101, "l": 99, "c": 100.5, "v": 100}
        for b in source.bars
    ]


def test_alpaca_minute_aggregation_uses_complete_open_aligned_intervals(monkeypatch):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(200, json={"bars": {"SPY": minute_rows()}, "next_page_token": None})

    controlled(monkeypatch, handle)
    source = providers.fetch_intraday(
        providers.IntradayFetch(
            symbols=["SPY"], start="2020-01-02", end="2020-01-02", bar_minutes=60
        )
    )
    assert len(source.bars) == 7 and source.bars[-1].end_at - source.bars[-1].start_at == timedelta(
        minutes=30
    )
    assert source.bars[0].volume == 6000 and source.bars[0].high == 101 and source.bars[0].low == 99
    assert source.bars[0].available_at - source.bars[0].end_at == timedelta(seconds=60)
    assert not source.complete and not source.reviewed and not source.synthetic
    assert (
        requests[0].url.params["timeframe"] == "1Min"
        and requests[0].url.params["adjustment"] == "raw"
    )
    assert requests[0].url.params["feed"] == "sip" and requests[0].url.params["asof"] == "-"
    assert len(source.source_hashes[0]) == 64


def test_missing_minutes_are_omitted_without_fabricated_flat_bars(monkeypatch):
    controlled(
        monkeypatch, lambda r: httpx.Response(200, json={"bars": {"SPY": minute_rows()[1:]}})
    )
    source = providers.fetch_intraday(
        providers.IntradayFetch(symbols=["SPY"], start="2020-01-02", end="2020-01-02")
    )
    assert len(source.bars) == 77 and source.bars[0].start_at.minute == 35
    assert "Missing 1 intervals omitted" in source.availability_policy


def test_revised_company_news_uses_version_clock_and_retains_keyword_rules(monkeypatch):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "news": [
                    {
                        "id": 123,
                        "created_at": "2020-01-02T15:00:00Z",
                        "updated_at": "2020-01-02T17:00:00Z",
                        "headline": "SYNTHETIC company oil headline",
                        "content": "<p>Strait of Hormuz transport disruption</p>",
                        "symbols": ["SPY"],
                        "url": "https://fixture.invalid/news",
                    }
                ]
            },
        )

    controlled(monkeypatch, handle)
    source = providers.fetch_news(
        providers.NewsFetch(
            symbols=["SPY"],
            start="2020-01-02",
            end="2020-01-02",
            keyword_tags=[{"tag": "geopolitics", "any_terms": ["Hormuz"]}],
        )
    )
    event = source.events[0]
    assert event.available_at.hour == 17 and event.published_at.hour == 15
    assert event.tags == ["geopolitics"] and event.details.keyword_tags == {
        "geopolitics": ["Hormuz"]
    }
    assert event.score is None and "<p>" not in event.details.text
    assert not source.reviewed and not source.complete
    assert requests[0].url.path == "/v1beta1/news"


def test_provider_errors_and_future_ranges_are_explicit_without_secret_leaks(monkeypatch):
    controlled(monkeypatch, lambda r: httpx.Response(403, json={"message": "no entitlement"}))
    with pytest.raises(ValueError, match="HTTP 403") as error:
        providers.fetch_news(
            providers.NewsFetch(symbols=["SPY"], start="2020-01-02", end="2020-01-02")
        )
    assert "fixture-secret" not in str(error.value)
    with pytest.raises(ValueError):
        providers.IntradayFetch(symbols=["SPY"], start="2020-01-01", end="2020-04-01")
    with pytest.raises(ValueError):
        providers.IntradayFetch(symbols=["SPY", "SPY"], start="2020-01-01", end="2020-01-02")
