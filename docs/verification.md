# Implementation milestones and verification

Current correctness gate: independent Milestone 3 review **passed for engine 1.2.0** after five confirmed baseline defects were fixed. The full backend suite now passes **54 tests**, including PostgreSQL, and the full four-run synthetic acceptance scenario was regenerated successfully. See `milestone-3-review.md`. Earlier 1.1.0 results remain immutable and require new runs to apply corrections.

The sections below retain the original implementation verification history.

## 1 — Foundation
Implemented modular backend/frontend, configuration, SQLAlchemy/PostgreSQL, Alembic, Compose and project conventions. Native API health and frontend startup/build verified. Migration upgrade/downgrade/reapply and schema-drift checks pass on SQLite and PostgreSQL 16. Docker runtime remains unverified because Docker is absent.

## 2 — Market data / clock
Implemented raw CSV/JSON import, Alpaca adapter, explicit synthetic demo, immutable revision hashes, FX, actions, coverage diagnostics, XNYS calendar and bounded strategy data views. Tests prove future blocking, FX publication gating, missing-session errors, holiday/early-close behavior and import validation. Live Alpaca credentials were unavailable.

## 3 — Simulation
Implemented Decimal ledger, next-open orders, costs, affordability, sizing, exposure/position/frequency limits, protective exits, splits/dividend receivables, marked final holdings, benchmark and analytics. Determinism, round-trip fees, FX valuation, flat/no-trade cases, splits, protective gaps and future-mutation tests pass. Simplified daily/full-fill conventions are documented.

## 4 — Declarative authoring
Implemented bounded typed expression trees, every requested indicator/operator, recursive visual editor, JSON editor, schema validation, draft revisions, publish/history/clone/archive/restore, parent versions and side-by-side definitions. API and frontend workflow tests pass; browser creation/validation/publication verified. Published versions have database immutability triggers.

## 5 — Profiles / jobs / experiments
Implemented shared editable profiles, snapshots, batch experiments, transactional PostgreSQL claiming, token ownership, heartbeat/progress, cancellation, visible stale/failure records and separate worker. Eight concurrent PostgreSQL claimers claimed eight distinct jobs. Snapshot and failure lifecycle tests pass.

## 6 — Dashboard / comparison
Implemented persistent run creation, equity/drawdown/benchmark charts, costs and statistics, filterable orders, trades/signals/ledger, open positions and incompatible-assumption warnings. Frontend TypeScript/production build and workflow tests pass. Synthetic results stay labeled.

## 7 — LLM authoring
Implemented configurable OpenAI-compatible provider interface, strict structured outputs, backend revalidation, persisted proposal preview, explicit draft acceptance and separate publication. Model/prompt/revision metadata retained. Missing-key and human-approval tests pass. Live provider calls remain unverified.

## 8 — Hardening / demonstration
Implemented immutable-input database triggers, bounded requests/trees/imports/queues, server-only credentials, restricted CORS and loopback deployment defaults, input hashes and synchronized documentation. The required four-run synthetic scenario passes version/profile immutability and later-price/FX mutation invariance. Measured results are in `demo-report.md`.

Original pre-review implementation checks: **45 backend tests passed**, including PostgreSQL migrations/rollback, eight-way concurrent claiming, complete worker persistence and immutable inputs. **9 frontend workflow tests passed**; TypeScript and Vite production build passed; Ruff lint/format checks passed; npm audit found **0 vulnerabilities**. Dependency deprecation notices and a frontend chunk-size advisory are disclosed, not hidden.

Live browser verification: created a visual MA strategy, saved and validated its draft, published version 1, selected the SGD profile and an explicit synthetic revision, acknowledged synthetic use, submitted a job, processed it in the separate worker, viewed filled orders/curves, and refreshed the results page successfully. A screenshot is retained in `.local/trading-lab-result.jpg`. The native API health check and frontend HTTP startup succeeded.

The complete four-run acceptance demonstration also passed against native PostgreSQL 16 with engine 1.1.0. The comparison page was inspected with three independently simulated portfolios, its sorted metrics table, and the synthetic-data disclosure; `.local/trading-lab-comparison.jpg` records that view. There were temporary Vite hot-reload connection resets during formatting; fresh navigation and result refresh succeeded afterward.

Provider hardening: official aggregation rules show that Alpaca daily volume includes extended-hours prints. Complete bars are now gated to assumed 20:15 New York publication, evaluated at 20:30, rather than exposing final daily volume at regular close. A dedicated mock-provider test verifies pagination, raw/IEX parameters, evening availability and explicit entitlement errors. Engine version is 1.1.0; old completed results remain unchanged.

Release status remains **locally verified synthetic MVP; Docker and credentialed real-data/LLM validation outstanding**, rather than claiming a real-data production deployment.

Final data-quality guards also reject unfinished API daily bars and block unreviewed real raw corporate-action histories. Both have dedicated passing tests; synthetic fixtures remain visibly labeled and unaffected.
