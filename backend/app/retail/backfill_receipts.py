"""Verify retained acquisition bytes before resuming or preparing derived inputs."""

import hashlib
import json
from pathlib import Path


def checked_partition(folder: Path) -> tuple[dict, Path]:
    record = json.loads((folder / "audit.json").read_text())
    candidate = folder / "news-unreviewed.json"
    if hashlib.sha256(candidate.read_bytes()).hexdigest() != record["candidate_file_sha256"]:
        raise ValueError("completed candidate changed on disk")
    # The acquisition path may come from a container mount. Only its local basename
    # is used; a receipt cannot direct reads outside this partition.
    attempt = folder / Path(record["attempt"]).name
    receipts = json.loads((attempt / "responses.json").read_text())
    hashes = []
    for receipt in receipts:
        name = receipt["path"]
        if Path(name).name != name or name in {"", ".", ".."}:
            raise ValueError("unsafe raw receipt path")
        raw = (attempt / name).read_bytes()
        if len(raw) != receipt["bytes"] or hashlib.sha256(raw).hexdigest() != receipt["sha256"]:
            raise ValueError("retained raw response changed on disk")
        if receipt["http_status"] != 200:
            raise ValueError("incomplete acquisition receipt")
        hashes.append(receipt["sha256"])
    payload = json.loads(candidate.read_text())
    if not hashes or payload["source_hashes"] != hashes:
        raise ValueError("candidate raw-response lineage mismatch")
    return record, candidate
