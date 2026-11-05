"""Fetch unreviewed ETF history and retain new immutable input revisions, never run a backtest."""

import argparse
import json
from datetime import date
from pathlib import Path

import httpx

from app.market_data.providers import AlpacaProvider
from app.market_data.validation import validate_dataset
from app.schemas.domain import DatasetInput


def prepare(output: Path, api_url: str | None = None) -> list[dict]:
    output.mkdir(parents=True, exist_ok=False)
    chunks = [
        AlpacaProvider().fetch(["SPY", "QQQ", "SMH", "XLE"], start, end, feed="sip")
        for start, end in [
            (date(2016, 1, 1), date(2020, 12, 31)),
            (date(2021, 1, 1), date(2025, 12, 31)),
        ]
    ]
    reports = []
    for symbol in ("SPY", "QQQ", "SMH", "XLE"):
        data = DatasetInput(
            name=f"Alpaca SIP {symbol} 2016–2025 — action/FX review pending",
            provider="alpaca-sip",
            decision_time=chunks[0].decision_time,
            availability_policy=chunks[0].availability_policy,
            bars=[bar for chunk in chunks for bar in chunk.bars if bar.symbol == symbol],
        )
        coverage = validate_dataset(data)
        if symbol not in coverage or coverage[symbol]["missing_sessions"]:
            raise ValueError(f"Incomplete real equity coverage for {symbol}")
        payload = data.model_dump(mode="json")
        (output / f"{symbol}-unreviewed.json").write_text(json.dumps(payload))
        report = {
            "symbol": symbol,
            "coverage": coverage,
            "corporate_actions_reviewed": False,
            "fx_observations": 0,
            "actions": 0,
        }
        if api_url:
            with httpx.Client(timeout=180) as client:
                response = client.post(
                    api_url.rstrip("/") + "/api/market-data/import", json=payload
                )
                if response.status_code != 201:
                    raise ValueError(f"Application import failed (HTTP {response.status_code})")
                report["dataset_id"] = response.json()["id"]
                report["content_hash"] = response.json()["content_hash"]
        reports.append(report)
        print(json.dumps(report), flush=True)
    (output / "report.json").write_text(json.dumps(reports, indent=2))
    return reports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--api-url", help="Optional local Trading Lab origin; never a data-provider URL"
    )
    args = parser.parse_args()
    prepare(args.output_dir, args.api_url)
