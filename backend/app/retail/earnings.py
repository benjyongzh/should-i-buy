"""Explicitly selected issuer/SEC earnings facts, with separate delivery assumptions."""

import hashlib
import re
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from pydantic import Field

from app.market_data.calendar import session_times, sessions
from app.onboarding.evidence import plain_text
from app.schemas.domain import StrictModel


class EarningsSelection(StrictModel):
    symbol: str = Field(pattern=r"^[A-Z]{1,5}$")
    issuer_name: str = Field(min_length=1, max_length=100)
    accession: str = Field(pattern=r"^\d{10}-\d{2}-\d{6}$")
    fiscal_period: str = Field(min_length=1, max_length=40)
    period_end_literal: str = Field(min_length=5, max_length=50)
    revenue_usd_millions: Decimal = Field(gt=0, le=1_000_000_000)
    issuer_revenue_billions: Decimal = Field(gt=0, le=1_000_000)
    diluted_eps_usd: Decimal = Field(ge=-10000, le=10000)
    issuer_eps_literal: str = Field(min_length=10, max_length=200)


def normalize_pair(issuer_body: bytes, sec_body: bytes, selection: EarningsSelection) -> dict:
    """A reviewer supplies literal selections; both retained bodies must corroborate."""
    text = sec_body.decode("utf-8", "strict")
    header = text.split("</SEC-HEADER>", 1)[0]
    if not re.search(r"ACCESSION NUMBER:\s*" + re.escape(selection.accession), header):
        raise ValueError("SEC earnings accession mismatch")
    accepted = re.search(r"<ACCEPTANCE-DATETIME>(\d{14})", header)
    if not accepted:
        raise ValueError("SEC earnings acceptance clock missing")
    clock = datetime.strptime(accepted[1], "%Y%m%d%H%M%S").replace(
        tzinfo=ZoneInfo("America/New_York")
    )
    exhibits = []
    for doc in re.findall(r"<DOCUMENT>(.*?)</DOCUMENT>", text, re.S):
        kind = re.search(r"<TYPE>([^\r\n]+)", doc)
        if kind and kind[1].strip().startswith("EX-99"):
            exhibits.append(plain_text(doc.encode()))
    if not exhibits:
        raise ValueError("SEC earnings exhibit missing")
    issuer = plain_text(issuer_body)

    # All supplied financial facts must match the SAME original exhibit.
    def matches(exhibit):
        identity = selection.issuer_name.casefold() in exhibit.casefold()
        period = selection.period_end_literal in exhibit
        eps = str(selection.diluted_eps_usd)
        nominal_revenue = format(selection.revenue_usd_millions, ",.0f")
        return (
            identity
            and period
            and bool(re.search(r"(?<![\d,])" + re.escape(nominal_revenue) + r"(?![\d,])", exhibit))
            and bool(re.search(r"(?<![\d.])" + re.escape(eps) + r"(?![\d.])", exhibit))
        )

    if not any(matches(exhibit) for exhibit in exhibits):
        raise ValueError("selected issuer/period/revenue/EPS do not match one original SEC exhibit")
    if (
        selection.issuer_name.casefold() not in issuer.casefold()
        or selection.period_end_literal not in issuer
    ):
        raise ValueError("issuer earnings identity/period mismatch")
    if selection.issuer_eps_literal.casefold() not in issuer.casefold():
        raise ValueError("issuer EPS statement not found")
    if not re.search(
        r"(?<![\d.])\$" + re.escape(str(selection.diluted_eps_usd)) + r"(?![\d.])",
        selection.issuer_eps_literal,
    ):
        raise ValueError("issuer EPS statement differs from selected nominal amount")
    if not re.search(
        r"\$" + re.escape(str(selection.issuer_revenue_billions)) + r"\s+billion", issuer
    ):
        raise ValueError("issuer headline revenue missing")
    # Headlines round to tenths of a billion; exact millions come from the SEC table.
    if abs(
        selection.revenue_usd_millions / Decimal(1000) - selection.issuer_revenue_billions
    ) > Decimal("0.05"):
        raise ValueError("issuer rounded headline and exact SEC revenue disagree")
    day = clock.date() + timedelta(days=1)
    assumed = session_times(sessions(day, day + timedelta(days=14))[0])[1]
    return {
        **selection.model_dump(mode="json"),
        "issuer_body_sha256": hashlib.sha256(issuer_body).hexdigest(),
        "sec_body_sha256": hashlib.sha256(sec_body).hexdigest(),
        "sec_accepted_at": clock.isoformat(),
        "verified_public_at": None,
        "assumed_daily_available_at": assumed.isoformat(),
        "clock_policy": "Assumed next-session-close delivery after SEC acceptance; not an observed release/publication clock.",
        "metric_basis": "Selected as-reported GAAP diluted EPS and nominal USD revenue; no later restatement or split adjustment",
        "consensus": None,
        "surprise": None,
        "strategy_eligible": False,
    }
