"""Offline snapshot audit and bounded staging. Optional duckdb reader is not an app dependency."""

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

from app.congress.evidence import HOUSE, index_rows
from app.retail.congress_snapshot import stage_trade, verify_shard


def qualify(root: Path, official: Path, output: Path, revision: str) -> dict:
    import duckdb

    if output.exists() and any(output.iterdir()):
        raise ValueError("use a new output directory")
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((root / "snapshot.json").read_text())
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("pin a full dataset commit")
    db = duckdb.connect(
        config={
            "threads": 1,
            "memory_limit": "512MB",
            "autoinstall_known_extensions": "false",
            "autoload_known_extensions": "false",
        }
    )
    counts = {}
    verified = 0
    try:
        for table in ("political_filings", "political_trades", "political_trade_events"):
            spec = manifest["tables"][table]
            files = []
            for part in spec["manifests"]:
                for shard in part["files"]:
                    path = shard["publicPath"]
                    if not (root / path).resolve().is_relative_to(root.resolve()):
                        raise ValueError("snapshot shard escapes its root")
                    verify_shard(path, (root / path).read_bytes(), shard)
                    files.append(str(root / path))
                    verified += 1
            db.from_parquet(files).create_view(table)
            count = db.sql("select count(*) from " + table).fetchone()[0]
            if count != spec["rows"]:
                raise ValueError("snapshot table count differs from manifest")
            counts[table] = count

        def rows(query, parameters=None):
            result = db.execute(query, parameters or [])
            return [
                dict(zip([column[0] for column in result.description], row, strict=True))
                for row in result.fetchall()
            ]

        filings = rows("select * from political_filings")
        by_doc = {(r["chamber"], r["docId"]): r for r in filings}
        if len(by_doc) != len(filings):
            raise ValueError("duplicate snapshot filing identity")
        by_index_year = defaultdict(set)
        for row in filings:
            if row["chamber"] == "house":
                match = re.fullmatch(
                    r"https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/(\d{4})/(\d{7,8})\.pdf",
                    row["sourceUrl"],
                )
                if match:
                    by_index_year[int(match[1])].add(row["docId"])
        comparisons = []
        for archive in sorted(official.glob("*FD.zip")):
            year = int(archive.name[:4])
            indexed = index_rows(
                SimpleNamespace(
                    body=archive.read_bytes(),
                    source_url=f"{HOUSE}/public_disc/financial-pdfs/{year}FD.zip",
                    metadata_json={"year": year, "http_status": 200},
                )
            )
            expected = {r["DocID"] for r in indexed if r["FilingType"] == "P"}
            observed = by_index_year[year]
            comparisons.append(
                {
                    "index_year": year,
                    "official_ptrs": len(expected),
                    "snapshot_ptrs": len(observed),
                    "missing_from_snapshot": sorted(expected - observed),
                    "snapshot_not_in_current_index": sorted(observed - expected),
                    "official_zip_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                }
            )
        selected = rows(
            "select * from political_trades where chamber='house' and docId in ('20020515','20020561') and printedTicker='AAPL' order by filingDate,rowIndex"
        )
        for method in ("html", "paper"):
            selected += rows(
                "select t.* from political_trades t join political_filings f using(chamber,docId) where t.chamber='senate' and f.parseMethod=? and t.filingDate between '2018-01-01' and '2025-12-31' and t.printedTicker in ('AAPL','MSFT') order by t.filingDate,t.docId,t.rowIndex limit 2",
                [method],
            )
        candidates = [stage_trade(r, by_doc[r["chamber"], r["docId"]]) for r in selected]
        reconciliations = []
        for row in selected:
            if row["chamber"] != "house":
                continue
            raw = (official / (row["docId"] + ".pdf")).read_bytes()
            if hashlib.sha256(raw).hexdigest() != row["rawSha256"]:
                raise ValueError("bounded Pelosi original PDF does not match snapshot receipt")
            if (
                row["owner"] != "spouse"
                or str(row["transactionDate"]) != "2022-01-21"
                or row["amountLow"] != 1000001
                or row["amountHigh"] != 5000000
            ):
                raise ValueError(
                    "bounded Pelosi transaction facts disagree with earlier source review"
                )
            if not re.search(r"[Ee]xercised\s+100\s+call options", row.get("comment") or ""):
                raise ValueError("bounded Pelosi option exercise text missing")
            reconciliations.append(
                {
                    "doc_id": row["docId"],
                    "exact_original_pdf_hash_matches": True,
                    "owner_date_amount_ticker_match": True,
                    "producer_action": row["action"],
                    "reviewed_action": "option_exercise",
                    "classification_requires_review": True,
                }
            )
        aggregate = rows(
            "select chamber,year(filingDate) as filing_year,count(*) as filings,sum(case when extractionStatus!='ok' then 1 else 0 end) as failed from political_filings group by all order by 1,2"
        )
        report = {
            "dataset_revision": revision,
            "verified_shards": verified,
            "table_counts": counts,
            "filings_by_chamber_year": aggregate,
            "official_index_comparisons": comparisons,
            "staged_rows": candidates,
            "pelosi_source_reconciliation": reconciliations,
            "strategy_eligible": False,
            "limitations": [
                "Producer filing-day clock is not verified public availability",
                "Senate sample originals not independently accessible here",
                "Current index differences require identity-level review",
                "No automatic duplicate/amendment or instrument approval",
            ],
        }
        (output / "report.json").write_text(json.dumps(report, indent=2, default=str))
        return report
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--official-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    report = qualify(args.snapshot_dir, args.official_dir, args.output, args.revision)
    print(
        json.dumps(
            {
                "verified_shards": report["verified_shards"],
                "table_counts": report["table_counts"],
                "staged_rows": len(report["staged_rows"]),
                "pelosi_source_reconciliation": report["pelosi_source_reconciliation"],
                "strategy_eligible": False,
            }
        )
    )


if __name__ == "__main__":
    main()
