import logging
from decimal import Decimal

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.market_data import analyst_provider as provider


def request(**changes):
    return provider.AnalystFetch(
        symbols=["SPY"],
        start="2020-01-02",
        end="2020-01-02",
        source_timezone="America/New_York",
        **changes,
    )


def record(**changes):
    return dict(
        id="fixture-1",
        date="2020-01-02",
        time="10:00:00",
        updated="2020-01-02T17:00:00Z",
        ticker="SPY",
        analyst="SYNTHETIC firm",
        analyst_name="SYNTHETIC analyst",
        action_company="Upgrades",
        rating_prior="Hold",
        rating_current="Buy",
        pt_prior="100",
        pt_current="120",
        adjusted_pt_current="60",
        currency="USD",
        **changes,
    )


def test_ratings_preserve_nominal_targets_and_late_version_clocks():
    source = provider.normalize_ratings([record()], request(), ["a" * 64])
    event = source.events[0]
    assert event.published_at.hour == 10 and event.available_at.hour == 17
    assert event.details.target_after == Decimal("120") and event.details.target_before == 100
    assert event.access == "subscription" and source.access_coverage == "any_licensed"
    assert "analyst.target_raise" in event.tags
    assert not source.complete and not source.reviewed
    assert source.source_hashes == ["a" * 64] and len(event.original_content_hash) == 64


@pytest.mark.parametrize(
    "change,match",
    [
        ({"time": ""}, "date/time"),
        ({"updated": ""}, "date/time"),
        ({"updated": "2020-01-02T14:00:00Z"}, "predates"),
        ({"currency": "SGD"}, "USD"),
        ({"action_company": "unknown"}, "unsupported"),
    ],
)
def test_ratings_reject_ambiguous_or_unsubstantiated_information(change, match):
    with pytest.raises(ValueError, match=match):
        provider.normalize_ratings([{**record(), **change}], request(), [])
    with pytest.raises(ValueError):
        provider.AnalystFetch(symbols=["SPY"], start="2020-01-02", end="2020-01-02")


def test_benzinga_http_and_log_redaction(monkeypatch, caplog):
    key = "SYNTHETIC-sensitive-token"
    monkeypatch.setattr(provider, "settings", lambda: Settings(benzinga_api_key=SecretStr(key)))
    client = httpx.Client
    seen = []

    def handler(req):
        seen.append(req)
        return httpx.Response(200, json={"ratings": [record()]})

    monkeypatch.setattr(
        provider.httpx, "Client", lambda **kwargs: client(transport=httpx.MockTransport(handler))
    )
    with caplog.at_level(logging.INFO, logger="httpx"):
        source = provider.fetch_ratings(request())
    assert len(source.events) == 1 and seen[0].url.params["parameters[tickers]"] == "SPY"
    assert key not in caplog.text and "[redacted]" in caplog.text
    monkeypatch.setattr(provider, "settings", lambda: Settings(benzinga_api_key=SecretStr("")))
    with pytest.raises(ValueError, match="BENZINGA_API_KEY"):
        provider.fetch_ratings(request())
