# Architecture and implementation plan

## Historical capability extension

The validated DSL now has opt-in timing/universe/conditional-sizing policies and
publication-gated operands. `InputBook` constructs protected completed prefixes;
`SignalView` evaluates rules; `event_engine` coordinates UTC event clocks, Decimal
ledger operations and daily/intraday marks. Existing daily simulation remains a
separate compatibility path. Source revisions are reviewed append-only records;
queue admission and workers verify frozen manifests. The LLM proposes bounded
plans and never runs generated code. See [capabilities](strategy-capabilities.md).

Trading Lab is a single-user research system: Vite/React → FastAPI → PostgreSQL, with a separate polling Python worker. No broker execution exists. The declarative interpreter has no I/O or arbitrary code execution. The simulator owns event ordering, execution quotes, Decimal ledgers, and a clock-filtered data view.

## Decisions

1. PostgreSQL is the deployment database. SQLite is supported for a frictionless single-worker local test/development mode; concurrency acceptance is tested separately on PostgreSQL.
2. Immutable normalized dataset revisions include candles, FX, and corporate actions together. Hashes cover the sorted validated content. Imported revisions are never patched. Runs snapshot profiles and reference immutable versions/revisions.
3. PostgreSQL jobs use row locks and conditional token ownership. Short transactions claim jobs; progress checkpoints renew leases. Stale jobs fail visibly and can be resubmitted, rather than risking duplicate automatic retries.
4. Money uses Decimal; result JSON stores monetary amounts as decimal strings. Charts convert these to numbers for display only.
5. Daily market orders fill next session open. Missing coverage rejects a run. Raw price-only returns are explicitly labeled unless a source attests complete dividends. No silent adjusted prices, FX substitution, or synthetic fallback.
6. LLM authoring proposes validated JSON. Accepting edits a draft; publishing remains a separate user action. Credentials never leave the server.
7. Context snapshots (VIX/FRED/manual CSV) are immutable and separate from accounting datasets. A review creates a new strategy-eligible revision with source lineage; unknown publication times remain ineligible. Runs pin selected revision IDs/hashes and the worker verifies them. The interpreter receives only current/prior clock-eligible scalar values, never future source history. External signals cannot supply accounting FX or corporate actions. Continuous year/quarter/month reports derive from saved portfolio marks and events without resetting capital. Development iterates over all of 2018–2025. See `strategy-inputs.md` and `continuous-research.md`.

## Boundaries

- `schemas`: strict external contracts, bounded recursive DSL.
- `market_data`: validation, calendar, CSV/API providers, timestamp filtering.
- `strategies`: pure indicator/condition interpreter.
- `portfolio`, `backtesting`, `analytics`: accounting, chronological simulation, documented statistics.
- `services`: immutable storage, version publication, job scheduling/ownership.
- `api`, `llm`: transport boundaries; no simulation inside HTTP handlers.
- `frontend`: editable rules and profiles, explicit data selection, persistent job/results views.

## Validation gates

Each milestone adds tests before progressing: migration/health; data and temporal filtering; deterministic accounting; DSL/versioning; worker/snapshots; UI/results; LLM validation; full synthetic demonstration. See roadmap for measured status. Docker runtime verification requires a Docker-capable host.
