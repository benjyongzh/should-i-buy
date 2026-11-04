# Implementation milestones and verification

## Deployment and real-data phase — 2026-11-04

Actual current checks: **63 backend tests passed in a disposable Linux container**, including isolated PostgreSQL migrations/check/rollback/reapply, immutable inputs, concurrent claiming and persisted worker results. The test process was deliberately given dummy Alpaca/LLM credentials; real HTTPX requests remained blocked and all tests passed. The native credential-isolation rerun passed **62 cases with the optional PostgreSQL case skipped**, because its URL was unset. Earlier native PostgreSQL checks used loopback 55432; container checks use only the isolated Compose database and random test-owned schemas. **10 frontend tests** and the TypeScript/Vite production build previously passed; the frontend is unchanged by this test-only patch. Ruff lint/format pass. Existing third-party deprecation notices and the build chunk-size advisory remain visible. See [testing.md](testing.md) for the unit/integration coverage map and limitations.

Credential audit: the missing-key LLM test previously inherited the server environment and could attempt a live call after keys were configured. An autouse fixture now clears inherited provider credentials/model in the test process, clears settings caches and blocks unmocked synchronous/asynchronous HTTPX transport requests. Two regression tests verify these guards. Explicit MockTransport provider fixtures and in-process API tests remain functional; that patch did not edit `.env` or running services. No real credentials were supplied or used for those automated tests. Subsequent credentialed integration checks are recorded below.

Inspected both Compose configurations, Dockerfiles, Nginx, environment loading, data/LLM adapters and the import UI. Fixed nested `.env` exclusion in Docker contexts, added explicit SIP/IEX feed selection and retained the dividend-completeness attestation on Alpaca imports. Feed/error/pagination tests use controlled HTTP responses; import tests check persisted action/attestation data and revision hashes. LLM HTTP tests cover valid strict output, invalid schema, refusal, truncation and provider error, alongside existing explicit draft acceptance/publication workflow tests. No engine behavior or dataset immutability rule changed.

**Docker subsequently VERIFIED after the user installed Desktop:** Windows/WSL 2 Linux engine 29.9.2, Compose 5.6.1. Both image builds, migration exit 0, `alembic check`, PostgreSQL/API/frontend health and independent worker processing passed in isolated project `trading-lab-verify-20261104080751` at loopback port 18080. All **61 backend tests** also passed in the Linux API container, including PostgreSQL; container Ruff checks passed. Nginx served the SPA/assets and proxied API/DB health. Complete dataset/version/profile/run/result comparisons passed after service restart and after container recreation with the retained volume. A second HTTP-submitted job completed after recreation with exactly the same result. The engine remains 1.2.0. Removing an unnecessary recursive env-template exception fixed Docker build-context traversal of an inaccessible test cache. See the runbook for exact evidence and hashes.

**Credentialed Alpaca checks now VERIFIED:** read-only paper account authentication at `https://paper-api.alpaca.markets/v2/account` returned 200. Historical SIP data correctly uses the separate `https://data.alpaca.markets/v2` base. The UI's actual import API, through Nginx, imported 1,259 real raw SPY daily bars for 2018–2022, no missing sessions. The revision remains unreviewed and has no FX/actions; scheduling was correctly rejected with 422 and created no run. Dataset/hash/evidence are recorded in the runbook. Interactive browser import and source publication-vintage certification were not performed.

**BLOCKED:** complete real FX/action reconciliation and the three real SPY runs/independent selected-fill comparison; live LLM generation/modification. An OpenAI key was supplied, but the temporary GPT-5.4 Mini live request returned HTTP 429 with `credit_balance_exhausted`/`insufficient_quota`. No successful completion, proposal acceptance or publication occurred. The saved model field was blank at inspection; GPT-6 Luna is now the recommended cost-focused candidate, not a benchmarked or live-validated winner. No real returns were generated. Standalone Ubuntu/external-DB deployment, Windows reboot autostart and backup/recovery remain unverified.

Free-first source plan: test Alpaca historical SIP, assess ALFRED DEXSIUS initial-release observations with actual publication dates, and reconcile US SPY issuer corporate actions. Historical SIP's documented free access must be checked on the user's account. Fed weekly publication can exceed the default seven-day FX age; any explicit use of the existing 14-day setting must be recorded. Revised equity bars and assumed evening timestamps do not constitute strict vendor-vintage certification. Exact credentials, safe isolated Docker commands, source-review steps and pending acceptance calculations are in [deployment-verification.md](deployment-verification.md) and [data-providers.md](data-providers.md).

## Earlier milestone evidence

Current correctness gate: independent Milestone 3 review **passed for engine 1.2.0** after five confirmed baseline defects were fixed. At that gate the full backend suite passed **54 tests**, including PostgreSQL, and the full four-run synthetic acceptance scenario was regenerated successfully. See `milestone-3-review.md`. Earlier 1.1.0 results remain immutable and require new runs to apply corrections.

The sections below retain the original implementation verification history.

## 1 — Foundation
Implemented modular backend/frontend, configuration, SQLAlchemy/PostgreSQL, Alembic, Compose and project conventions. Native API health and frontend startup/build verified. Migration upgrade/downgrade/reapply and schema-drift checks pass on SQLite and PostgreSQL 16. Docker was unavailable during the original milestones; subsequent Windows Desktop verification is recorded above.

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

Original release status was **locally verified synthetic MVP; Docker and credentialed real-data/LLM validation outstanding**. Docker Desktop verification has since passed as recorded above; credentialed real-data/LLM validation remains outstanding. This is not a verified real-data production deployment.

Final data-quality guards also reject unfinished API daily bars and block unreviewed real raw corporate-action histories. Both have dedicated passing tests; synthetic fixtures remain visibly labeled and unaffected.
