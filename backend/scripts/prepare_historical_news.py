"""Verify month receipts and assemble unreviewed yearly news/analyst candidates."""

import argparse
import json
from collections import Counter
from pathlib import Path

from app.market_data.strategy_inputs import StrategyInput
from app.retail.analyst_news import extract_action
from app.retail.backfill_receipts import checked_partition


def prepare(root: Path, output: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError("use a new output directory; prior candidates are immutable")
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "years": [],
        "quarantined": [],
        "excluded_older_versions": 0,
        "analyst_counts": Counter(),
    }
    for year in range(2018, 2026):
        inputs, analysts, proofs = [], [], []
        for month in range(1, 13):
            record, path = checked_partition(root / f"{year}-{month:02}")
            source = StrategyInput.model_validate_json(path.read_bytes())
            if source.reviewed or source.complete:
                raise ValueError("raw acquisition must remain unreviewed")
            inputs.append(source)
            report["quarantined"].extend(
                {"month": f"{year}-{month:02}", **q} for q in record.get("quarantined", [])
            )
            report["excluded_older_versions"] += (
                len(record.get("excluded_older_versions", []))
                if "excluded_older_versions" in record
                else record["older_publications_updated_in_window_excluded"]
            )
            for event in source.events:
                action, proof = extract_action(
                    event, {"AAPL": ("Apple", "AAPL"), "MSFT": ("Microsoft", "MSFT")}
                )
                proofs.append(proof)
                report["analyst_counts"][proof["status"]] += 1
                if action:
                    analysts.append(action)
        data = inputs[0].model_dump(mode="json")
        data.update(
            name=f"UNREVIEWED AAPL MSFT news {year} current-version publication cohorts",
            coverage_end=inputs[-1].coverage_end.isoformat(),
            events=[e.model_dump(mode="json") for s in inputs for e in s.events],
            source_hashes=[h for s in inputs for h in s.source_hashes],
            category_catalog=[],
        )
        news = StrategyInput.model_validate(data)
        (output / f"news-{year}-unreviewed.json").write_text(news.model_dump_json(indent=2))
        data.update(
            name=f"UNREVIEWED AAPL MSFT news-derived analyst actions {year}",
            source="retained-alpaca-news-literal-analyst",
            stream_id="NEWS_ANALYST_ACTIONS",
            events=[e.model_dump(mode="json") for e in analysts],
            category_catalog=[],
            availability_policy="Literal single-issuer news headlines, NOT a comprehensive analyst feed. Current article-version availability preserved. Original report delivery unknown. No consensus, inferred prior rating, fabricated target or automatically reviewed coverage.",
        )
        analyst = StrategyInput.model_validate(data)
        (output / f"analyst-{year}-unreviewed.json").write_text(analyst.model_dump_json(indent=2))
        (output / f"analyst-{year}-proofs.json").write_text(json.dumps(proofs, indent=2))
        report["years"].append(
            {
                "year": year,
                "news": len(news.events),
                "analyst": len(analyst.events),
                "raw_pages_verified": len(news.source_hashes),
            }
        )
    report["analyst_counts"] = dict(report["analyst_counts"])
    (output / "report.json").write_text(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.source_dir, args.output)
    print(json.dumps({k: v for k, v in report.items() if k != "quarantined"}))
    print("quarantined", len(report["quarantined"]))


if __name__ == "__main__":
    main()
