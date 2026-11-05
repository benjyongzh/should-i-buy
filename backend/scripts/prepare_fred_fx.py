"""Prepare, audit and retain real FX inputs; never imports or changes an app dataset."""

import argparse
import csv
import hashlib
import json
import os
import re
import time
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from html import unescape
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

from app.market_data.calendar import decision_timestamp, session_times, sessions
from app.market_data.view import fx_at
from app.schemas.domain import FXObservation

NY = ZoneInfo("America/New_York")
POLICY = (
    "ALFRED DEXSIUS initial-release values; observed noon New York; available midnight "
    "New York AFTER FRED realtime_start date (conservative date-only publication bound). "
    "Missing values omitted, never filled. Lagged reference FX, not executable quotes."
)
PARAMS = {
    "series_id": "DEXSIUS",
    "file_type": "json",
    "observation_start": "2017-12-01",
    "observation_end": "2022-12-31",
    "realtime_start": "1776-07-04",
    "realtime_end": "2023-01-31",
    "output_type": 4,
    "limit": 100000,
}


def normalize(rows: list[dict]) -> list[FXObservation]:
    output = []
    seen = set()
    for row in rows:
        observed = date.fromisoformat(row["date"])
        if observed in seen:
            raise ValueError("Duplicate FRED observation date")
        seen.add(observed)
        released = date.fromisoformat(row["realtime_start"])
        if released < observed:
            raise ValueError("FRED release precedes observation")
        if row["value"] == ".":
            continue
        output.append(
            FXObservation(
                observed_at=datetime.combine(observed, datetime.min.time(), NY).replace(hour=12),
                available_at=datetime.combine(
                    released + timedelta(days=1), datetime.min.time(), NY
                ),
                rate=row["value"],
            )
        )
    if not output:
        raise ValueError("FRED returned no numeric observations")
    return sorted(output, key=lambda r: (r.observed_at, r.available_at))


def archive_values(html: str, released: date) -> dict[date, str]:
    """Read only the explicitly dated weekly table, rejecting ambiguous layouts."""
    marker = re.search(r"Release Date:\s*([^<\n]+)", html)
    if not marker or datetime.strptime(marker[1].strip(), "%B %d, %Y").date() != released:
        raise ValueError("Fed archive release date mismatch")
    tables = [
        table
        for table in re.findall(r"<table\b[^>]*>(.*?)</table>", html, re.S | re.I)
        if "SINGAPORE" in table and "CURRENCY" in table
    ]
    if len(tables) != 1:
        raise ValueError("Fed weekly table missing or ambiguous")
    rows = []
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", tables[0], re.S | re.I):
        cells = re.findall(r"<t[hd]\b[^>]*>(.*?)</t[hd]>", row, re.S | re.I)
        rows.append([" ".join(unescape(re.sub(r"<[^>]+>", "", c)).split()) for c in cells])
    headers = next((r for r in rows if r[:2] == ["COUNTRY", "CURRENCY"]), [])
    singapore = next((r for r in rows if r[:2] == ["SINGAPORE", "DOLLAR"]), [])
    if len(headers) != 7 or len(singapore) != 7:
        raise ValueError("Fed Singapore table has unexpected columns")
    output = {}
    for label, value in zip(headers[2:], singapore[2:], strict=True):
        cleaned = label.replace(".", "").replace("Sept ", "Sep ")
        candidates = []
        for year in (released.year - 1, released.year):
            try:
                day = datetime.strptime(f"{cleaned} {year}", "%b %d %Y").date()
            except ValueError:
                continue
            if 0 < (released - day).days <= 14:
                candidates.append(day)
        if len(candidates) != 1:
            raise ValueError("Fed archive observation date ambiguous")
        if value != "ND":
            if not Decimal(value).is_finite() or Decimal(value) <= 0:
                raise ValueError("Fed archive has invalid rate")
        output[candidates[0]] = value
    return output


def audit_clocks(fx: list[FXObservation], start: date, end: date) -> dict:
    clocks = [
        clock
        for day in sessions(start, end)
        for clock in (*session_times(day), decision_timestamp(day, "20:30_America/New_York"))
    ]
    latest = []
    for clock in clocks:
        eligible = [r for r in fx if r.observed_at <= clock and r.available_at <= clock]
        if not eligible:
            raise ValueError("Missing historically available FX at a required clock")
        latest.append(max(eligible, key=lambda r: (r.observed_at, r.available_at)))
    ages = [
        (clock - row.observed_at).total_seconds() / 86400
        for clock, row in zip(clocks, latest, strict=True)
    ]
    failures = {}
    for limit in (7, 14):
        bad = []
        for clock in clocks:
            try:
                fx_at(fx, clock, limit)
            except ValueError:
                bad.append(clock.isoformat())
        failures[str(limit)] = {"count": len(bad), "first": bad[:3]}
    worst = max(range(len(ages)), key=ages.__getitem__)
    return {
        "start": str(start),
        "end": str(end),
        "clocks": len(clocks),
        "maximum_observation_age_days": ages[worst],
        "worst_clock": clocks[worst].isoformat(),
        "worst_observed_at": latest[worst].observed_at.isoformat(),
        "worst_available_at": latest[worst].available_at.isoformat(),
        "age_limit_failures": failures,
    }


def get(client: httpx.Client, url: str, params: dict | None = None) -> httpx.Response:
    try:
        response = client.get(url, params=params)
    except httpx.HTTPError:
        raise ValueError("Source connection failed; credentials and URL query suppressed") from None
    if response.status_code != 200:
        raise ValueError(f"Source HTTP {response.status_code}; response/query suppressed")
    return response


def prepare(output: Path, resume: bool = False) -> dict:
    key = os.environ.get("FRED_API_KEY", "").strip()
    if not key:
        raise ValueError("Set FRED_API_KEY in the preparation process environment")
    if (output / "report.json").exists():
        raise ValueError("Completed preparation is immutable; choose a new output directory")
    output.mkdir(parents=True, exist_ok=resume)
    raw_dir = output / "raw"
    raw_dir.mkdir(exist_ok=resume)
    rows = []
    sources = []
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        offset = 0
        for page in range(20):
            path = raw_dir / f"fred-page-{page}.json"
            raw = (
                path.read_bytes()
                if resume and path.exists()
                else get(
                    client,
                    "https://api.stlouisfed.org/fred/series/observations",
                    {**PARAMS, "offset": offset, "api_key": key},
                ).content
            )
            # API response JSON contains observations and metadata, not request credentials.
            if key.encode() in raw:
                raise ValueError("Refusing to retain response containing credential")
            payload = json.loads(raw)
            for field in (
                "observation_start",
                "observation_end",
                "realtime_start",
                "realtime_end",
                "output_type",
            ):
                if payload[field] != PARAMS[field]:
                    raise ValueError("Cached FRED query does not match preparation bounds")
            if payload["offset"] != offset:
                raise ValueError("FRED pagination offset mismatch")
            if not path.exists():
                path.write_bytes(raw)
            batch = payload["observations"]
            rows.extend(batch)
            offset += len(batch)
            sources.append(
                {
                    "file": str(path.relative_to(output)),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
            if offset >= payload["count"]:
                break
            if not batch:
                raise ValueError("FRED pagination stopped before declared count")
        else:
            raise ValueError("FRED pagination limit exceeded")
        fx = normalize(rows)
        releases = sorted({r["realtime_start"] for r in rows})
        mismatches = []
        unavailable = []
        archive_issues = []
        verified = 0
        for index, release in enumerate(releases):
            url = "https://www.federalreserve.gov/releases/h10/" + release.replace("-", "") + "/"
            path = raw_dir / f"h10-{release}.html"
            try:
                raw = path.read_bytes() if resume and path.exists() else get(client, url).content
            except ValueError as exc:
                if str(exc).startswith("Source HTTP 404;"):
                    unavailable.append({"release": release, "url": url, "status": 404})
                    time.sleep(0.3)
                    continue
                raise
            if not path.exists():
                path.write_bytes(raw)
            try:
                values = archive_values(raw.decode(), date.fromisoformat(release))
            except ValueError as exc:
                archive_issues.append(
                    {
                        "release": release,
                        "url": url,
                        "reason": str(exc),
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                )
                time.sleep(0.3)
                continue
            for row in (r for r in rows if r["realtime_start"] == release):
                archived = values.get(date.fromisoformat(row["date"]))
                match = (
                    archived == "ND"
                    if row["value"] == "."
                    else archived is not None
                    and archived != "ND"
                    and Decimal(archived) == Decimal(row["value"])
                )
                if match:
                    verified += 1
                else:
                    mismatches.append(
                        {
                            "date": row["date"],
                            "release": release,
                            "fred": row["value"],
                            "archive": archived,
                        }
                    )
            sources.append(
                {
                    "url": url,
                    "file": str(path.relative_to(output)),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
            if (index + 1) % 25 == 0:
                print(
                    json.dumps({"releases_checked": index + 1, "total": len(releases)}), flush=True
                )
            time.sleep(0.3)
    report = {
        "retrieved_at": datetime.now(UTC).isoformat(),
        "source": "ALFRED DEXSIUS output_type=4 + unrevised Fed H.10 archive reconciliation",
        "query_without_key": PARAMS,
        "availability_policy": POLICY,
        "rows": len(rows),
        "numeric_observations": len(fx),
        "missing_omitted": len(rows) - len(fx),
        "release_count": len(releases),
        "archive_matched_rows": verified,
        "archive_mismatches": mismatches,
        "archive_unavailable": unavailable,
        "archive_issues": archive_issues,
        "review_status": "prepared candidate; unresolved archive evidence"
        if mismatches or unavailable or archive_issues
        else "archive reconciliation passed; profile policy review required",
        "coverage": [
            audit_clocks(fx, date(2018, 1, 1), date(2022, 12, 31)),
            audit_clocks(fx, date(2019, 1, 1), date(2022, 12, 31)),
        ],
        "sources": sources,
    }
    path = output / "usd-sgd-candidate.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["observed_at", "available_at", "rate"])
        writer.writeheader()
        for row in fx:
            writer.writerow(
                {
                    "observed_at": row.observed_at.isoformat(),
                    "available_at": row.available_at.isoformat(),
                    "rate": str(row.rate),
                }
            )
    report["csv_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return {k: v for k, v in report.items() if k != "sources"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse original raw responses from an incomplete preparation",
    )
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.output_dir, args.resume), indent=2), flush=True)
    except (ValueError, httpx.HTTPError) as exc:
        # Never emit an HTTP exception representation containing a query-string API key.
        raise SystemExit(
            str(exc) if isinstance(exc, ValueError) else "Source request failed"
        ) from None
