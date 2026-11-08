"""Prepare unreviewed literal analyst actions from retained news JSON; no network calls."""

import argparse
import json
from collections import Counter
from pathlib import Path

from app.market_data.strategy_inputs import StrategyInput
from app.retail.analyst_news import VERSION, extract_action
from app.schemas.domain import canonical_hash


def prepare(source_dir: Path, output: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError("use a new output directory; prior evidence is not overwritten")
    output.mkdir(parents=True, exist_ok=True)
    report = {"policy": VERSION, "sources": [], "proofs": [], "counts": Counter()}
    for path in sorted(source_dir.glob("news-*-unreviewed.json")):
        source = StrategyInput.model_validate_json(path.read_bytes())
        events = []
        for article in source.events:
            event, proof = extract_action(
                article, {"AAPL": ("Apple", "AAPL"), "MSFT": ("Microsoft", "MSFT")}
            )
            report["proofs"].append(proof)
            report["counts"][proof["status"]] += 1
            if event is not None:
                events.append(event)
        if not events:
            continue
        payload = source.model_dump(mode="json")
        payload.update(
            name="SAMPLE news-derived analyst actions " + path.name[5:15],
            source="retained-alpaca-news-literal-analyst",
            stream_id="NEWS_ANALYST_ACTIONS",
            availability_policy="Sampled news-derived individual analyst announcements; not a comprehensive ratings feed. Literal supported single-issuer headlines only; current article version clocks preserved. USD targets interpreted only for reviewed US Apple/Microsoft feed context. Missing prior values stay null; original analyst report time is unknown. No automatic source approval.",
            events=[e.model_dump(mode="json") for e in events],
            category_catalog=sorted(
                {e.category for e in events} | {tag for e in events for tag in e.tags}
            ),
            reviewed=False,
            complete=False,
            parent_id=None,
            parent_hash=None,
            review_note="",
        )
        candidate = StrategyInput.model_validate(payload)
        filename = "analyst-" + path.name[5:]
        (output / filename).write_text(candidate.model_dump_json(indent=2))
        report["sources"].append(
            {
                "file": filename,
                "article_source_file": path.name,
                "article_source_hash": canonical_hash(source.model_dump(mode="json")),
                "events": len(events),
                "candidate_hash": canonical_hash(candidate.model_dump(mode="json")),
            }
        )
    report["counts"] = dict(report["counts"])
    (output / "report.json").write_text(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.source_dir, args.output)
    print(json.dumps({"counts": report["counts"], "source_candidates": len(report["sources"])}))


if __name__ == "__main__":
    main()
