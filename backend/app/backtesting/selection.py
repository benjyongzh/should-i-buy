from app.backtesting.advanced_validation import candidates
from app.strategies.interpreter import condition, numeric


def select_universe(config, profile, book, clock, views):
    eligible = candidates(config, profile, book, clock)
    policy = config.universe
    if not policy:
        return eligible, []
    ranked = []
    audit = []
    for symbol in eligible:
        view = views[symbol]
        bars, _ = book.history(symbol, view.timeframe, clock)
        passed = condition(policy.filter, bars, view)
        rank = numeric(policy.rank_by, bars, features=view) if policy.rank_by else None
        state = book.state(symbol, clock) if book.universe else None
        included = passed is True and (policy.rank_by is None or rank is not None)
        sector = state.sector if state else None
        preference = (
            policy.prefer_sectors.index(sector)
            if sector in policy.prefer_sectors
            else len(policy.prefer_sectors)
        )
        audit.append(
            {
                "symbol": symbol,
                "sector": sector,
                "state_available_at": state.available_at.isoformat() if state else None,
                "filter_result": passed,
                "rank": str(rank) if rank is not None else None,
                "eligible": included,
            }
        )
        if included:
            ranked.append(
                (preference, -rank if rank is not None and policy.descending else rank or 0, symbol)
            )
    selected = [row[2] for row in sorted(ranked)[: policy.top_n]]
    for row in audit:
        row["selected"] = row["symbol"] in selected
    return selected, audit
