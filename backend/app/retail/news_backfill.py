"""Explicit quarantine for long historical acquisition; source defects stay visible."""

import hashlib
import json
from collections import Counter

from app.market_data.platform_providers import NewsFetch, normalize_news
from app.market_data.strategy_inputs import StrategyInput


def normalize_partition(body: NewsFetch, pages: list[dict], hashes: list[str]):
    source = normalize_news(body, [{"news": []}], hashes)
    rows = [row for page in pages for row in page.get("news") or []]
    counts = Counter(str(row.get("id")) for row in rows)
    events, quarantine, excluded = [], [], []
    for row in rows:
        identity = str(row.get("id"))
        fingerprint = hashlib.sha256(
            json.dumps(row, sort_keys=True, default=str).encode()
        ).hexdigest()
        try:
            if row.get("id") is None or counts[identity] != 1:
                raise ValueError("missing or duplicate source identity")
            normalized = normalize_news(body, [{"news": [row]}], hashes)
            events.extend(normalized.events)
            if not normalized.events:
                excluded.append(
                    {
                        "id": identity,
                        "row_hash": fingerprint,
                        "reason": "older publication updated in this query window",
                    }
                )
        except (ValueError, KeyError, TypeError) as exc:
            quarantine.append({"id": identity, "row_hash": fingerprint, "reason": str(exc)[:600]})
    payload = source.model_dump(mode="json")
    payload["events"] = [event.model_dump(mode="json") for event in events]
    candidate = StrategyInput.model_validate(payload)
    return candidate, {
        "request": body.model_dump(mode="json"),
        "pages": len(pages),
        "returned_records": len(rows),
        "events": len(events),
        "quarantined": quarantine,
        "excluded_older_versions": excluded,
        "provider_pagination_complete": bool(pages) and not pages[-1].get("next_page_token"),
        "original_vintages_certified": False,
        "automatically_approved": False,
    }
