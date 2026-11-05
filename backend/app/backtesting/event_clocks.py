"""Only selected, available information streams may trigger extra decisions."""

from zoneinfo import ZoneInfo

from app.backtesting.advanced_validation import requirements
from app.market_data.calendar import session_times

NY = ZoneInfo("America/New_York")


def source_clocks(config, profile, book, features, days):
    needed = requirements(config, profile)
    clocks = set()
    for node in needed["event_nodes"]:
        for partition in book.streams.get(node["stream_id"], []):
            for event in partition.events:
                if node["access"] == "public_only" and event.access != "public":
                    continue
                clocks.add(event.available_at)
                if (
                    node["measure"] != "count"
                    and node["value_field"] == "score"
                    and event.score_available_at
                ):
                    clocks.add(max(event.available_at, event.score_available_at))
    if needed["universe"] and book.universe:
        clocks.update(max(s.available_at, s.effective_at) for s in book.universe.states)
    for feature in features:
        if feature.series_id in needed["external_series"]:
            clocks.update(p.available_at for p in feature.points)
    result = {}
    allowed = set(days)
    for clock in clocks:
        day = clock.astimezone(NY).date()
        if day not in allowed:
            continue
        opening, closing = session_times(day)
        if opening <= clock < closing:
            result.setdefault(day, set()).add(clock)
    return result
