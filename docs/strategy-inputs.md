# Indicators and external strategy inputs

Engine 1.3.0 extends the existing declarative rules with MACD, slow stochastic and reviewed external observations. Existing RSI, SMA, EMA, volume, average volume, momentum and rolling extrema remain available. No new provider key is needed to calculate indicators from imported daily OHLCV. Use period 200 for EMA200 and `multiply` for volume thresholds. Signals still execute at the next eligible open under the selected profile; indicators do not change execution, cash, FX or corporate-action rules.

## External source workflow

1. Retrieve a source snapshot under Market context, or import a CSV with `observation_date,available_at,value` and optional `release_date`. Timestamps must carry a timezone. Supply source URL, source name and an honest availability policy. Fear & Greed uses `FEAR_GREED_US` and values 0–100. Mark synthetic fixtures explicitly.
2. Inspect the exported observations, source hashes, coverage and publication policy. Imports initially remain viewing-only. A date for the represented period is not proof of its publication time. Review data rights separately from technical validation.
3. Explicitly acknowledge the publication policy and save a review note (20–2,000 characters). Approval creates a new immutable strategy-eligible revision linked to its unchanged source. Unknown publication timestamps cannot be waived. Approval records a human attestation; it cannot prove a vendor's historical claims.
4. Use an `external` expression with the exact series ID and a suitable maximum observation age. Monthly macro releases usually require more than the seven-day default. For a crossover, coverage must also include the preceding trading-session decision.
5. Select the eligible revision when scheduling backtests. Each run retains the revision IDs, content hashes and manifest hash; it never resolves a newer source automatically. Synthetic external inputs require the synthetic-data acknowledgement even with real price bars. Missing, stale, unreviewed, duplicate-series or changed inputs block scheduling/execution.

The CSV header is literal; no sample financial rows are provided here to avoid confusing invented values with historical data. Blank availability may be stored for viewing but prevents strategy approval. Empty values are errors, not filled observations. Boundaries: 5 MB CSV, 30,000 observations per snapshot, 20 selected series and 100,000 selected points total. Unsupported series require an explicit catalog/contract extension.

## Current sources and limits

FRED v1 initial-release snapshots retain a conservative availability policy: midnight New York after the first-release date. This is deliberately later than the release date; it does not claim the original intraday publication time or replay later revisions. Review the exported policy and coverage before approving a specific revision. `FRED_API_KEY` stays server-side. A reviewed `DEXSIUS` strategy input is a signal only: it does not populate the accounting FX dataset or waive its separate review.

The current public Cboe VIX history has unknown original publication times and stays viewing-only. Importing known timestamps requires a qualified source; a checkbox does not invent them. Fear & Greed has a manual import path, not an automatic historical feed. No real Fear & Greed history has been verified or imported by this implementation. Provide a permitted historical file/feed with original publication or defensible first-seen times, source attribution and revision policy. No additional key is needed for CSV import; a future provider may require one. Retrospective revised history without historical availability is suitable for viewing, not trades.

News, politics, geopolitical events and derived sentiment are not enabled strategy feeds. They require historical publication/first-seen/update metadata and a separately reviewed transformation contract. No news scraping, ML training, intraday trading or broker execution is included.

All full-period 2018–2025 reruns remain recorded as development/in-sample research with immutable published versions and run snapshots. Repeated improvement on that same history is not independent out-of-sample evidence. Annual/quarterly/monthly reports inspect the continuous portfolio without resetting cash or positions.
