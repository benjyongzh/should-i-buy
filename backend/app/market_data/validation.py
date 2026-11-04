from app.market_data.calendar import decision_timestamp, session_times, sessions
from app.market_data.view import fx_at
from app.schemas.domain import DatasetInput, ProfileConfig


def validate_dataset(data: DatasetInput) -> dict:
    keys = [(b.symbol, b.session_date) for b in data.bars]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate candle symbol/session")
    for bar in data.bars:
        _, close = session_times(bar.session_date)
        if bar.available_at < close or bar.source_timestamp < close:
            raise ValueError(
                f"{bar.symbol} {bar.session_date}: completed bar timestamp precedes close"
            )
        if bar.available_at < bar.source_timestamp:
            raise ValueError("bar availability precedes source timestamp")
    fx_keys = [(r.observed_at, r.available_at) for r in data.fx]
    if len(fx_keys) != len(set(fx_keys)):
        raise ValueError("duplicate FX observation")
    action_keys = [(a.symbol, a.session_date, a.kind) for a in data.actions]
    if len(action_keys) != len(set(action_keys)):
        raise ValueError("duplicate corporate action")
    for action in data.actions:
        opening, _ = session_times(action.session_date)
        if action.available_at > opening:
            raise ValueError("corporate action must be known by effective session open")
    coverage = {}
    for symbol in sorted({b.symbol for b in data.bars}):
        dates = sorted(b.session_date for b in data.bars if b.symbol == symbol)
        missing = sorted(set(sessions(dates[0], dates[-1])) - set(dates))
        coverage[symbol] = {
            "start": str(dates[0]),
            "end": str(dates[-1]),
            "bars": len(dates),
            "missing_sessions": [str(d) for d in missing],
        }
    return coverage


def validate_coverage(data: DatasetInput, profile: ProfileConfig) -> None:
    if not data.synthetic and not data.corporate_actions_reviewed:
        raise ValueError(
            "Raw historical data requires reviewed corporate-action coverage. Supply all effective splits, attest the source review, and import a new revision before backtesting."
        )
    days = sessions(profile.start_date, profile.end_date)
    if not days:
        raise ValueError("profile contains no trading sessions")
    keys = {(b.symbol, b.session_date) for b in data.bars}
    for symbol in sorted(set(profile.symbols + [profile.benchmark])):
        missing = [d for d in days if (symbol, d) not in keys]
        if missing:
            raise ValueError(f"missing {len(missing)} sessions for {symbol}; first: {missing[0]}")
    if profile.account_currency == "SGD":
        for day in days:
            for timestamp in (*session_times(day), decision_timestamp(day, data.decision_time)):
                fx_at(data.fx, timestamp, profile.max_fx_age_days)
