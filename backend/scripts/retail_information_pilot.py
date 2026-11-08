"""Bounded AAPL/MSFT source pilot. Run from backend: python -m scripts.retail_information_pilot --output DIR.

Writes private exact responses and UNREVIEWED candidates; never changes app databases.
This is a sampled qualification pilot, not a full-history collector or coverage approval.
"""

import argparse
import hashlib
import json
import re
import time
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

from app.core.config import settings
from app.market_data.platform_providers import NewsFetch, fetch_news, normalize_news
from app.market_data.strategy_inputs import StrategyInput
from app.onboarding.evidence import plain_text
from app.retail.qualification import audit_news, insider_event, inventory_rows
from app.schemas.domain import canonical_hash


class Evidence:
    def __init__(self, root, reuse=None):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.entries = []
        self.total = 0
        self.last_sec = 0.0
        self.reuse = reuse
        self.cached = json.loads((reuse / "responses.json").read_text()) if reuse else []

    def write(self, name, data):
        (self.root / name).write_text(json.dumps(data, indent=2, default=str))

    def capture(self, response):
        raw = response.content
        self.total += len(raw)
        if self.total > 256_000_000 or len(raw) > 20_000_000 or len(self.entries) >= 500:
            raise ValueError("pilot source budget reached")
        digest = hashlib.sha256(raw).hexdigest()
        path = f"response-{len(self.entries):04d}-{digest}.raw"
        (self.root / path).write_bytes(raw)
        self.entries.append(
            {
                "path": path,
                "source_url": str(response.request.url),
                "sha256": digest,
                "bytes": len(raw),
                "http_status": response.status_code,
                "retrieved_at": datetime.now(UTC).isoformat(),
                "content_type": response.headers.get("content-type"),
            }
        )
        self.write("responses.json", self.entries)

    def reuse_response(self, entry):
        name = entry["path"]
        if Path(name).name != name or not re.fullmatch(r"response-\d{4}-[a-f0-9]{64}\.raw", name):
            raise ValueError("unsafe retained evidence filename")
        raw = (self.reuse / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"] or entry["http_status"] != 200:
            raise ValueError("retained source replay hash/status mismatch")
        self.capture(
            httpx.Response(200, content=raw, request=httpx.Request("GET", entry["source_url"]))
        )
        self.entries[-1].update(
            reused_from=str(self.reuse / name),
            retrieved_at=entry["retrieved_at"],
            content_type=entry.get("content_type"),
        )
        self.write("responses.json", self.entries)
        return raw

    def news(self, request):
        matched = []
        for entry in self.cached:
            url = urlparse(entry["source_url"])
            query = parse_qs(url.query)
            if (
                url.netloc == "data.alpaca.markets"
                and url.path == "/v1beta1/news"
                and query.get("start") == [str(request.start)]
                and query.get("end") == [str(request.end + timedelta(days=1))]
                and query.get("symbols") == [",".join(request.symbols)]
            ):
                matched.append(entry)
        if matched:
            raw = [self.reuse_response(entry) for entry in matched]
            pages = [json.loads(value, parse_float=Decimal) for value in raw]
            if pages[-1].get("next_page_token"):
                raise ValueError("cached news pages incomplete")
            return normalize_news(
                request, pages, [hashlib.sha256(value).hexdigest() for value in raw]
            )
        return fetch_news(request, capture=self.capture)

    def sec(self, url):
        if not url.startswith(("https://data.sec.gov/", "https://www.sec.gov/")):
            raise ValueError("only constructed SEC URLs allowed")
        for entry in self.cached:
            if entry["source_url"] == url and entry["http_status"] == 200:
                return self.reuse_response(entry)
        contact = settings().data_source_contact_email
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", contact):
            raise ValueError("DATA_SOURCE_CONTACT_EMAIL is required")
        remaining = 1.1 - (time.monotonic() - self.last_sec)
        if remaining > 0:
            time.sleep(remaining)
        self.last_sec = time.monotonic()
        with httpx.Client(timeout=45, follow_redirects=False) as client:
            with client.stream(
                "GET",
                url,
                headers={
                    "User-Agent": "TradingLabRetailPilot/1.0 " + contact,
                    "Accept-Encoding": "identity",
                },
            ) as response:
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > 20_000_000:
                        raise ValueError("SEC response exceeds pilot bound")
                    chunks.append(chunk)
                raw = b"".join(chunks)
                retained = httpx.Response(
                    response.status_code,
                    content=raw,
                    # iter_bytes already decoded HTTP content encoding.
                    headers={
                        "content-type": response.headers.get(
                            "content-type", "application/octet-stream"
                        )
                    },
                    request=response.request,
                )
                self.capture(retained)
                if response.status_code != 200:
                    raise ValueError(f"SEC HTTP {response.status_code}; no substitute or bypass")
                return raw


def collect(output, reuse=None):
    evidence = Evidence(output, reuse)
    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "symbols": ["AAPL", "MSFT"],
        "scope": "Sample windows in each year2018–2025 plus a recent completed week; not continuous historical coverage",
        "news": [],
        "sec": [],
        "blocked": [],
        "strategy_eligible": False,
    }
    evidence.write("report.json", report)
    windows = [(date(year, 7, 25), date(year, 7, 31)) for year in range(2018, 2026)]
    windows.append((date(2026, 11, 2), date(2026, 11, 6)))
    rules = [
        {"tag": "retail.earnings_mention", "any_terms": ["earnings", "quarterly results"]},
        {"tag": "retail.analyst_mention", "any_terms": ["price target", "downgrade", "upgrade"]},
        {"tag": "retail.insider_mention", "any_terms": ["insider", "form 4"]},
        {
            "tag": "retail.congress_mention",
            "any_terms": ["pelosi", "senator", "congressional trading"],
        },
    ]
    for start, end in windows:
        first = len(evidence.entries)
        request = NewsFetch(
            symbols=report["symbols"],
            start=start,
            end=end,
            keyword_tags=rules,
            access="subscription",
        )
        try:
            source = evidence.news(request)
            raw = [(output / r["path"]).read_bytes() for r in evidence.entries[first:]]
            audit = audit_news(request, raw, source)
            file = f"news-{start}-unreviewed.json"
            evidence.write(file, source.model_dump(mode="json"))
            report["news"].append({**audit, "candidate_file": file})
        except (ValueError, httpx.HTTPError) as exc:
            report["blocked"].append(
                {"source": "alpaca-news", "start": str(start), "error": str(exc)}
            )
            evidence.write("report.json", report)
            # Avoid retries/continued source access after entitlement/rate-limit denial.
            if "403" in str(exc) or "429" in str(exc):
                break
        evidence.write("report.json", report)

    for symbol, cik in [("AAPL", "0000320193"), ("MSFT", "0000789019")]:
        try:
            inventory = json.loads(evidence.sec(f"https://data.sec.gov/submissions/CIK{cik}.json"))
            rows = inventory_rows(inventory["filings"]["recent"])
            for part in inventory["filings"]["files"]:
                if part["filingTo"] < "2018-01-01" or part["filingFrom"] > "2026-12-31":
                    continue
                if not re.fullmatch(r"CIK\d{10}-submissions-\d{3}\.json", part["name"]):
                    raise ValueError("invalid SEC inventory partition")
                rows += inventory_rows(
                    json.loads(evidence.sec("https://data.sec.gov/submissions/" + part["name"]))
                )
            identities = {}
            for row in rows:
                accession = row["accessionNumber"]
                if accession in identities and identities[accession] != row:
                    raise ValueError("conflicting SEC inventory accession")
                identities[accession] = row
            rows = sorted(
                identities.values(), key=lambda r: (r["filingDate"], r["accessionNumber"])
            )
            evidence.write(f"sec-{symbol}-inventory.json", rows)
            chosen = []
            for year in range(2018, 2027):
                cohort = [r for r in rows if r["filingDate"].startswith(str(year))]
                chosen += [r for r in cohort if r["form"] == "4"][:2]
                chosen += [r for r in cohort if r["form"] == "4/A"][:1]
                # Earnings presence/exhibits are checked without inventing EPS or surprise.
                chosen += [
                    r for r in cohort if r["form"] == "8-K" and "2.02" in str(r.get("items", ""))
                ][:1]
            events = []
            for row in chosen:
                accession = row["accessionNumber"]
                if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession):
                    raise ValueError("invalid SEC accession")
                url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/{accession}.txt"
                raw = evidence.sec(url)
                if row["form"] in {"4", "4/A"}:
                    event, summary = insider_event(raw, row, symbol, cik, url)
                    events.append(event)
                    report["sec"].append(
                        {
                            "symbol": symbol,
                            "source_url": url,
                            "sha256": hashlib.sha256(raw).hexdigest(),
                            **summary,
                        }
                    )
                else:
                    text = raw.decode("utf-8", "replace")
                    header = text.split("</SEC-HEADER>", 1)[0]
                    if not re.search(r"ACCESSION NUMBER:\s*" + re.escape(accession), header):
                        raise ValueError("SEC8-K accession mismatch")
                    exhibits = []
                    for doc in re.findall(r"<DOCUMENT>(.*?)</DOCUMENT>", text, re.S):
                        form = re.search(r"<TYPE>([^\r\n]+)", doc)
                        if form and form[1].strip().startswith("EX-99"):
                            content = plain_text(doc.encode())
                            exhibits.append(
                                {
                                    "type": form[1].strip(),
                                    "text_hash": hashlib.sha256(content.encode()).hexdigest(),
                                    "earnings_terms_present": bool(
                                        re.search(
                                            r"\b(earnings|quarterly results|financial results)\b",
                                            content,
                                            re.I,
                                        )
                                    ),
                                }
                            )
                    report["sec"].append(
                        {
                            "symbol": symbol,
                            "accession": accession,
                            "form": "8-K",
                            "source_url": url,
                            "sha256": hashlib.sha256(raw).hexdigest(),
                            "exhibits": exhibits,
                            "earnings_metrics_normalized": False,
                        }
                    )
                evidence.write("report.json", report)
            if events:
                source = StrategyInput(
                    kind="events",
                    name=f"{symbol} SAMPLE SEC insider filings2018–2026 UNREVIEWED",
                    source="sec-form4-sample",
                    source_url="https://www.sec.gov/",
                    availability_policy="SAMPLED filing presence, NOT complete coverage. Original SEC header cross-checked with inventory. Assumed next-session-close availability. Amendments retained separately; lineage unresolved; no holdings or investment intent inferred.",
                    coverage_start=datetime(2018, 1, 1, tzinfo=UTC),
                    coverage_end=datetime(2027, 1, 1, tzinfo=UTC),
                    symbols=[symbol],
                    stream_id="INSIDER_FILINGS",
                    events=events,
                    source_hashes=[e.original_content_hash for e in events],
                )
                evidence.write(
                    f"sec-{symbol}-insider-sample-unreviewed.json", source.model_dump(mode="json")
                )
        except (ValueError, httpx.HTTPError, KeyError) as exc:
            report["blocked"].append({"source": "sec", "symbol": symbol, "error": str(exc)})
            if "403" in str(exc) or "429" in str(exc):
                break
    report["completed_at"] = datetime.now(UTC).isoformat()
    report["responses"] = len(evidence.entries)
    report["reused_responses"] = sum("reused_from" in row for row in evidence.entries)
    report["bytes"] = evidence.total
    report["analyst_ratings"] = {
        "structured_feed_configured": bool(settings().benzinga_api_key.get_secret_value()),
        "status": "News mentions only; no individual rating feed acquired or consensus substituted.",
    }
    report["congress"] = {
        "quiver_key_used": False,
        "status": "Paid API not configured; no aggregator history acquired.",
    }
    report["report_hash"] = canonical_hash(report)
    evidence.write("report.json", report)
    print(
        json.dumps({k: report[k] for k in ["responses", "bytes", "blocked", "strategy_eligible"]})
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--reuse-evidence",
        type=Path,
        help="Replay exact hash-checked earlier responses; retain provenance and fetch only missing SEC documents",
    )
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("output must be new/empty; retained evidence is never overwritten")
    collect(args.output, args.reuse_evidence)


if __name__ == "__main__":
    main()
