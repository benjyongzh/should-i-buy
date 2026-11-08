"""Suggest review fields from retained issuer text; never grants eligibility."""

import re
from datetime import datetime
from decimal import Decimal

from app.onboarding.evidence import date_in_text, plain_text

D = Decimal
WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "twenty": 20,
    "hundred": 100,
}


def money_in_text(value, text):
    return D(value) in {D(x) for x in re.findall(r"\$\s*(\d+(?:\.\d+)?|\.\d+)\b", text)}


def ratio_in_text(value, text):
    for a, b in re.findall(
        r"\b(\d+|" + "|".join(WORDS) + r")[ -]+for[ -]+(\d+|" + "|".join(WORDS) + r")\b",
        text.lower(),
    ):
        left, right = WORDS.get(a, a), WORDS.get(b, b)
        if D(right) and D(left) / D(right) == D(value):
            return True
    return False


def candidate_action(candidate):
    row = candidate["record"]
    dividend = candidate["kind"] == "cash_dividends"
    value = D(str(row["rate"])) if dividend else D(str(row["new_rate"])) / D(str(row["old_rate"]))
    return {
        "symbol": row["symbol"],
        "session_date": row["ex_date"],
        "kind": "dividend" if dividend else "split",
        "value": str(value),
        "payment_date": row.get("payable_date") if dividend else None,
        "available_at": "",
    }


def proposals(candidates, artifacts):
    snippets = []
    for artifact in artifacts:
        if artifact.kind != "sec_submission":
            continue
        text = plain_text(artifact.body)
        for match in list(re.finditer(r"\bdividend\b|\bstock split\b", text, re.I))[:40]:
            snippets.append((artifact, text[max(0, match.start() - 220) : match.end() + 1500]))
    output = []
    for candidate in candidates:
        action = candidate_action(candidate)
        proposal = {
            "source_action_id": candidate["record"]["id"],
            "action": action,
            "artifact_id": "",
            "quote": "",
            "state": "needs_evidence",
        }
        for artifact, quote in snippets:
            if artifact.metadata_json.get("symbol") != action["symbol"]:
                continue
            payment = action["payment_date"]
            if action["kind"] == "dividend":
                if not money_in_text(action["value"], quote):
                    continue
                if not payment:
                    found = re.search(
                        r"(?:payable|paid)\s+(?:on\s+)?([A-Za-z]+\.?\s+\d{1,2},\s*\d{4})",
                        quote,
                        re.I,
                    )
                    if found:
                        for fmt in ("%B %d, %Y", "%b %d, %Y"):
                            try:
                                payment = (
                                    datetime.strptime(found[1].replace(".", ""), fmt)
                                    .date()
                                    .isoformat()
                                )
                                break
                            except ValueError:
                                pass
                if not payment or not date_in_text(datetime.fromisoformat(payment).date(), quote):
                    continue
            elif not ratio_in_text(action["value"], quote) or not date_in_text(
                datetime.fromisoformat(action["session_date"]).date(), quote
            ):
                continue
            proposal.update(artifact_id=artifact.id, quote=quote, state="needs_review")
            proposal["action"] = {
                **action,
                "payment_date": payment,
                "available_at": artifact.metadata_json["available_at"],
            }
            break
        output.append(proposal)
    return output
