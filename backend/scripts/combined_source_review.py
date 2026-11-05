"""Pure source-review transforms; never sets review flags or imports a dataset."""

import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.market_data.calendar import session_times
from app.schemas.domain import Action, FXObservation
from scripts.prepare_fred_fx import normalize


def weekly_fx(
    rows: list[dict], release_floors: dict[date, date] | None = None
) -> tuple[list[FXObservation], list[dict]]:
    """Keep initial values, but never expose a week before its following Monday.

    ALFRED is the authority for first-vintage dates. The H.10 weekly release
    convention supplies an additional conservative floor, not an earlier date.
    normalize adds a further midnight-after-release boundary. Holidays/delays
    already represented by later ALFRED dates are never brought forward.
    """
    adjusted, changes = [], []
    for row in rows:
        observed = date.fromisoformat(row["date"])
        released = date.fromisoformat(row["realtime_start"])
        if released < observed:
            raise ValueError("FRED release precedes observation")
        following_monday = observed + timedelta(days=7 - observed.weekday())
        floor = max(
            released, following_monday, (release_floors or {}).get(observed, following_monday)
        )
        if row["value"] != "." and floor != released:
            changes.append(
                {
                    "observation_date": str(observed),
                    "fred_first_vintage": str(released),
                    "conservative_release_floor": str(floor),
                    "value": row["value"],
                }
            )
        adjusted.append({**row, "realtime_start": str(floor)})
    return normalize(adjusted), changes


def declared_usd(text: str) -> set[Decimal]:
    """Extract an original USD amount, excluding later FX conversion notices."""
    normalized = " ".join(text.split())
    if not re.search(r"S&P\s*500", normalized) or "SPY" not in normalized:
        raise ValueError("Announcement does not identify SPY")
    if re.search(r"(?:Foreign Exchange|FX) Rate Announcement", normalized, re.I):
        return set()
    values = re.findall(r"(?:USD|US\$)\s*([0-9]+\.\s*[0-9]+)", normalized)
    return {Decimal(re.sub(r"\s", "", value)) for value in values}


def dividend_from_evidence(
    ex_date: date,
    payment_date: date,
    amount: Decimal,
    announcements: list[dict],
    required_at: datetime | None = None,
) -> tuple[Action, list[str]]:
    opening = session_times(ex_date)[0]
    matches = []
    for row in announcements:
        if amount not in declared_usd(row["text"]):
            continue
        clock = datetime.fromisoformat(row["broadcast_at"])
        if clock.tzinfo is None or clock.utcoffset() is None:
            raise ValueError("Announcement timestamp requires timezone")
        # This source-specific join uses the original ASX notice's local day and
        # the independently supplied US ex-date, never the CDI ex/payment dates.
        if clock.astimezone(ZoneInfo("Australia/Sydney")).date() != ex_date:
            continue
        # The archive has minute precision. Use the end of that displayed minute.
        available = clock.replace(second=0, microsecond=0) + timedelta(minutes=1)
        if available <= opening:
            matches.append((available, row["id"]))
    if not matches:
        raise ValueError(f"No matching published SPY amount before {ex_date} US open")
    # Latest corroborating original/amended notice before the effective open is
    # deliberately conservative. Later payment/FX notices cannot enter this set.
    available = max(clock for clock, _ in matches)
    if required_at is not None:
        if required_at.tzinfo is None or required_at.utcoffset() is None:
            raise ValueError("Payment-date evidence requires timezone")
        available = max(available, required_at)
        if available > opening:
            raise ValueError("Complete action evidence is unavailable before US open")
    return (
        Action(
            symbol="SPY",
            kind="dividend",
            session_date=ex_date,
            payment_date=payment_date,
            available_at=available,
            value=amount,
        ),
        sorted(identifier for _, identifier in matches),
    )
