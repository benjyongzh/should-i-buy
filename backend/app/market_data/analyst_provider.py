"""Benzinga ratings preparation; clocks/targets are not reconstructed from consensus."""

import hashlib
import json
import logging
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

import httpx

from app.core.config import settings
from app.market_data.platform_providers import FetchRange
from app.market_data.strategy_inputs import HistoricalEvent, StrategyInput


class RedactQueryKeys(logging.Filter):
    def filter(self, record):
        record.msg = re.sub(
            r"([?&](?:token|apiKey|apikey|api_key)=)[^&\s\"']+",
            r"\1[redacted]",
            record.getMessage(),
        )
        record.args = ()
        return True


logging.getLogger("httpx").addFilter(RedactQueryKeys())


class AnalystFetch(FetchRange):
    source_timezone: Literal["America/New_York", "UTC"]


def normalize_ratings(rows, body, hashes):
    zone = ZoneInfo(body.source_timezone)
    actions = {
        "upgrades": "upgrade",
        "downgrades": "downgrade",
        "maintains": "reiterate",
        "reiterates": "reiterate",
        "initiates coverage on": "initiate",
        "resumes coverage on": "resume",
        "suspends": "suspend",
        "terminates coverage on": "suspend",
        "raises": "price_target",
        "lowers": "price_target",
        "announces": "price_target",
    }
    output = []
    for row in rows:
        if row.get("ticker") not in body.symbols:
            raise ValueError("rating source returned an unrequested ticker")
        if not row.get("date") or not row.get("time") or not row.get("updated"):
            raise ValueError(
                "ratings require original date/time and version-update evidence; import a timestamped archival export when these are missing"
            )
        naive = datetime.fromisoformat(str(row["date"]) + "T" + str(row["time"]))
        if naive.tzinfo is not None:
            raise ValueError("date/time export must match the explicitly selected source timezone")
        published = naive.replace(tzinfo=zone)
        if (
            published.replace(fold=1).utcoffset() != published.utcoffset()
            or published.astimezone(UTC).astimezone(zone).replace(tzinfo=None) != naive
        ):
            raise ValueError(
                "ambiguous or nonexistent rating clock; import an explicit timezone-aware archival timestamp"
            )
        if not body.start <= published.date() <= body.end:
            raise ValueError("rating publication lies outside requested dates")
        updated = (
            datetime.fromisoformat(str(row["updated"]).replace("Z", "+00:00"))
            if "T" in str(row["updated"])
            else datetime.fromtimestamp(int(row["updated"]), UTC)
        )
        if updated.tzinfo is None:
            raise ValueError("rating update clock lacks timezone")
        if updated < published:
            raise ValueError(
                "rating update predates the declared publication; confirm the source timezone"
            )
        action = actions.get(
            str(row.get("action_company") or row.get("action_pt") or "").casefold().strip()
        )
        if action is None:
            raise ValueError(
                "unsupported rating action; normalize it explicitly instead of guessing"
            )
        prior = Decimal(str(row["pt_prior"])) if row.get("pt_prior") not in (None, "") else None
        current = (
            Decimal(str(row["pt_current"])) if row.get("pt_current") not in (None, "") else None
        )
        if (prior is not None or current is not None) and row.get("currency") != "USD":
            raise ValueError("nominal target currency must be explicitly USD")
        tags = []
        if prior is not None and current is not None and prior != current:
            tags = [
                "analyst.price_target",
                "analyst.target_raise" if current > prior else "analyst.target_lower",
            ]
        firm = str(row.get("analyst") or row.get("firm") or "")
        if not firm:
            raise ValueError("rating source lacks analyst firm identity")
        source_url = (
            row.get("url_news")
            or row.get("url_calendar")
            or row.get("url")
            or "https://api.benzinga.com/api/v2/calendar/ratings"
        )
        raw = json.dumps(row, sort_keys=True, default=str).encode()
        output.append(
            HistoricalEvent(
                event_id=str(row["id"]),
                published_at=published,
                available_at=updated,
                category="analyst." + action,
                tags=tags,
                symbols=[row["ticker"]],
                title=f"{firm}: {action} {row['ticker']}",
                source_url=source_url,
                original_content_hash=hashlib.sha256(raw).hexdigest(),
                derivation="Benzinga nominal rating/target fields, gated at actual version update; no adjusted target or consensus reconstruction",
                access="subscription",
                details={
                    "type": "analyst",
                    "firm": firm,
                    "analyst": row.get("analyst_name"),
                    "action": action,
                    "rating_before": row.get("rating_prior") or None,
                    "rating_after": row.get("rating_current") or None,
                    "target_before": prior,
                    "target_after": current,
                    "report_available_at": published,
                },
            )
        )
    return StrategyInput(
        kind="events",
        name=f"Benzinga ratings {body.start}–{body.end}",
        source="benzinga-ratings",
        source_url="https://api.benzinga.com/api/v2/calendar/ratings",
        availability_policy="Current nominal individual rating records, not original publication vintages. Publication timezone explicitly selected from source documentation; visibility gated at version updated clock. Subscription access requires explicit strategy opt-in. No future-adjusted price targets or current consensus substitution.",
        coverage_start=datetime.combine(body.start, datetime.min.time(), zone),
        coverage_end=datetime.combine(body.end + timedelta(days=1), datetime.min.time(), zone),
        symbols=body.symbols,
        stream_id="ANALYST_RATINGS",
        access_coverage="any_licensed",
        events=output,
        source_hashes=hashes,
        category_catalog=sorted(
            {"analyst." + a for a in actions.values()}
            | {"analyst.price_target", "analyst.target_raise", "analyst.target_lower"}
        ),
    )


def fetch_ratings(body: AnalystFetch):
    key = settings().benzinga_api_key.get_secret_value()
    if not key:
        raise ValueError(
            "Benzinga ratings access is not configured; set BENZINGA_API_KEY or import a timestamped source export"
        )
    rows = []
    hashes = []
    with httpx.Client(timeout=60) as client:
        for page in range(100):
            params = {
                "token": key,
                "page": page,
                "pagesize": 100,
                "parameters[tickers]": ",".join(body.symbols),
                "parameters[date_from]": str(body.start),
                "parameters[date_to]": str(body.end),
            }
            try:
                response = client.get(
                    "https://api.benzinga.com/api/v2/calendar/ratings",
                    params=params,
                    headers={"Accept": "application/json"},
                )
            except httpx.HTTPError as exc:
                raise ValueError("Benzinga connection failed; retry a smaller range") from exc
            if response.status_code != 200:
                raise ValueError(
                    f"Benzinga ratings HTTP {response.status_code}; confirm historical entitlement"
                )
            if len(response.content) > 20_000_000:
                raise ValueError("rating response exceeded size limit")
            payload = json.loads(response.content, parse_float=Decimal)
            batch = payload.get("ratings", [])
            hashes.append(hashlib.sha256(response.content).hexdigest())
            rows.extend(batch)
            if len(rows) > 10000:
                raise ValueError("rating preparation limit reached; use smaller date partitions")
            if len(batch) < 100:
                break
        else:
            raise ValueError("rating pagination limit reached")
    return normalize_ratings(rows, body, hashes)
