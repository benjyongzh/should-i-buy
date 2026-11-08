"""Read-only preparation adapters. Returned revisions require explicit review."""

import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from html.parser import HTMLParser
from typing import Literal
from zoneinfo import ZoneInfo

import httpx
from pydantic import Field, model_validator

from app.core.config import settings
from app.market_data.calendar import session_times, sessions
from app.market_data.strategy_inputs import HistoricalEvent, IntradayBar, StrategyInput
from app.schemas.domain import StrictModel, Symbol


class FetchRange(StrictModel):
    symbols: list[Symbol] = Field(min_length=1, max_length=5)
    start: date
    end: date

    @model_validator(mode="after")
    def bounded(self):
        if (
            not date(1990, 1, 1) <= self.start <= self.end <= datetime.now(UTC).date()
            or (self.end - self.start).days > 31
        ):
            raise ValueError(
                "provider requests require a completed historical range of at most 32 calendar days"
            )
        if len(set(self.symbols)) != len(self.symbols):
            raise ValueError("duplicate fetch symbol")
        return self


class IntradayFetch(FetchRange):
    bar_minutes: Literal[1, 5, 15, 30, 60] = 5
    feed: Literal["sip", "iex"] = "sip"
    assumed_delay_seconds: int = Field(default=60, ge=1, le=900)


class KeywordTag(StrictModel):
    tag: str = Field(min_length=1, max_length=80)
    any_terms: list[str] = Field(min_length=1, max_length=30)


class NewsFetch(FetchRange):
    keyword_tags: list[KeywordTag] = Field(default_factory=list, max_length=30)
    access: Literal["public", "subscription"] = "subscription"


def alpaca_pages(path, params, *, capture=None):
    config = settings()
    if (
        not config.alpaca_api_key.get_secret_value()
        or not config.alpaca_secret_key.get_secret_value()
    ):
        raise ValueError("Alpaca credentials are not configured; import source files instead")
    headers = {
        "APCA-API-KEY-ID": config.alpaca_api_key.get_secret_value(),
        "APCA-API-SECRET-KEY": config.alpaca_secret_key.get_secret_value(),
    }
    hashes = []
    pages = []
    with httpx.Client(timeout=60) as client:
        for _ in range(50):
            try:
                response = client.get(
                    "https://data.alpaca.markets" + path, params=params, headers=headers
                )
            except httpx.HTTPError as exc:
                raise ValueError(
                    "Alpaca data connection failed; retry a smaller historical range"
                ) from exc
            if response.status_code != 200:
                raise ValueError(
                    f"Alpaca data HTTP {response.status_code}; check entitlement and rate limits"
                )
            if len(response.content) > 20_000_000:
                raise ValueError("provider response exceeded the preparation limit")
            if capture is not None:
                capture(response)
            payload = json.loads(response.content, parse_float=Decimal)
            hashes.append(hashlib.sha256(response.content).hexdigest())
            pages.append(payload)
            token = payload.get("next_page_token")
            if not token:
                break
            params = {**params, "page_token": token}
        else:
            raise ValueError("provider pagination limit reached; use smaller source partitions")
    return pages, hashes


def fetch_intraday(body: IntradayFetch):
    days = sessions(body.start, body.end)
    if not days:
        raise ValueError("no historical sessions in range")
    params = {
        "symbols": ",".join(body.symbols),
        "start": str(body.start),
        "end": str(body.end + timedelta(days=1)),
        "timeframe": "1Min",
        "feed": body.feed,
        "adjustment": "raw",
        "asof": "-",
        "sort": "asc",
        "limit": 10000,
    }
    pages, hashes = alpaca_pages("/v2/stocks/bars", params)
    minute_rows = {}
    allowed = set(days)
    for page in pages:
        for symbol, rows in (page.get("bars") or {}).items():
            if symbol not in body.symbols:
                raise ValueError("provider returned an unrequested symbol")
            for row in rows:
                clock = datetime.fromisoformat(row["t"].replace("Z", "+00:00"))
                day = clock.astimezone(ZoneInfo("America/New_York")).date()
                if day not in allowed:
                    continue
                opening, closing = session_times(day)
                if not opening <= clock < closing:
                    continue
                if (clock - opening).total_seconds() % 60:
                    raise ValueError("provider minute was not aligned to its session")
                key = (symbol, clock)
                if key in minute_rows:
                    raise ValueError("duplicate provider minute; no silent replacement")
                minute_rows[key] = row
                if len(minute_rows) > 100_000:
                    raise ValueError(
                        "minute preparation row limit reached; fetch a smaller partition"
                    )
    bars = []
    omitted = 0
    for day in days:
        opening, closing = session_times(day)
        for symbol in body.symbols:
            clock = opening
            while clock < closing:
                end = min(clock + timedelta(minutes=body.bar_minutes), closing)
                expected = [
                    clock + timedelta(minutes=i)
                    for i in range(int((end - clock).total_seconds() / 60))
                ]
                values = [minute_rows[(symbol, t)] for t in expected if (symbol, t) in minute_rows]
                if len(values) != len(expected):
                    omitted += 1
                    clock = end
                    continue
                available = end + timedelta(seconds=body.assumed_delay_seconds)
                if available > datetime.now(UTC):
                    raise ValueError("unfinished intraday interval cannot be imported")
                bars.append(
                    IntradayBar(
                        symbol=symbol,
                        session_date=day,
                        start_at=clock,
                        end_at=end,
                        open=str(values[0]["o"]),
                        high=str(max(Decimal(str(v["h"])) for v in values)),
                        low=str(min(Decimal(str(v["l"])) for v in values)),
                        close=str(values[-1]["c"]),
                        volume=str(sum((Decimal(str(v["v"])) for v in values), Decimal(0))),
                        source_timestamp=end,
                        available_at=available,
                        quality=[
                            "revised_history_not_publication_vintage",
                            "assumed_completion_delay",
                            "aggregated_from_complete_1min_intervals",
                        ],
                    )
                )
                clock = end
    if not bars:
        raise ValueError(
            "no complete regular-session intervals returned; missing data was not filled"
        )
    return StrategyInput(
        kind="intraday",
        name=f"Alpaca {body.feed.upper()} {body.bar_minutes}m {body.start}–{body.end}",
        source=f"alpaca-{body.feed}",
        source_url="https://data.alpaca.markets/v2/stocks/bars",
        availability_policy=f"Current raw revised minute history, not original vintages. RTH aggregated from complete minute intervals at the exchange open. Assumed {body.assumed_delay_seconds}s completion delay. Missing {omitted} intervals omitted; no fill. Execution uses next strictly later interval opens as full-fill proxies, not certified auction/quote prints.",
        coverage_start=session_times(days[0])[0],
        coverage_end=session_times(days[-1])[1],
        symbols=body.symbols,
        bar_minutes=body.bar_minutes,
        bars=bars,
        source_hashes=hashes,
    )


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, value):
        self.parts.append(value)


def fetch_news(body: NewsFetch, *, capture=None):
    pages, hashes = alpaca_pages(
        "/v1beta1/news",
        {
            "symbols": ",".join(body.symbols),
            "start": str(body.start),
            "end": str(body.end + timedelta(days=1)),
            "sort": "asc",
            "limit": 50,
            "include_content": "true",
        },
        capture=capture,
    )
    return normalize_news(body, pages, hashes)


def normalize_news(body: NewsFetch, pages, hashes):
    """Replay retained provider pages without backdating current article versions."""
    start = datetime.combine(body.start, datetime.min.time(), UTC)
    end = datetime.combine(body.end + timedelta(days=1), datetime.min.time(), UTC)
    events = []
    ids = set()
    for page in pages:
        for article in page.get("news") or []:
            identifier = str(article["id"])
            if identifier in ids:
                raise ValueError("duplicate news identity; import explicit source revisions")
            ids.add(identifier)
            if not article.get("created_at") or not article.get("updated_at"):
                raise ValueError("news requires publication and current-version update timestamps")
            published = datetime.fromisoformat(article["created_at"].replace("Z", "+00:00"))
            updated = datetime.fromisoformat(article["updated_at"].replace("Z", "+00:00"))
            if published.tzinfo is None or updated.tzinfo is None:
                raise ValueError("news timestamps require explicit timezones")
            if not set(article.get("symbols", [])) & set(body.symbols):
                raise ValueError("news lacks any requested symbol association")
            if updated < published:
                raise ValueError("article update precedes original publication")
            if published < start and start <= updated < end:
                # The endpoint can return older articles updated in this query window.
                # Retained pages keep them; this candidate is a publication cohort.
                continue
            if not start <= published < end:
                raise ValueError("news publication lies outside requested half-open range")
            parser = TextOnly()
            parser.feed(str(article.get("content") or article.get("summary") or ""))
            text = " ".join(parser.parts)[:30000]
            searchable = (str(article["headline"]) + " " + text).casefold()
            tags = [
                rule.tag
                for rule in body.keyword_tags
                if any(term.casefold() in searchable for term in rule.any_terms)
            ]
            raw = json.dumps(article, sort_keys=True, default=str).encode()
            events.append(
                HistoricalEvent(
                    event_id=identifier,
                    published_at=published,
                    available_at=max(published, updated),
                    category="company_news",
                    access=body.access,
                    tags=tags,
                    symbols=[s for s in article.get("symbols", []) if s in body.symbols],
                    title=article["headline"],
                    source_url=article["url"],
                    original_content_hash=hashlib.sha256(raw).hexdigest(),
                    derivation="Provider article/symbol fields; optional deterministic keyword-v1 tags, rules hash "
                    + hashlib.sha256(body.model_dump_json().encode()).hexdigest(),
                    details={
                        "type": "news",
                        "article_id": identifier,
                        "version_available_at": max(published, updated),
                        "text": text[:30000],
                        "keyword_tags": {rule.tag: rule.any_terms for rule in body.keyword_tags},
                    },
                )
            )
            if len(events) > 10000:
                raise ValueError("news preparation limit exceeded; request a smaller range")
    start = datetime.combine(body.start, datetime.min.time(), UTC)
    end = datetime.combine(body.end + timedelta(days=1), datetime.min.time(), UTC)
    return StrategyInput(
        kind="events",
        name=f"Alpaca/Benzinga company news {body.start}–{body.end}",
        source="alpaca-benzinga",
        source_url="https://data.alpaca.markets/v1beta1/news",
        availability_policy="Current article versions only; gated at max(created_at,updated_at), never backdated revised text. Vendor coverage is not all public news. Older articles returned because of updates within the query window are excluded from this publication cohort, not backdated or treated as new publications. Query exhaustion does not certify the original historical archive. Optional deterministic keyword-v1 tags are in-sample research definitions, not an LLM's retrospective knowledge. Public dissemination/access and coverage require review.",
        coverage_start=start,
        coverage_end=end,
        symbols=body.symbols,
        stream_id="COMPANY_NEWS",
        access_coverage="any_licensed" if body.access == "subscription" else "public_only",
        category_catalog=["company_news"] + sorted({rule.tag for rule in body.keyword_tags}),
        events=events,
        source_hashes=hashes,
    )
