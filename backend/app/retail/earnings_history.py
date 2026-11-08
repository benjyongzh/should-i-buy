"""Original quarterly statements with issuer corroboration and declared daily clocks."""

import hashlib
import re
from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.market_data.calendar import session_times, sessions
from app.market_data.strategy_inputs import HistoricalEvent, StrategyInput
from app.onboarding.evidence import plain_text
from app.retail.earnings_tables import selected_income_statement

ORDINAL = {"first": 1, "second": 2, "third": 3, "fourth": 4}
NY = ZoneInfo("America/New_York")


def quarterly_pair(
    sec: bytes,
    issuer: bytes,
    symbol: str,
    accession: str,
    exhibit_name: str,
    issuer_url: str,
    sec_url: str,
):
    raw = sec.decode("utf-8", "strict")
    header = raw.split("</SEC-HEADER>", 1)[0]
    if not re.search(r"ACCESSION NUMBER:\s*" + re.escape(accession), header):
        raise ValueError("quarterly accession mismatch")
    accepted = re.search(r"<ACCEPTANCE-DATETIME>(\d{14})", header)
    if not accepted:
        raise ValueError("quarterly acceptance clock missing")
    accepted_at = datetime.strptime(accepted[1], "%Y%m%d%H%M%S").replace(tzinfo=NY)
    document = None
    for doc in re.findall(r"<DOCUMENT>(.*?)</DOCUMENT>", raw, re.S):
        filename = re.search(r"<FILENAME>([^\r\n]+)", doc)
        kind = re.search(r"<TYPE>([^\r\n]+)", doc)
        if (
            filename
            and filename[1].strip() == exhibit_name
            and kind
            and kind[1].strip().startswith("EX-99")
        ):
            document = doc
    if document is None:
        raise ValueError("original quarterly earnings exhibit not found")
    text = plain_text(document.encode())
    period = re.search(r"quarter ended ([A-Z][a-z]+ \d{1,2}, 20\d\d)", text[:1800])
    if not period:
        raise ValueError("explicit quarterly period end missing")
    period_end = datetime.strptime(period[1], "%B %d, %Y").date()
    if symbol == "AAPL":
        fiscal = re.search(
            r"fiscal (20\d\d) (first|second|third|fourth) quarter", text[:1800], re.I
        )
        if not fiscal:
            raise ValueError("Apple fiscal quarter missing")
        fiscal_year, quarter = int(fiscal[1]), ORDINAL[fiscal[2].lower()]
        company, start = "Apple", "CUPERTINO"
    elif symbol == "MSFT":
        quarter = {9: 1, 12: 2, 3: 3, 6: 4}.get(period_end.month)
        if quarter is None:
            raise ValueError("Microsoft period is not a regular fiscal quarter")
        fiscal_year = period_end.year + (quarter < 3)
        company, start = "Microsoft", "REDMOND"
    else:
        raise ValueError("review a new issuer's statement convention before extraction")
    tables = selected_income_statement(document.encode())
    if len(tables) != 1:
        raise ValueError("quarterly income statement is missing or ambiguous")
    statement = tables[0]
    revenue = Decimal(statement["revenue_columns"][0])
    eps = Decimal(statement["diluted_eps_columns"][0])
    if revenue <= 0 or abs(eps) > 10000:
        raise ValueError("implausible current-quarter nominal figures")
    issuer_text = plain_text(issuer)
    position = re.search(start, issuer_text, re.I)
    if not position:
        raise ValueError("issuer press-release body is missing")
    intro = issuer_text[position.start() : position.start() + 4500]
    if company not in intro or period[1] not in intro:
        raise ValueError("issuer identity or reported period mismatch")
    # Earnings headlines round revenues; the exact number comes from the original table.
    amounts = [Decimal(m) for m in re.findall(r"\$\s*(\d+(?:\.\d+)?)\s+billion", intro, re.I)]
    if not any(abs(revenue / 1000 - amount) <= Decimal("0.05") for amount in amounts):
        raise ValueError("issuer revenue headline does not corroborate original statement")
    money = re.compile(r"\$\s*(\(?-?\d+(?:\.\d+)?\)?)")
    proofs = []
    for match in money.finditer(intro):
        amount = Decimal(match[1].strip("()")) * (-1 if match[1].startswith("(") else 1)
        context = intro[max(0, match.start() - 180) : match.end() + 70]
        if amount == eps and re.search(r"earnings|loss|EPS", context, re.I):
            proofs.append(context)
    if not proofs:
        raise ValueError("issuer EPS text does not corroborate original GAAP diluted EPS")
    day = accepted_at.date() + timedelta(days=1)
    clock = session_times(sessions(day, day + timedelta(days=14))[0])[1]
    return {
        "symbol": symbol,
        "accession": accession,
        "fiscal_year": fiscal_year,
        "fiscal_quarter": quarter,
        "period_end": str(period_end),
        "sec_accepted_at": accepted_at.isoformat(),
        "modeled_available_at": clock.isoformat(),
        "verified_public_at": None,
        "revenue_usd_millions": str(revenue),
        "gaap_diluted_eps_usd": str(eps),
        "revenue_columns": statement["revenue_columns"],
        "eps_columns": statement["diluted_eps_columns"],
        "issuer_eps_context": proofs[0],
        "issuer_url": issuer_url,
        "sec_url": sec_url,
        "sec_body_sha256": hashlib.sha256(sec).hexdigest(),
        "issuer_body_sha256": hashlib.sha256(issuer).hexdigest(),
    }


def earnings_source(records: list[dict]):
    keys = [(r["symbol"], r["fiscal_year"], r["fiscal_quarter"]) for r in records]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate quarterly earnings identity")
    if len(records) != 64 or any(
        sum(r["symbol"] == symbol and r["sec_accepted_at"].startswith(str(year)) for r in records)
        != 4
        for symbol in ("AAPL", "MSFT")
        for year in range(2018, 2026)
    ):
        raise ValueError(
            "full2018–2025 quarterly source needs four original releases per issuer/calendar year"
        )
    events = []
    for record in records:
        clock = record["modeled_available_at"]
        for kind, value, units in (
            ("release", None, None),
            ("gaap_eps", record["gaap_diluted_eps_usd"], "USD/share GAAP diluted EPS"),
            (
                "revenue_usd_millions",
                record["revenue_usd_millions"],
                "USD millions nominal revenue",
            ),
        ):
            details = (
                None
                if value is None
                else {
                    "type": "economic",
                    "release_at": clock,
                    "reference_period": f"FY{record['fiscal_year']}Q{record['fiscal_quarter']}",
                    "units": units,
                    "actual": value,
                }
            )
            events.append(
                HistoricalEvent(
                    event_id=f"issuer-earnings:{record['accession']}:{kind}",
                    published_at=clock,
                    available_at=clock,
                    category="earnings." + kind,
                    symbols=[record["symbol"]],
                    title=f"{record['symbol']} FY{record['fiscal_year']}Q{record['fiscal_quarter']} {kind}",
                    source_url=record["sec_url"],
                    original_content_hash=record["sec_body_sha256"],
                    derivation="Original quarterly GAAP statement corroborated with issuer release. Publication/availability are modeled at next exchange-session close after acceptance, not measured first delivery. No adjusted EPS, restatement or consensus substitution.",
                    details=details,
                )
            )
    return StrategyInput(
        kind="events",
        name="AAPL MSFT original quarterly earnings2018–2025 daily research proxy",
        source="issuer+original-sec-quarterly-statements",
        source_url="https://www.sec.gov/",
        availability_policy="64 original quarterly releases from reviewed SEC8K inventory, paired with issuer pages. Both modeled publication and availability use next exchange-session CLOSE after SEC acceptance; original public latency unverified. GAAP current-quarter diluted EPS and nominal revenue in USD millions; no adjusted EPS, annual-column, revised-history or consensus substitution. Numeric economic-release contract reused for company earnings. Not all corporate announcements or analyst news.",
        coverage_start=datetime(2018, 1, 1, tzinfo=NY),
        coverage_end=datetime(2025, 12, 31, 23, 59, 59, 999999, tzinfo=NY),
        symbols=["AAPL", "MSFT"],
        stream_id="ISSUER_EARNINGS",
        events=events,
        source_hashes=sorted(
            {r[k] for r in records for k in ("sec_body_sha256", "issuer_body_sha256")}
        ),
    )
