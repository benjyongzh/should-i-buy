# Roadmap

Implement in order: (1) foundation, migrations and health; (2) immutable imports/calendar/FX; (3) deterministic simulation and analytics; (4) declarative strategy/version CRUD and editor; (5) profiles, experiments and leased worker; (6) results and comparisons; (7) reviewable LLM authoring; (8) hardening and demonstration.

The final verification report records actual checks and limitations. A scaffold alone is not completion.

Current status: all eight milestones have local implementations; 45 backend and 9 frontend tests pass, with a complete PostgreSQL/SQLite synthetic acceptance scenario. The release verification backlog is Docker deployment, live Alpaca/LLM connectivity and real 2019–2022 source-data coverage. See `verification.md` and `known-limitations.md` for the exact boundary.

Deferred: model training/registry and walk-forward scheduling; intraday events/storage; paper trading; ensembles; explicitly separately authorized brokerage adapters. Future feature providers receive only a clock-bound data view, and trainers must require label-maturity timestamps <= training cutoff. No modern LLM is used as a historical trading oracle.
