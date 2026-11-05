import json
from typing import Protocol

import httpx
from pydantic import Field

from app.core.config import settings
from app.schemas.domain import StrategyConfig, StrictModel

PROMPT_VERSION = "strategy-author-v3-historical-capabilities"


class StrategyPlan(StrictModel):
    config: StrategyConfig | None
    interpretation: str = Field(min_length=1, max_length=5000)
    assumptions: list[str] = Field(default_factory=list, max_length=30)
    data_requirements: list[str] = Field(default_factory=list, max_length=30)
    unsupported_requests: list[str] = Field(default_factory=list, max_length=30)


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
        return StrategyConfig.model_validate(
            self._request(prompt, current, StrategyConfig, "strategy_config")
        )

    def plan(self, prompt: str, current: dict) -> StrategyPlan:
        return StrategyPlan.model_validate(
            self._request(prompt, current, StrategyPlan, "strategy_plan")
        )

    def _request(self, prompt, current, response_model, response_name):
        config = settings()
        if not config.llm_api_key.get_secret_value() or not config.llm_model:
            raise ValueError(
                "LLM authoring is not configured. Set LLM_API_KEY and LLM_MODEL on the server; manual editing remains available."
            )
        schema = compatible_schema(response_model.model_json_schema())
        body = {
            "model": config.llm_model,
            "max_completion_tokens": 5000,
            "messages": [
                {
                    "role": "system",
                    "content": "You author declarative long-only historical strategies within the supplied schema, never executable code. Return the requested response schema only. If returning a strategy plan, explain exact timing/selection/sizing semantics, assumptions, data requirements, and unsupported requests. Set config null for requests which cannot be represented; never silently substitute a different strategy. No broker execution, shorts, leverage or ML training. Intraday execution_policy windows are relative to actual exchange open/close; completed-bar decisions fill at the next strictly later eligible interval open, not the same bar's earlier open. Intraday profile/source revisions are required; daily candles cannot supply intraday execution. Market wrappers select daily/intraday completed histories. Universe filters, sector preferences, ranking and top_n act within the profile's allowed symbols using historical membership/classifications. Event streams require reviewed publication-time histories: COMPANY_NEWS, ANALYST_RATINGS, ECONOMIC_RELEASES or CONGRESS_TRADES are possible bindings, not guaranteed datasets. Use symbol scope for company-specific records, global for broad events; categories/tags and actors must match actual imported source records. News revisions use version availability. Analyst changes require report availability. Congress records use public disclosure time, never transaction date; disclosed ranges are not exact trade amounts. Scores computed later cannot be backdated. Public_only is default; any_licensed must be explicit. For ratings price targets use event value_field analyst_target_after; Congress amount_min/max preserve bounds; economic surprises require historical pre-release consensus. No historical data or external input observations may be invented. Arithmetic and conditional sizing_rules are declarative. Portfolio scalars reflect the current decision clock. Percentage sizing uses fractions, e.g. 0.1=10%. trading schedules select close decisions. Monthly means the first calendar-month trading session's decision. Once retries until first buy fills. Set allow_additions true for DCA. cash_percent sizes current cash; target_allocation buys/trims toward equity fraction; exit_fraction sells that fraction, exits take priority. Profile funding/costs/capital are separate and must not be put in strategy JSON. Current draft: "
                    + json.dumps(current),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": response_name, "strict": True, "schema": schema},
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
                return json.loads(message["message"]["content"])
        except httpx.HTTPError as exc:
            raise ValueError("LLM provider connection failed; check server configuration") from exc
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("LLM provider returned an unsupported response") from exc
