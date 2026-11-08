"""Resumable month-partitioned raw news backfill. Acquisition is never approval."""

import argparse
import calendar
import hashlib
import json
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from app.market_data.platform_providers import NewsFetch, alpaca_pages
from app.retail.backfill_receipts import checked_partition
from app.retail.news_backfill import normalize_partition
from scripts.retail_information_pilot import Evidence


def collect(root: Path, start_year: int, end_year: int) -> dict:
    if not 2018 <= start_year <= end_year <= 2025:
        raise ValueError("this bounded pilot accepts2018–2025 only")
    root.mkdir(parents=True, exist_ok=True)
    request = {
        "start_year": start_year,
        "end_year": end_year,
        "symbols": ["AAPL", "MSFT"],
        "policy": "current-version publication cohorts; not original complete news history",
    }
    identity = root / "request.json"
    if identity.exists() and json.loads(identity.read_text()) != request:
        raise ValueError("backfill request is immutable; use a new directory")
    if not identity.exists():
        identity.write_text(json.dumps(request, indent=2))
    progress = {"request": request, "partitions": [], "status": "running"}
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            start = date(year, month, 1)
            end = date(year, month, calendar.monthrange(year, month)[1])
            folder = root / str(start)[:7]
            done = folder / "audit.json"
            if done.exists():
                record, candidate = checked_partition(folder)
            else:
                # Keep failed attempts separately. Never replace retained raw bytes.
                attempt = folder / ("attempt-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f"))
                evidence = Evidence(attempt)
                body = NewsFetch(
                    symbols=request["symbols"],
                    start=start,
                    end=end,
                    access="subscription",
                    keyword_tags=[
                        {
                            "tag": "retail.analyst_mention",
                            "any_terms": ["upgrade", "downgrade", "price target"],
                        },
                        {
                            "tag": "retail.earnings_mention",
                            "any_terms": ["earnings", "quarterly results"],
                        },
                    ],
                )
                try:
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
                        capture=evidence.capture,
                    )
                    source, record = normalize_partition(body, pages, hashes)
                    candidate = folder / "news-unreviewed.json"
                    candidate.write_text(source.model_dump_json(indent=2))
                    record.update(
                        month=str(start)[:7],
                        attempt=str(attempt),
                        candidate_file_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
                    )
                    done.write_text(json.dumps(record, indent=2))
                except ValueError as exc:
                    progress.update(status="blocked", blocked_month=str(start)[:7], error=str(exc))
                    (root / "progress.json").write_text(json.dumps(progress, indent=2))
                    raise
            progress["partitions"].append(record)
            (root / "progress.json").write_text(json.dumps(progress, indent=2))
            print(str(start)[:7], record["events"], flush=True)
            time.sleep(0.2)
    progress["status"] = "acquired_unreviewed"
    progress["total_events"] = sum(p["events"] for p in progress["partitions"])
    progress["original_vintages_certified"] = False
    (root / "progress.json").write_text(json.dumps(progress, indent=2))
    return progress


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start-year", type=int, default=2018)
    parser.add_argument("--end-year", type=int, default=2025)
    args = parser.parse_args()
    result = collect(args.output, args.start_year, args.end_year)
    print(
        json.dumps(
            {
                "status": result["status"],
                "partitions": len(result["partitions"]),
                "events": result["total_events"],
            }
        )
    )


if __name__ == "__main__":
    main()
