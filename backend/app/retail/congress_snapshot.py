"""Third-party disclosure staging. Filing-date proxies never become public clocks."""

import hashlib
import re
from datetime import datetime
from decimal import Decimal


def verify_shard(path: str, body: bytes, expected: dict) -> None:
    if not re.fullmatch(
        r"data/political_(?:filings|trades|trade_events)/[A-Za-z0-9_.-]+\.parquet", path
    ):
        raise ValueError("invalid snapshot shard path")
    if len(body) != expected["size"] or hashlib.sha256(body).hexdigest() != expected["sha256"]:
        raise ValueError("snapshot shard size/hash mismatch")


def stage_trade(row: dict, filing: dict) -> dict:
    if (row["chamber"], row["docId"]) != (filing["chamber"], filing["docId"]):
        raise ValueError("snapshot trade/filing identity mismatch")
    if row["rawSha256"] != filing["rawSha256"]:
        raise ValueError("snapshot raw document hash mismatch")
    if filing["extractionStatus"] != "ok":
        raise ValueError("failed/unsupported filing cannot supply trade candidates")
    amounts = {}
    for field in ("amountLow", "amountHigh"):
        value = row.get(field)
        parsed = Decimal(str(value)) if value is not None else None
        if parsed is not None and (not parsed.is_finite() or parsed < 0):
            raise ValueError("invalid disclosure range")
        amounts[field] = str(parsed.normalize()) if parsed is not None else None
    if (
        amounts["amountLow"] is not None
        and amounts["amountHigh"] is not None
        and Decimal(amounts["amountLow"]) > Decimal(amounts["amountHigh"])
    ):
        raise ValueError("inverted disclosure range")
    assumed = row["availableAt"]
    if not isinstance(assumed, (str, datetime)):
        raise ValueError("invalid producer availability representation")
    return {
        "chamber": row["chamber"],
        "document_id": row["docId"],
        "row_index": row["rowIndex"],
        "source_url": row["sourceUrl"],
        "raw_document_hash": row["rawSha256"],
        "reported_transaction_date": str(row.get("transactionDate"))
        if row.get("transactionDate")
        else None,
        "filing_date": str(row["filingDate"]),
        "producer_assumed_available_at": str(assumed),
        "availability_source": row.get("availabilitySource"),
        "verified_public_at": None,
        "strategy_eligible": False,
        "owner": row.get("owner"),
        "reported_action": row.get("action"),
        "asset_description": row.get("assetDescription"),
        "reported_ticker": row.get("printedTicker"),
        "reported_asset_type": row.get("assetTypeCode") or row.get("assetTypeLabel"),
        "comment": row.get("comment"),
        **amounts,
        "blockers": [
            "No measured public/provider clock",
            "Instrument/action and amendment lineage require source review",
        ],
    }
