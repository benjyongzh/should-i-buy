import asyncio

import httpx
import pytest

from app.core.config import settings


def test_configured_environment_cannot_enable_live_providers():
    config = settings()
    assert not config.alpaca_api_key.get_secret_value()
    assert not config.alpaca_secret_key.get_secret_value()
    assert not config.llm_api_key.get_secret_value()
    assert not config.llm_model
    with httpx.Client() as client:
        with pytest.raises(AssertionError, match="Unmocked outbound HTTP"):
            client.get("https://provider.invalid/never-connect")


def test_async_provider_http_is_also_blocked():
    async def request():
        async with httpx.AsyncClient() as client:
            await client.get("https://provider.invalid/never-connect")

    with pytest.raises(AssertionError, match="Unmocked outbound HTTP"):
        asyncio.run(request())
