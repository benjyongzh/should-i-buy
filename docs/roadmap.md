# Roadmap

Implement in order: (1) foundation, migrations and health; (2) immutable imports/calendar/FX; (3) deterministic simulation and analytics; (4) declarative strategy/version CRUD and editor; (5) profiles, experiments and leased worker; (6) results and comparisons; (7) reviewable LLM authoring; (8) hardening and demonstration.

The final verification report records actual checks and limitations. A scaffold alone is not completion.

**Mandatory gate between milestones 3 and 4:** independently review the backtesting engine for look-ahead bias and accounting errors. Reproduce findings with adversarial tests, resolve correctness defects, and have fixes independently verified before strategy-editor work proceeds. See `milestone-3-review.md`. The editor predates this added gate in the current checkout; the retroactive gate is now cleared for engine 1.2.0 following independent fix verification and the full regression/acceptance replay.

Current status: all eight milestones have local implementations; 54 backend and 9 frontend tests pass, with a complete PostgreSQL/SQLite synthetic acceptance scenario. The release verification backlog is Docker deployment, live Alpaca/LLM connectivity and real 2019–2022 source-data coverage. See `verification.md` and `known-limitations.md` for the exact boundary.

Deferred: model training/registry and walk-forward scheduling; intraday events/storage; paper trading; ensembles; explicitly separately authorized brokerage adapters. Future feature providers receive only a clock-bound data view, and trainers must require label-maturity timestamps <= training cutoff. No modern LLM is used as a historical trading oracle.
