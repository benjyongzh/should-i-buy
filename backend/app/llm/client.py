import json
from typing import Protocol

import httpx

from app.core.config import settings
from app.schemas.domain import StrategyConfig

PROMPT_VERSION = "strategy-author-v1"


class AuthoringProvider(Protocol):
    def propose(self, prompt: str, current: dict) -> StrategyConfig: ...


def compatible_schema(schema):
    if isinstance(schema, list):
        return [compatible_schema(v) for v in schema]
    if not isinstance(schema, dict):
        return schema
    output = {
        k: compatible_schema(v)
        for k, v in schema.items()
        if k not in ("default", "discriminator", "title")
    }
    if "oneOf" in output:
        output["anyOf"] = output.pop("oneOf")
    if output.get("type") == "object":
        output["required"] = list(output.get("properties", {}))
        output["additionalProperties"] = False
    return output


class CompatibleAuthor:
    def propose(self, prompt: str, current: dict) -> StrategyConfig:
        config = settings()
        if not config.llm_api_key.get_secret_value() or not config.llm_model:
            raise ValueError(
                "LLM authoring is not configured. Set LLM_API_KEY and LLM_MODEL on the server; manual editing remains available."
            )
        schema = compatible_schema(StrategyConfig.model_json_schema())
        body = {
            "model": config.llm_model,
            "max_completion_tokens": 5000,
            "messages": [
                {
                    "role": "system",
                    "content": "You author declarative long-only daily strategies. Return only the supported JSON strategy configuration. Do not claim predictive historical knowledge. Percentage sizing uses fractions, e.g. 0.1 = 10%. Current draft: "
                    + json.dumps(current),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "strategy_config", "strict": True, "schema": schema},
            },
        }
        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(
                    config.llm_base_url.rstrip("/") + "/chat/completions",
                    headers={"Authorization": "Bearer " + config.llm_api_key.get_secret_value()},
                    json=body,
                )
                if response.status_code != 200:
                    raise ValueError(
                        f"LLM provider returned HTTP {response.status_code}; check model and structured-output support"
                    )
                if len(response.content) > 100_000:
                    raise ValueError("LLM response exceeded size limit")
                message = response.json()["choices"][0]
                if message.get("finish_reason") != "stop" or message["message"].get("refusal"):
                    raise ValueError("LLM did not produce a complete supported strategy")
                return StrategyConfig.model_validate_json(message["message"]["content"])
        except httpx.HTTPError as exc:
            raise ValueError("LLM provider connection failed; check server configuration") from exc
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("LLM provider returned an unsupported response") from exc
