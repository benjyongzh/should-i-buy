"""Source-to-candidate checks for a declared retail information boundary."""

import hashlib
import json
import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from app.market_data.calendar import session_times, sessions
from app.market_data.platform_providers import NewsFetch, normalize_news
from app.market_data.strategy_inputs import HistoricalEvent
from app.schemas.domain import canonical_hash

NY = ZoneInfo("America/New_York")


def audit_news(request: NewsFetch, raw_pages: list[bytes], candidate):
    """Require a byte-replay match, then report limits without declaring eligibility."""
    hashes = [hashlib.sha256(raw).hexdigest() for raw in raw_pages]
    pages = [json.loads(raw, parse_float=Decimal) for raw in raw_pages]
    expected = normalize_news(request, pages, hashes)
    if expected != candidate:
        raise ValueError("news candidate differs from retained source replay")
    if not pages or pages[-1].get("next_page_token"):
        raise ValueError("news pagination is incomplete")
    events = candidate.events
    rows = [r for page in pages for r in page.get("news") or []]
    return {
        "policy": "retail-vendor-current-versions-v1",
        "request": request.model_dump(mode="json"),
        "candidate_hash": canonical_hash(candidate.model_dump(mode="json")),
        "source_hashes": hashes,
        "pages": len(pages),
        "events": len(events),
        "rows_checked": len(rows),
        "older_publications_updated_in_window_excluded": len(rows) - len(events),
        "updated_versions": sum(e.available_at > e.published_at for e in events),
        "headline_only": sum(not r.get("content") and not r.get("summary") for r in rows),
        "missing_full_body": sum(not r.get("content") for r in rows),
        "available_after_requested_period": sum(
            e.available_at >= candidate.coverage_end for e in events
        ),
        "symbols": {s: sum(s in e.symbols for e in events) for s in request.symbols},
        "tag_mentions": {
            t: sum(t in e.tags for e in events)
            for t in candidate.category_catalog
            if t != "company_news"
        },
        "provider_pagination_complete": True,
        "original_vintages_certified": False,
        "all_retail_news_covered": False,
        "automatically_approved": False,
        "limits": [
            "The provider's returned current versions are visible only at their version update time.",
            "Completed pagination establishes query exhaustion, not an independently proven complete historical archive.",
            "Missing full bodies remain missing; keyword mentions are not structured ratings, trades or sentiment.",
            "Authenticated retail feed access is subscription access; public dissemination is not inferred.",
        ],
    }


def inventory_rows(table: dict) -> list[dict]:
    """SEC parallel columns must have equal lengths; no silent zip truncation."""
    names = ["accessionNumber", "form", "filingDate", "acceptanceDateTime", "primaryDocument"]
    lengths = {len(table[n]) for n in names}
    if len(lengths) != 1:
        raise ValueError("SEC inventory columns have different lengths")
    rows = [
        dict(zip(names, values, strict=True))
        for values in zip(*(table[n] for n in names), strict=True)
    ]
    if "items" in table:
        if len(table["items"]) != len(rows):
            raise ValueError("SEC item column has different length")
        for row, items in zip(rows, table["items"], strict=True):
            row["items"] = items
    return rows


def insider_event(raw: bytes, row: dict, symbol: str, cik: str, source_url: str):
    """Describe original Form 4 non-derivative rows without inferring investment intent."""
    if row["form"] not in {"4", "4/A"} or not re.fullmatch(
        r"\d{10}-\d{2}-\d{6}", row["accessionNumber"]
    ):
        raise ValueError("not an identified SEC Form 4 or amendment")
    text = raw.decode("utf-8", "strict")
    header = text.split("</SEC-HEADER>", 1)[0]
    match = re.search(r"<ACCEPTANCE-DATETIME>(\d{14})", header)
    if not match or not re.search(
        r"ACCESSION NUMBER:\s*" + re.escape(row["accessionNumber"]), header
    ):
        raise ValueError("SEC header lacks matching accession/acceptance")
    accepted = datetime.strptime(match[1], "%Y%m%d%H%M%S").replace(tzinfo=NY)
    if accepted.replace(fold=1).utcoffset() != accepted.utcoffset():
        raise ValueError("ambiguous SEC acceptance clock")
    declared = datetime.fromisoformat(row["acceptanceDateTime"].replace("Z", "+00:00"))
    if declared.tzinfo is None or declared != accepted:
        raise ValueError("SEC inventory and original header acceptance clocks disagree")
    primary_document = row["primaryDocument"]
    if "/" in primary_document:
        if not re.fullmatch(r"xslF345X\d{2}/[A-Za-z0-9_.-]+\.xml", primary_document):
            raise ValueError("unrecognized SEC ownership rendering path")
        primary_document = primary_document.split("/", 1)[1]
    payload = None
    for doc in re.findall(r"<DOCUMENT>(.*?)</DOCUMENT>", text, re.S):
        filename = re.search(r"<FILENAME>([^\r\n]+)", doc)
        form = re.search(r"<TYPE>([^\r\n]+)", doc)
        if (
            filename
            and filename[1].strip() == primary_document
            and form
            and form[1].strip() == row["form"]
        ):
            xml = re.search(r"(<ownershipDocument\b.*?</ownershipDocument>)", doc, re.S)
            if xml:
                payload = xml[1]
    if payload is None or "<!DOCTYPE" in text or "<!ENTITY" in text:
        raise ValueError("SEC ownership primary XML missing or unsafe")
    root = ET.fromstring(payload)
    if (
        int(root.findtext("issuer/issuerCik", "0")) != int(cik)
        or root.findtext("issuer/issuerTradingSymbol", "").upper() != symbol
    ):
        raise ValueError("SEC ownership issuer identity disagrees")
    if root.findtext("documentType") != row["form"]:
        raise ValueError("SEC ownership form identity disagrees")
    owners = [
        e.findtext("reportingOwnerId/rptOwnerName", "") for e in root.findall("reportingOwner")
    ]
    transactions = []
    for transaction in root.findall("nonDerivativeTable/nonDerivativeTransaction"):
        day = date.fromisoformat(transaction.findtext("transactionDate/value", ""))
        if day > accepted.date():
            raise ValueError("insider transaction occurs after filing acceptance")

        def amount(path, transaction=transaction):
            value = transaction.findtext(path)
            if value is None or not value.strip():
                return None
            parsed = Decimal(value)
            if not parsed.is_finite() or parsed < 0:
                raise ValueError("invalid nominal insider transaction amount")
            return str(parsed)

        transactions.append(
            {
                "transaction_date": str(day),
                "code": transaction.findtext("transactionCoding/transactionCode"),
                "acquired_disposed": transaction.findtext(
                    "transactionAmounts/transactionAcquiredDisposedCode/value"
                ),
                "shares": amount("transactionAmounts/transactionShares/value"),
                "price_per_share": amount("transactionAmounts/transactionPricePerShare/value"),
            }
        )
    next_day = accepted.date() + timedelta(days=1)
    available = session_times(sessions(next_day, next_day + timedelta(days=14))[0])[1]
    tags = ["insider.form4_amendment" if row["form"] == "4/A" else "insider.form4"]
    # Amendments are separate filings, never additional inferred purchase/sale signals.
    if row["form"] == "4":
        tags += sorted(
            {
                {"P": "insider.reported_purchase", "S": "insider.reported_sale"}[t["code"]]
                for t in transactions
                if t["code"] in {"P", "S"}
            }
        )
    event = HistoricalEvent(
        event_id="sec-" + row["accessionNumber"],
        published_at=accepted,
        available_at=available,
        category="insider_filing",
        tags=tags,
        symbols=[symbol],
        title=f"{symbol} SEC {row['form']} ownership disclosure",
        source_url=source_url,
        original_content_hash=hashlib.sha256(raw).hexdigest(),
        derivation="Original SEC ownership XML/header; nominal rows, not adjusted holdings. Assumed next-session-close delivery after acceptance; amendments separate and not replayed as new trades.",
    )
    return event, {
        "accession": row["accessionNumber"],
        "form": row["form"],
        "owners": owners,
        "accepted_at": accepted.astimezone(UTC).isoformat(),
        "available_at": available.isoformat(),
        "transactions": transactions,
        "derivative_rows_not_normalized": len(
            root.findall("derivativeTable/derivativeTransaction")
        ),
        "clock_policy": "Assumed next-session-close delivery; not a measured first-public timestamp.",
        "amendment_lineage_reviewed": False if row["form"] == "4/A" else None,
    }
