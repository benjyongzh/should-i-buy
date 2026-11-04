import csv
import io
import time
from datetime import UTC, date, datetime, timedelta
from datetime import time as day_time
from typing import Literal, Protocol
from zoneinfo import ZoneInfo

import httpx

from app.core.config import settings
from app.market_data.calendar import session_times
from app.schemas.domain import Bar, DatasetInput


class HistoricalProvider(Protocol):
    def fetch(self, symbols: list[str], start: date, end: date) -> DatasetInput: ...


def csv_records(content: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError("CSV requires unique column headers")
    records = []
    for number, row in enumerate(reader, start=2):
        if None in row or any(v is None for v in row.values()):
            raise ValueError(f"CSV row {number} has inconsistent columns")
        if len(records) >= settings().max_dataset_rows:
            raise ValueError("CSV row limit exceeded")
        records.append({k: v for k, v in row.items() if v != ""})
    return records


class AlpacaProvider:
    """Read-only, raw daily bars. No brokerage endpoint exists in this adapter."""

    def fetch(
        self, symbols: list[str], start: date, end: date, *, feed: Literal["iex", "sip"] = "iex"
    ) -> DatasetInput:
        if feed not in ("iex", "sip"):
            raise ValueError("Alpaca feed must be iex or sip")
        config = settings()
        if (
            not config.alpaca_api_key.get_secret_value()
            or not config.alpaca_secret_key.get_secret_value()
        ):
            raise ValueError("Alpaca data credentials are not configured; import CSV instead")
        headers = {
            "APCA-API-KEY-ID": config.alpaca_api_key.get_secret_value(),
            "APCA-API-SECRET-KEY": config.alpaca_secret_key.get_secret_value(),
        }
        params = {
            "symbols": ",".join(symbols),
            "start": str(start),
            "end": str(end + timedelta(days=1)),
            "timeframe": "1Day",
            "adjustment": "raw",
            "feed": feed,
            "asof": "-",
            "limit": 10000,
            "sort": "asc",
        }
        bars = []
        with httpx.Client(timeout=60) as client:
            for _ in range(50):
                try:
                    response = client.get(
                        "https://data.alpaca.markets/v2/stocks/bars", headers=headers, params=params
                    )
                except httpx.HTTPError as exc:
                    raise ValueError(
                        "Alpaca data connection failed; retry with a smaller date range"
                    ) from exc
                if response.status_code != 200:
                    raise ValueError(
                        f"Alpaca historical data request failed (HTTP {response.status_code}); check data entitlements/rate limits"
                    )
                payload = response.json()
                for symbol, values in (payload.get("bars") or {}).items():
                    for value in values:
                        day = (
                            datetime.fromisoformat(value["t"].replace("Z", "+00:00"))
                            .astimezone(ZoneInfo("America/New_York"))
                            .date()
                        )
                        if not start <= day <= end:
                            continue
                        session_times(day)
                        # Daily volume includes extended-hours trades; gate the complete bar until evening.
                        close = datetime.combine(
                            day, day_time(20), ZoneInfo("America/New_York")
                        ).astimezone(UTC)
                        if close + timedelta(minutes=15) > datetime.now(UTC):
                            raise ValueError(
                                "Alpaca returned an unfinished daily session; import completed sessions only"
                            )
                        bars.append(
                            Bar(
                                symbol=symbol,
                                session_date=day,
                                open=str(value["o"]),
                                high=str(value["h"]),
                                low=str(value["l"]),
                                close=str(value["c"]),
                                volume=str(value["v"]),
                                source_timestamp=close,
                                available_at=close + timedelta(minutes=15),
                                quality=[
                                    "availability_assumed_20_15_new_york",
                                    "revised_history_not_vintage",
                                ],
                            )
                        )
                if len(bars) > config.max_dataset_rows:
                    raise ValueError("Alpaca import exceeds configured row limit")
                token = payload.get("next_page_token")
                if not token:
                    break
                params["page_token"] = token
                time.sleep(0.35)
            else:
                raise ValueError("Alpaca pagination limit exceeded; use a smaller import")
        return DatasetInput(
            name=f"Alpaca {feed.upper()} {start}–{end}",
            provider=f"alpaca-{feed}",
            decision_time="20:30_America/New_York",
            bars=bars,
            availability_policy=f"Assumed 20:15 America/New_York availability after extended-hours volume; decisions 20:30. Current revised bars, not publication vintages. {feed.upper()} feed; not official auction prices. FX/actions require separate source inputs.",
        )
