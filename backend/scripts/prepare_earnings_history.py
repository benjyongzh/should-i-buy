"""Normalize explicitly selected original SEC exhibits and paired issuer receipts."""

import argparse
import hashlib
import json
from pathlib import Path

from app.retail.earnings_history import earnings_source, quarterly_pair


def prepare(inventory: Path, sec_root: Path, issuer_dir: Path, output: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError("use a new output directory; prior evidence is immutable")
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((issuer_dir / "manifest.json").read_text())
    records, blocked = [], []
    for row in json.loads(inventory.read_text()):
        try:
            matches = [m for m in manifest if m["accession"] == row["accession"]]
            if len(matches) != 1 or matches[0]["http_status"] != 200:
                raise ValueError("issuer acquisition missing or ambiguous")
            page = matches[0]
            for root, filename in [(issuer_dir, page["file"]), (sec_root, row["file"])]:
                if not (root / filename).resolve().is_relative_to(root.resolve()):
                    raise ValueError("unsafe retained evidence path")
            issuer, sec = (
                (issuer_dir / page["file"]).read_bytes(),
                (sec_root / row["file"]).read_bytes(),
            )
            if (
                hashlib.sha256(issuer).hexdigest() != page["sha256"]
                or hashlib.sha256(sec).hexdigest() != row["sha256"]
            ):
                raise ValueError("retained source hash mismatch")
            records.append(
                quarterly_pair(
                    sec,
                    issuer,
                    row["symbol"],
                    row["accession"],
                    row["exhibit_filename"],
                    page["url"],
                    row["url"],
                )
            )
        except (ValueError, OSError) as exc:
            blocked.append(
                {"symbol": row["symbol"], "accession": row["accession"], "error": str(exc)}
            )
    report = {"records": records, "blocked": blocked}
    (output / "report.json").write_text(json.dumps(report, indent=2))
    if not blocked:
        source = earnings_source(records)
        (output / "earnings-unreviewed.json").write_text(source.model_dump_json(indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("inventory", "sec-root", "issuer-dir", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.inventory, args.sec_root, args.issuer_dir, args.output)
    print(json.dumps({"paired": len(result["records"]), "blocked": result["blocked"]}))


if __name__ == "__main__":
    main()
