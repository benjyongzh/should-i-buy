"""Publication-gated inputs. Strategy evaluation receives bounded prefixes/scalars."""

from bisect import bisect_right
from collections.abc import Sequence
from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.market_data.calendar import session_times, sessions
from app.market_data.features import FeatureBook, FeatureView
from app.market_data.strategy_inputs import StrategyInput
from app.schemas.domain import (
    Arithmetic,
    CalendarValue,
    Constant,
    CorporateValue,
    EventValue,
    External,
    Market,
    Multiply,
    PortfolioValue,
)
from app.strategies.streaming import IndicatorCache

D = Decimal
NY = ZoneInfo("America/New_York")


class Prefix(Sequence):
    def __init__(self, rows, count, splits):
        self.__rows, self.__count, self.__splits = rows, count, splits

    def __len__(self):
        return self.__count

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(self.__count))]
        if index < 0:
            index += self.__count
        if not 0 <= index < self.__count:
            raise IndexError("future or missing history prefix")
        bar = self.__rows[index]
        ratio = D(1)
        for action in self.__splits:
            if bar.session_date < action.session_date:
                ratio *= action.value
        return (
            bar.model_copy(
                update={
                    "open": bar.open / ratio,
                    "high": bar.high / ratio,
                    "low": bar.low / ratio,
                    "close": bar.close / ratio,
                    "volume": bar.volume * ratio,
                }
            )
            if ratio != 1
            else bar
        )


class InputBook:
    def __init__(self, data, sources: list[StrategyInput], features=None):
        sources = [StrategyInput.model_validate(source.model_dump()) for source in sources]
        if any(not source.reviewed for source in sources):
            raise ValueError(
                "strategy sources require explicit reviewed revisions at the engine boundary"
            )
        self.data = data
        self.sources = sources
        if (
            len(sources) > 100
            or sum(len(s.bars) + len(s.states) + len(s.events) for s in sources) > 1_000_000
        ):
            raise ValueError(
                "strategy source/run row limit exceeded; use smaller symbol/date partitions"
            )
        universes = [s for s in sources if s.kind == "universe"]
        if len(universes) > 1:
            raise ValueError("choose exactly one historical universe revision")
        self.universe = universes[0] if universes else None
        self.states = {}
        for state in self.universe.states if self.universe else []:
            self.states.setdefault(state.symbol, []).append(state)
        self.intraday = [b for s in sources if s.kind == "intraday" for b in s.bars]
        keys = [(b.symbol, b.start_at) for b in self.intraday]
        if len(keys) != len(set(keys)):
            raise ValueError("overlapping intraday revisions/intervals")
        self.frames = {}
        for timeframe, rows in (("daily", data.bars), ("intraday", self.intraday)):
            for symbol in {b.symbol for b in rows}:
                subset = sorted(
                    (b for b in rows if b.symbol == symbol),
                    key=lambda b: getattr(b, "end_at", b.source_timestamp),
                )
                # Delayed/corrected bars require their own chronology rather than
                # backfilling them ahead of an already published newer candle.
                if any(
                    a.available_at > b.available_at
                    for a, b in zip(subset, subset[1:], strict=False)
                ):
                    raise ValueError(
                        "advanced bar availability must be nondecreasing; split delayed/corrected vintages into an explicit source policy"
                    )
                self.frames[(timeframe, symbol)] = (
                    subset,
                    [
                        max(
                            b.available_at,
                            b.source_timestamp,
                            getattr(b, "end_at", session_times(b.session_date)[1]),
                        )
                        for b in subset
                    ],
                )
        self.features = FeatureBook(features or [])
        self.cache = IndicatorCache()
        self.streams = {}
        for source in sources:
            if source.kind == "events":
                self.streams.setdefault(source.stream_id, []).append(source)
        for name, partitions in self.streams.items():
            ids = [e.event_id for s in partitions for e in s.events]
            if len(ids) != len(set(ids)):
                raise ValueError(f"duplicate event identity across {name} revisions")
            by_id = {e.event_id: e for s in partitions for e in s.events}
            for event in by_id.values():
                if event.supersedes_event_id:
                    prior = by_id.get(event.supersedes_event_id)
                    if (
                        prior is None
                        or prior.event_id == event.event_id
                        or prior.available_at >= event.available_at
                    ):
                        raise ValueError(
                            "event amendment requires an earlier retained source record"
                        )

    def state(self, symbol, clock):
        if (
            not self.universe
            or not self.universe.complete
            or not self.universe.coverage_start <= clock <= self.universe.coverage_end
        ):
            raise ValueError(
                f"reviewed historical universe coverage required for {symbol} at {clock.isoformat()}"
            )
        eligible = [
            s
            for s in self.states.get(symbol, [])
            if s.available_at <= clock and s.effective_at <= clock
        ]
        if not eligible:
            raise ValueError(
                f"no historically known classification/membership for {symbol} at {clock.isoformat()}"
            )
        return max(eligible, key=lambda s: (s.effective_at, s.available_at))

    def history(self, symbol, timeframe, clock):
        rows, clocks = self.frames.get((timeframe, symbol), ([], []))
        n = bisect_right(clocks, clock)
        splits = tuple(
            a
            for a in self.data.actions
            if a.symbol == symbol
            and a.kind == "split"
            and a.available_at <= clock
            and session_times(a.session_date)[0] <= clock
        )
        return Prefix(rows, n, splits), (
            symbol,
            timeframe,
            tuple((a.session_date, str(a.value)) for a in splits),
        )

    def event_value(self, node, symbol, clock):
        lower = clock - timedelta(minutes=node.lookback_minutes)
        partitions = self.streams.get(node.stream_id, [])
        declared = {category for source in partitions for category in source.category_catalog}
        if partitions and set(node.categories) - declared:
            raise ValueError(
                f"event categories/tags not declared by {node.stream_id}: {sorted(set(node.categories) - declared)}"
            )
        intervals = sorted(
            (s.coverage_start, s.coverage_end)
            for s in partitions
            if s.complete
            and (node.access == "public_only" or s.access_coverage == "any_licensed")
            and (node.scope == "global" or symbol in s.symbols)
        )
        covered = lower
        for start, end in intervals:
            if start > covered:
                break
            covered = max(covered, end)
        if covered < clock:
            raise ValueError(
                f"missing complete event coverage for {node.stream_id} at {clock.isoformat()}"
            )
        sector = self.state(symbol, clock).sector if node.scope == "sector" else None
        visible = [
            e
            for source in partitions
            for e in source.events
            if e.published_at <= clock
            and e.available_at <= clock
            and (node.access == "any_licensed" or e.access == "public")
        ]
        superseded = {e.supersedes_event_id for e in visible if e.supersedes_event_id}
        rows = [
            e
            for e in visible
            if e.event_id not in superseded
            and lower < e.published_at
            and (
                not node.categories
                or e.category in node.categories
                or set(node.categories) & set(e.tags)
            )
            and (
                not node.actors
                or (
                    e.details
                    and any(
                        actor in node.actors
                        for actor in [
                            getattr(e.details, "reporter", None),
                            getattr(e.details, "firm", None),
                            getattr(e.details, "analyst", None),
                        ]
                    )
                )
            )
            and (
                node.scope == "global"
                or (node.scope == "symbol" and symbol in e.symbols)
                or (node.scope == "sector" and sector in e.sectors)
            )
        ]

        def scalar(event):
            if node.value_field == "score":
                return (
                    event.score
                    if event.score_available_at and event.score_available_at <= clock
                    else None
                )
            detail = event.details
            if node.value_field == "analyst_target_after" and detail and detail.type == "analyst":
                return detail.target_after
            if (
                node.value_field.startswith("congress_amount_")
                and detail
                and detail.type == "congress"
            ):
                return getattr(detail, node.value_field.removeprefix("congress_"))
            if detail and detail.type == "economic":
                if node.value_field == "economic_actual":
                    return detail.actual
                if node.value_field == "economic_surprise":
                    return (
                        detail.actual - detail.consensus if detail.consensus is not None else None
                    )
            return None

        values = [scalar(e) for e in rows]
        if node.measure == "count":
            value = D(len(rows))
        elif any(v is None for v in values):
            value = None
        elif node.measure == "sum_score":
            value = sum(values, D(0))
        else:
            value = (
                scalar(max(rows, key=lambda e: (e.published_at, e.available_at, e.event_id)))
                if rows
                else None
            )
        audit = [
            {
                "event_id": e.event_id,
                "published_at": e.published_at.isoformat(),
                "available_at": e.available_at.isoformat(),
                "category": e.category,
                "title": e.title,
                "source_url": e.source_url,
                "access": e.access,
                "details": e.details.model_dump(mode="json", exclude={"text", "keyword_tags"})
                if e.details
                else None,
                "score": str(e.score)
                if e.score is not None and e.score_available_at <= clock
                else None,
            }
            for e in sorted(rows, key=lambda e: (e.published_at, e.event_id))[-50:]
        ]
        return value, audit


class SignalView(FeatureView):
    def __init__(self, book, symbol, now, previous, timeframe, portfolio, previous_portfolio):
        self.book, self.symbol, self.now, self.previous = book, symbol, now, previous
        self.timeframe = timeframe
        self.portfolios = (portfolio, previous_portfolio)
        self.feature_view = book.features.materialize(now, previous)
        self.evaluations = []

    def cutoff(self, offset=0):
        if offset not in (0, 1):
            raise ValueError("unsupported prior decision offset")
        return self.previous if offset else self.now

    def value(self, series_id, max_age_days, offset=0):
        return self.feature_view.value(series_id, max_age_days, offset)

    def audit(self, names):
        return self.feature_view.audit(names)

    def evaluate(self, node, offset=0, timeframe=None):
        clock = self.cutoff(offset)
        timeframe = timeframe or self.timeframe
        evidence = {}
        if isinstance(node, Constant):
            value = node.value
        elif isinstance(node, Multiply):
            left, right = (
                self.evaluate(node.left, offset, timeframe),
                self.evaluate(node.right, offset, timeframe),
            )
            value = left * right if left is not None and right is not None else None
        elif isinstance(node, Arithmetic):
            left, right = (
                self.evaluate(node.left, offset, timeframe),
                self.evaluate(node.right, offset, timeframe),
            )
            if left is None or right is None:
                value = None
            elif node.op == "divide":
                value = left / right if right else None
            else:
                value = {
                    "add": lambda: left + right,
                    "subtract": lambda: left - right,
                    "min": lambda: min(left, right),
                    "max": lambda: max(left, right),
                }[node.op]()
        elif isinstance(node, Market):
            value = self.evaluate(node.expression, offset, node.timeframe)
        elif isinstance(node, External):
            value = self.value(node.series_id, node.max_age_days, offset)
        elif isinstance(node, EventValue):
            value, events = self.book.event_value(node, self.symbol, clock)
            evidence = {"events": events}
        elif isinstance(node, CorporateValue):
            day = clock.astimezone(NY).date()
            rows = []
            for a in self.book.data.actions:
                if a.symbol != self.symbol or a.kind != node.kind or a.available_at > clock:
                    continue
                delta = (a.session_date - day).days
                matches = (
                    0 <= delta <= node.days
                    if node.window == "effective_next"
                    else -node.days <= delta <= 0
                    if node.window == "effective_past"
                    else clock - timedelta(days=node.days) <= a.available_at <= clock
                )
                if matches:
                    rows.append(a)
            value = D(len(rows)) if node.measure == "count" else sum((a.value for a in rows), D(0))
            evidence = {"known_actions": [a.model_dump(mode="json") for a in rows]}
        elif isinstance(node, PortfolioValue):
            snapshot = self.portfolios[offset]
            value = snapshot.get(node.field, D(0))
        elif isinstance(node, CalendarValue):
            day = clock.astimezone(NY).date()
            opening, closing = session_times(day)
            if node.field in {"minutes_after_open", "minutes_before_close"}:
                span = clock - opening if node.field == "minutes_after_open" else closing - clock
                value = (
                    D(span.days * 86400 + span.seconds) + D(span.microseconds) / 1_000_000
                ) / 60
            else:
                value = D(
                    {
                        "weekday": day.weekday(),
                        "day_of_month": day.day,
                        "month": day.month,
                        "year": day.year,
                        "session_of_month": len(sessions(day.replace(day=1), day)),
                    }[node.field]
                )
        else:
            history, key = self.book.history(self.symbol, timeframe, clock)
            value = self.book.cache.value(node, history, key)
            evidence = {
                "timeframe": timeframe,
                "completed_bars": len(history),
                "last_bar_available_at": history[-1].available_at.isoformat() if history else None,
            }
        if len(self.evaluations) < 100:
            self.evaluations.append(
                {
                    "expression": node.model_dump(mode="json"),
                    "clock": clock.isoformat(),
                    "value": str(value) if value is not None else None,
                    **evidence,
                }
            )
        return value
