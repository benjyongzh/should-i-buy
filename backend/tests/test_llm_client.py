"""Controlled HTTP responses verify the provider boundary, not live model access."""

import json

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.llm import client as authoring
from app.schemas.domain import default_strategy


@pytest.mark.parametrize("mode", ["valid", "invalid_schema", "refusal", "truncated", "http_error"])
def test_structured_authoring_http_boundary(monkeypatch, mode):
    current = default_strategy().model_dump(mode="json")
    proposed = (
        {**current, "unsupported_code": "print('no')"} if mode == "invalid_schema" else current
    )
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(
            403 if mode == "http_error" else 200,
            json={
                "choices": [
                    {
                        "finish_reason": "length" if mode == "truncated" else "stop",
                        "message": {
                            "content": json.dumps(proposed),
                            "refusal": "refused" if mode == "refusal" else None,
                        },
                    }
                ]
            },
        )

    client_type = httpx.Client
    monkeypatch.setattr(
        authoring.httpx,
        "Client",
        lambda **kwargs: client_type(transport=httpx.MockTransport(handle)),
    )
    monkeypatch.setattr(
        authoring,
        "settings",
        lambda: Settings(
            llm_api_key=SecretStr("fixture-key"),
            llm_model="fixture-model",
            llm_base_url="https://llm.invalid/v1",
        ),
    )
    if mode == "valid":
        assert (
            authoring.CompatibleAuthor().propose("buy and hold", current).model_dump(mode="json")
            == current
        )
    else:
        with pytest.raises(ValueError):
            authoring.CompatibleAuthor().propose("buy and hold", current)
    assert len(requests) == 1
    assert str(requests[0].url) == "https://llm.invalid/v1/chat/completions"
    body = json.loads(requests[0].content)
    assert body["model"] == "fixture-model"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert requests[0].headers["authorization"] == "Bearer fixture-key"
