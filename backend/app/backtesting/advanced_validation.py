from datetime import timedelta

from app.market_data.calendar import decision_timestamp, session_times, sessions
from app.market_data.features import requirements as external_requirements
from app.market_data.input_book import InputBook
from app.market_data.strategy_inputs import advanced
from app.market_data.validation import validate_dataset
from app.schemas.domain import ExecutionPolicy


def execution_policy(config, profile):
    return config.execution_policy or ExecutionPolicy(
        decision_cadence="bar_close" if profile.timeframe != "1d" else "daily_close",
        default_timeframe="intraday" if profile.timeframe != "1d" else "daily",
    )


def requirements(config, profile):
    nodes = []

    def visit(value):
        if isinstance(value, dict):
            nodes.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(config.model_dump(mode="json"))
    policy = execution_policy(config, profile)
    intraday = (
        profile.timeframe != "1d"
        or policy.decision_cadence != "daily_close"
        or policy.default_timeframe == "intraday"
        or any(n.get("type") == "market" and n.get("timeframe") == "intraday" for n in nodes)
        or any(
            w.start_minutes_after_open or w.end_minutes_before_close
            for w in (policy.entry_window, policy.exit_window)
        )
    )
    universe = bool(
        config.universe
        and (
            config.universe.require_membership
            or config.universe.sectors
            or config.universe.exclude_sectors
            or config.universe.prefer_sectors
        )
    ) or any(n.get("type") == "event" and n.get("scope") == "sector" for n in nodes)
    return {
        "advanced_engine": advanced(config, profile),
        "intraday": intraday,
        "universe": universe,
        "event_streams": sorted({n["stream_id"] for n in nodes if n.get("type") == "event"}),
        "external_series": sorted({name for name, _, _ in external_requirements(config)}),
        "event_nodes": [n for n in nodes if n.get("type") == "event"],
    }


def candidates(config, profile, book, clock):
    policy = config.universe
    output = []
    for symbol in sorted(profile.symbols):
        if policy and (
            (policy.include_symbols and symbol not in policy.include_symbols)
            or symbol in policy.exclude_symbols
        ):
            continue
        state = (
            book.state(symbol, clock)
            if policy
            and (
                policy.require_membership
                or policy.sectors
                or policy.exclude_sectors
                or policy.prefer_sectors
            )
            else None
        )
        if state and (
            not state.listed
            or (policy.sectors and state.sector not in policy.sectors)
            or state.sector in policy.exclude_sectors
        ):
            continue
        output.append(symbol)
    return output


def validate_advanced(config, profile, data, sources, features=None):
    validate_dataset(data)
    if not data.synthetic and not data.corporate_actions_reviewed:
        raise ValueError(
            "reviewed complete corporate-action coverage is required for real raw prices"
        )
    days = sessions(profile.start_date, profile.end_date)
    if not days:
        raise ValueError("profile contains no trading sessions")
    book = InputBook(data, sources, features)
    needed = requirements(config, profile)
    if needed["intraday"] and profile.timeframe == "1d":
        raise ValueError(
            "intraday timing/operands require an intraday profile and reviewed bar revisions; daily candles cannot satisfy this request"
        )
    if needed["universe"] and not book.universe:
        raise ValueError("historical classification/membership revision required")
    if any(not s.complete for s in sources):
        raise ValueError("selected strategy inputs must attest complete coverage")
    if config.universe and (set(config.universe.include_symbols) - set(profile.symbols)):
        raise ValueError(
            "strategy universe includes symbols outside the profile's permitted universe"
        )
    minute = None if profile.timeframe == "1d" else int(profile.timeframe.removesuffix("min"))
    if minute and (
        not book.intraday or any(s.bar_minutes != minute for s in sources if s.kind == "intraday")
    ):
        raise ValueError("reviewed intraday inputs matching the profile resolution are required")
    lookup = {
        (b.symbol, getattr(b, "start_at", b.session_date)): b
        for b in (book.intraday if minute else data.bars)
    }
    ticks = 0
    for day in days:
        opening, closing = session_times(day)
        clocks = []
        start = opening
        while start < closing:
            clocks.append(start)
            if minute is None:
                break
            start += timedelta(minutes=minute)
        ticks += len(clocks)
        if ticks > 200_000:
            raise ValueError(
                "run exceeds 200,000 execution intervals; reduce date range or choose coarser bars"
            )
        for clock in clocks:
            for symbol in set(candidates(config, profile, book, clock) + [profile.benchmark]):
                key = (symbol, clock if minute else day)
                if key not in lookup:
                    raise ValueError(
                        f"missing required {'intraday interval' if minute else 'session'} for {symbol} at {clock.isoformat()}; no data substitution is allowed"
                    )
                if lookup[key].available_at > decision_timestamp(day, data.decision_time):
                    raise ValueError(
                        "required bar is unavailable by the session's final valuation clock"
                    )
        now = decision_timestamp(day, data.decision_time)
        previous = decision_timestamp(
            sessions(day - timedelta(days=14), day - timedelta(days=1))[-1], data.decision_time
        )
        for name, age, prior in external_requirements(config):
            view = book.features.materialize(now, previous)
            view.value(name, age)
            if prior:
                view.value(name, age, 1)
        # Validate the entire interval, not only decision dates: sparse event
        # sources must explicitly attest the no-event periods as well.
        for node in needed["event_nodes"]:
            from app.schemas.domain import EventValue

            expression = EventValue.model_validate(node)
            for symbol in candidates(config, profile, book, now):
                book.event_value(expression, symbol, opening)
                book.event_value(expression, symbol, now)
    return book
