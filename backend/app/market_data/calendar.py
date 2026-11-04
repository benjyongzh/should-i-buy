from datetime import UTC, date, datetime, time, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

import exchange_calendars as xcals


@lru_cache
def calendar():
    return xcals.get_calendar("XNYS", start="1989-01-01", end="2036-12-31")


def sessions(start: date, end: date) -> list[date]:
    return [s.date() for s in calendar().sessions_in_range(str(start), str(end))]


@lru_cache(maxsize=20000)
def session_times(day: date) -> tuple[datetime, datetime]:
    cal = calendar()
    if not cal.is_session(str(day)):
        raise ValueError(f"{day} is not an XNYS trading session")
    return cal.session_open(str(day)).to_pydatetime(), cal.session_close(str(day)).to_pydatetime()


def decision_timestamp(day: date, policy: str) -> datetime:
    if policy == "20:30_America/New_York":
        return datetime.combine(day, time(20, 30), ZoneInfo("America/New_York")).astimezone(UTC)
    return session_times(day)[1] + timedelta(minutes=30)
