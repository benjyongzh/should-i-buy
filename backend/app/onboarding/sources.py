"""Bounded public-source collection with fixed provider hosts and retained bytes."""

import json
import re
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.market_data.calendar import session_times, sessions
from app.models.entities import SourceArtifact
from app.onboarding.evidence import retain_artifact

NY = ZoneInfo("America/New_York")


class SourceClient:
    def __init__(self, db: Session, intake_id: str, checkpoint):
        self.db, self.intake_id, self.checkpoint = db, intake_id, checkpoint
        self.bytes, self.calls, self.last_sec = 0, 0, 0.0
        self.artifacts: list[SourceArtifact] = []

    def capture(self, response: httpx.Response, kind="daily_prices", metadata=None):
        self.calls += 1
        if self.calls > 240:
            raise ValueError("intake request budget exhausted")
        response.read()
        return self.store(str(response.request.url), kind, response.content, metadata or {})

    def store(self, url, kind, body, metadata):
        self.bytes += len(body)
        if self.bytes > settings().intake_max_bytes:
            raise ValueError("intake source-byte budget exhausted; use a shorter date interval")
        if len(url) > 1000:
            raise ValueError("source URL exceeds evidence limit")
        row = retain_artifact(self.db, self.intake_id, url, kind, body, metadata)
        if row.id not in {a.id for a in self.artifacts}:
            self.artifacts.append(row)
        self.checkpoint()
        return row

    def get(self, url, kind, *, params=None, metadata=None):
        if not url.startswith(
            ("https://www.sec.gov/", "https://data.sec.gov/", "https://data.alpaca.markets/")
        ):
            raise ValueError("unsupported source host")
        self.calls += 1
        if self.calls > 240:
            raise ValueError("intake request budget exhausted")
        self.checkpoint()
        headers = {}
        if "sec.gov/" in url:
            contact = settings().data_source_contact_email.strip()
            if not re.fullmatch(r"[^\s@\r\n]+@[^\s@\r\n]+\.[^\s@\r\n]+", contact):
                raise ValueError("configure DATA_SOURCE_CONTACT_EMAIL for SEC collection")
            delay = 1.1 - (time.monotonic() - self.last_sec)
            if delay > 0:
                time.sleep(delay)
            self.last_sec = time.monotonic()
            headers["User-Agent"] = "TradingLabResearch/1.0 " + contact
        else:
            config = settings()
            if (
                not config.alpaca_api_key.get_secret_value()
                or not config.alpaca_secret_key.get_secret_value()
            ):
                raise ValueError("configure the existing Alpaca market-data credentials")
            headers = {
                "APCA-API-KEY-ID": config.alpaca_api_key.get_secret_value(),
                "APCA-API-SECRET-KEY": config.alpaca_secret_key.get_secret_value(),
            }
        try:
            with httpx.Client(timeout=45, follow_redirects=False) as client:
                with client.stream("GET", url, params=params, headers=headers) as response:
                    if response.status_code != 200:
                        raise ValueError(
                            f"source request rejected (HTTP {response.status_code}); no data substituted"
                        )
                    parts, total = [], 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > settings().intake_max_artifact_bytes:
                            raise ValueError("source artifact exceeds size limit")
                        parts.append(chunk)
                    resolved = str(response.request.url)
        except httpx.HTTPError as exc:
            raise ValueError(
                "source connection failed; retry or use reviewed file imports"
            ) from exc
        row = self.store(resolved, kind, b"".join(parts), metadata or {})
        return row


def json_body(artifact):
    return json.loads(artifact.body)


def resolve_identity(client, symbol):
    artifact = client.get("https://www.sec.gov/files/company_tickers_exchange.json", "sec_identity")
    data = json_body(artifact)
    fields = data["fields"]
    rows = [dict(zip(fields, values, strict=True)) for values in data["data"]]
    matches = [r for r in rows if r["ticker"].upper().replace(".", "-") == symbol.replace(".", "-")]
    if len(matches) != 1:
        raise ValueError(
            "no unique current SEC-listed identity; historical/delisted mapping requires evidence"
        )
    row = matches[0]
    if row.get("exchange") not in {"Nasdaq", "NYSE", "CBOE", "NYSE American", "NYSE Arca"}:
        raise ValueError("current identity is not on a supported US exchange")
    return {
        "symbol": symbol,
        "sec_ticker": row["ticker"],
        "cik": str(row["cik"]).zfill(10),
        "name": row["name"],
        "exchange": row["exchange"],
        "artifact_id": artifact.id,
        "limitation": "Current SEC identity only. Historical symbol/share-class continuity requires explicit review; no historical sector inferred.",
    }


def sec_filings(client, identity, start, end, coverage_start, coverage_end, limit):
    cik, symbol = identity["cik"], identity["symbol"]
    metadata = client.get(
        f"https://data.sec.gov/submissions/CIK{cik}.json",
        "sec_inventory",
        metadata={"symbol": symbol},
    )
    inventory = json_body(metadata)
    tables = [inventory["filings"]["recent"]]
    older = [
        f
        for f in inventory["filings"]["files"]
        if f["filingFrom"] <= end.isoformat() and f["filingTo"] >= start.isoformat()
    ]
    if len(older) > 20:
        raise ValueError("too many historical inventory partitions; shorten the request")
    for item in older:
        if not re.fullmatch(r"CIK\d{10}-submissions-\d{3}\.json", item["name"]):
            raise ValueError("invalid SEC inventory filename")
        tables.append(
            json_body(
                client.get(
                    "https://data.sec.gov/submissions/" + item["name"],
                    "sec_inventory",
                    metadata={"symbol": symbol},
                )
            )
        )
    records = {}
    for table in tables:
        for i, form in enumerate(table["form"]):
            if (
                form not in {"8-K", "8-K/A"}
                or not start.isoformat() <= table["filingDate"][i] <= end.isoformat()
            ):
                continue
            accession = table["accessionNumber"][i]
            if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
                raise ValueError("invalid SEC accession")
            row = {
                k: table[k][i]
                for k in [
                    "accessionNumber",
                    "acceptanceDateTime",
                    "filingDate",
                    "primaryDocument",
                    "items",
                    "form",
                ]
            }
            if accession in records and records[accession] != row:
                raise ValueError("conflicting duplicate SEC accession")
            records[accession] = row
    if len(records) > limit:
        raise ValueError(
            f"SEC inventory has {len(records)} filings, exceeding requested {limit}; increase the document limit or shorten dates"
        )
    events, documents = [], []
    for accession, row in sorted(records.items()):
        accepted = datetime.fromisoformat(row["acceptanceDateTime"].replace("Z", "+00:00"))
        if accepted.tzinfo is None:
            raise ValueError("SEC acceptance timestamp lacks an explicit timezone")
        next_day = accepted.astimezone(NY).date() + timedelta(days=1)
        available = session_times(sessions(next_day, next_day + timedelta(days=14))[0])[1]
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{accession}.txt"
        artifact = client.get(
            url,
            "sec_submission",
            metadata={
                "symbol": symbol,
                "cik": cik,
                "accession": accession,
                "accepted_at": accepted.isoformat(),
                "available_at": available.isoformat(),
            },
        )
        raw = artifact.body.decode("utf-8", "replace")
        header = raw.split("</SEC-HEADER>", 1)[0]
        found = re.search(r"<ACCEPTANCE-DATETIME>(\d{14})", header)
        if not found or datetime.strptime(found[1], "%Y%m%d%H%M%S").replace(tzinfo=NY) != accepted:
            raise ValueError("SEC submission acceptance timestamp disagrees with inventory")
        if not re.search(r"ACCESSION NUMBER:\s*" + re.escape(accession), header):
            raise ValueError("SEC submission accession mismatch")
        actual_cik = re.search(r"CENTRAL INDEX KEY:\s*(\d+)", header)
        if not actual_cik or int(actual_cik[1]) != int(cik):
            raise ValueError("SEC submission issuer mismatch")
        from app.onboarding.evidence import plain_text

        primary = None
        for body in re.findall(r"<DOCUMENT>(.*?)</DOCUMENT>", raw, re.S):
            filename = re.search(r"<FILENAME>([^\r\n]+)", body)
            if filename and filename[1].strip().lower() == row["primaryDocument"].lower():
                form = re.search(r"<TYPE>([^\r\n]+)", body)
                if not form or form[1].strip() != row["form"]:
                    raise ValueError("SEC primary-document form disagrees with inventory")
                primary = plain_text(body.encode())
        if primary is None:
            raise ValueError("primary filing is absent from retained SEC submission")
        items = [i.strip() for i in row["items"].split(",") if i.strip()]
        if any(
            not re.fullmatch(r"\d\.\d\d", i)
            or not re.search(
                r"\bItem\s*" + re.escape(i).replace(r"\.", r"\s*\.\s*") + r"\b", primary, re.I
            )
            for i in items
        ):
            raise ValueError("SEC item metadata disagrees with primary-document headings")
        documents.append(
            {
                "accession": accession,
                "form": row["form"],
                "items": items,
                "artifact_id": artifact.id,
                "available_at": available.isoformat(),
            }
        )
        if not coverage_start <= available <= coverage_end:
            continue
        events.append(
            {
                "event_id": "sec-" + accession,
                "published_at": available.isoformat(),
                "available_at": available.isoformat(),
                "category": "sec_8k_amendment" if row["form"] == "8-K/A" else "sec_8k",
                "tags": ["sec_item_" + i.replace(".", "_") for i in items],
                "symbols": [symbol],
                "title": f"{symbol} {row['form']} {accession}",
                "source_url": url,
                "original_content_hash": artifact.content_hash,
                "derivation": "Literal filing presence and item headings. Both clocks modeled at next exchange session close after acceptance; exact first-public unavailable. Amendments remain separate additive events.",
                "access": "public",
            }
        )
    from app.market_data.strategy_inputs import StrategyInput

    source = StrategyInput(
        kind="events",
        name=f"{symbol} SEC filing candidate {start}–{end}",
        source="SEC retained primary submissions",
        source_url="https://www.sec.gov/search-filings/edgar-application-programming-interfaces",
        availability_policy="Publication and availability are conservative research proxies at the next exchange session CLOSE after acceptance. Exact historical first-public time is unavailable. Only 8-K/8-K/A filing presence and literal item tags; amendments additive, no sentiment or historical sector inference. Coverage uses New York boundaries.",
        coverage_start=coverage_start,
        coverage_end=coverage_end,
        symbols=[symbol],
        stream_id="SEC_FILINGS",
        events=events,
        source_hashes=sorted({e["original_content_hash"] for e in events}),
    )
    return source, documents


def alpaca_actions(client, symbols, start, end):
    from decimal import Decimal

    params = {
        "symbols": ",".join(symbols),
        "types": "cash_dividend,forward_split,reverse_split",
        "start": (start - timedelta(days=90)).isoformat(),
        "end": (end + timedelta(days=90)).isoformat(),
        "limit": 1000,
        "sort": "asc",
    }
    rows = []
    for _ in range(10):
        artifact = client.get(
            "https://data.alpaca.markets/v1/corporate-actions", "corporate_actions", params=params
        )
        payload = json.loads(artifact.body, parse_float=Decimal)
        for kind, values in payload.get("corporate_actions", {}).items():
            for row in values:
                if (
                    row.get("symbol") not in symbols
                    or not start.isoformat() <= row.get("ex_date", "") <= end.isoformat()
                ):
                    continue
                if kind not in {"cash_dividends", "forward_splits", "reverse_splits"}:
                    raise ValueError("unsupported corporate action kind")
                rows.append(
                    json.loads(
                        json.dumps(
                            {"kind": kind, "record": row, "artifact_id": artifact.id}, default=str
                        )
                    )
                )
        token = payload.get("next_page_token")
        if not token:
            keys = [
                (
                    r["record"]["symbol"],
                    r["record"]["ex_date"],
                    "dividend" if r["kind"] == "cash_dividends" else "split",
                )
                for r in rows
            ]
            if len(keys) != len(set(keys)):
                raise ValueError(
                    "duplicate corporate-action candidates require source reconciliation"
                )
            return rows
        params["page_token"] = token
    raise ValueError("corporate-action pagination limit exhausted")
