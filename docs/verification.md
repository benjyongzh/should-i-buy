# Implementation milestones and verification

## Historical strategy capabilities — engine 2.0.0, 2026-11-05

**Verified:** independent financial/causal gate before editor work; 183 backend
including PostgreSQL and 31 frontend tests; lint/format/build; isolated Docker
images/migration 004/drift and worker connectivity; 17 real Chromium workflow
checks; exact synthetic multi-source intraday replay and independent SGD fill
arithmetic; two live LLM planning/draft/publication checks. Existing Alpaca keys
returned 78 SPY five-minute intervals (2018-01-02) and 17 AAPL/MSFT news records
(2020-01-02); these real source slices remain raw/unreviewed.

Restart preserved ten earlier result hashes, two new synthetic results, fourteen
source exports, LLM versions/profile and the reviewed daily dataset. Own database
container and all 22 unrelated containers remain unchanged; only own application
services were updated on loopback port 18080.

**Unverified/blocked:** real event/sector-driven and full-period intraday
performance, complete original news versions, live analyst entitlement/key,
reviewed historical classifications and actual Congress collection/publication
history. Typed Congress imports/rules are tested, not a real-data archive.
See [actual evidence and run IDs](historical-capabilities-verification-2026-11-05.md),
[capability semantics](strategy-capabilities.md) and [what to provide](historical-input-checklist.md).
Earlier dated verification below remains historical evidence for its named engine.

## Performance timeline and cash comparisons — 2026-11-05

Completed reports and Compare now share a zoomable account-value timeline with
fill, contribution/corporate-action and optional decision markers. Chart/date
selection opens the saved account snapshot, readable rule outcomes, recorded
reasons and original audit fields. Published versions and different strategies
can share the chart; saved buy-and-hold and modeled zero-interest cash references
are deduplicated under shared assumptions. Different currencies are not overlaid.
Decimal-string percentages now display correctly in exposure/period reports.

**Verified:** 140 backend tests including PostgreSQL, 26 frontend tests, Ruff
lint/format, Prettier and production build. A disposable Chromium browser passed
12 deployed desktop/mobile checks: actual chart selection and zoom, markers,
normalized performance, three-strategy comparison, cash/SPY deduplication,
selected real partial-sale audit, mobile chart size, and no runtime/API failures.
The browser found and verified a fix for the audited-run selector's accessible
name. Screenshots were visually inspected. This is bounded browser verification
of the report/comparison screens, not an exhaustive application/accessibility audit.

The read-only cash endpoint uses frozen initial capital and recorded external
deposits in Decimal; interest and costs are explicitly zero. No engine behavior,
historical result, strategy version, provider or schema changed. Engine remains
1.4.0. Only this project's API/frontend were recreated on loopback port 18080;
the worker/database and unrelated containers were left in place. Final retained
hash/container/cash-curve checks are archived in
`.local/ui-timeline-20261105/verification-final.json`. See
[timeline usage and interpretation limits](performance-timeline.md).

Postdeployment checks matched ten complete retained result hashes and the
reviewed dataset export, independently reconciled all 7,407 cash-baseline marks
for those runs, and confirmed unchanged worker/database IDs plus all 22 unrelated
container IDs, start times, restart counts and port bindings.

## Funding and granular trade controls — 2026-11-05

Engine **1.4.0** is deployed in the isolated Trading Lab project. Strategies can
choose daily/weekly/monthly/once entry decisions, repeated additions, equity/cash
fractions, fixed order budgets, target allocations and partial exits. Profiles
independently configure fixed monthly account-currency contributions, default
zero. Returns/drawdown/period reports exclude external capital; actual balance,
contributed capital, investment P&L and eligible investor IRR are separate.

**Verified:** 136 backend tests including PostgreSQL, 20 frontend tests, Ruff
lint/format, Prettier and production build. Independent review passed before
editor changes; legacy configuration/profile/full-result hashes and four complete
financial baselines match exactly. Three real SPY Q1-2019 funded smoke cases and
three exact repeats completed; separate stdlib arithmetic reconciled 183 strategy
marks, 26 fills/18 exits and 183 independently reconstructed benchmark marks.
Live `gpt-6-luna` generation/modification passed the new schema, draft isolation
and separate publication checks.

Docker images built, migrations ran at head, and only the project's API/worker/
frontend were recreated and restarted on existing loopback port 18080. All six new
results, four retained legacy results, the reviewed dataset and new LLM versions
persist unchanged. The project's PostgreSQL container/volume remained in place;
all 22 unrelated container IDs, start times, restart counts and published ports
match the predeployment record. API/database/frontend are healthy; worker runs.

**Unverified in this extension:** a full 2018–2025 funded sweep and new interactive
browser layout review. Earlier real full-history 1.3 acceptances remain historical
evidence, not 1.4 funded results. See [configuration semantics](funding-and-trade-controls.md),
[dated test results and run IDs](funding-verification-2026-11-05.md), and
[independent review](milestone-3-review.md). No new credentials were needed.

## Real SPY acceptance executed — 2026-11-05

**SPY's combined-data blocker is cleared under the documented reference-FX research policy.** New immutable dataset `051e4285-e374-4b44-b82c-a54ffc8a6a6e` contains2,514 raw SIP bars,2,494 reviewed initial-release FX observations and 40 issuer dividends for 2016–2025. Source review supplies the missing Alpaca action fields and corroborates all 40 amounts with dated original pre-US-open publications. One anomalous2018-07-23 FX availability is delayed to2018-08-01 after the evidenced weekly release. Missing first releases remain omitted. All6,033 clocks pass the explicit14-day age limit; full source assumptions and archive-flag dispositions are retained.

Buy/hold, SMA20/50 and RSI14 completed on real data for **2018–2025** and supplemental **2019–2022**; all six repeats are exactly identical. Independent stdlib arithmetic matched9,057 strategy signals/marks and9,057 benchmark marks,75 strategy fills,262 strategy ledger entries, dividends/receivables, costs and reporting metrics. Input/result hashes and annual linked returns/order/fee totals revalidate. Prior input revisions/results remain unchanged. The isolated API/database/frontend remain healthy and the worker persisted all jobs. No application/engine behavior or frontend code changed in this source/integration pass. **121 backend tests including PostgreSQL** and Ruff lint/format pass; frontend's existing17-test/build result remains the latest check.

See [actual returns, run IDs, independent calculations and limits](real-spy-acceptance-2026-11-05.md). These are real-data model results with95% equity entry sizing, not broker-executable FX, certified original price vintages or out-of-sample evidence. QQQ/SMH/XLE source/action acceptance, original intraday FX/price-vintage certification and real Fear & Greed/news feeds remain unverified. Earlier sections below record their dated states; their SPY blocker statements are superseded by this result.

## Strategy indicators and external inputs — 2026-11-05

Engine **1.3.0** implements MACD, slow stochastic and publication-gated external series in declarative strategy rules. The mandatory independent review passed after finding and fixing previous-crossover split contamination; the finding, adversarial reproduction and independent recheck are in [Milestone 3 review](milestone-3-review.md). Four complete engine 1.2 synthetic financial baselines remain exactly equal. Existing strategies, datasets and completed results were not rewritten.

**Verified:** 109 backend tests including PostgreSQL; 17 frontend tests; Ruff lint/format, Prettier and TypeScript/Vite build. Tests cover hand-calculated oscillator seeds/smoothing/warm-up, delayed releases and prior clocks, missing/stale errors, future-mutation isolation, immutable source review revisions, manifest/hash rejection, worker pinning, synthetic acknowledgement and comparison compatibility. The independent reviewer separately checked 2,520 oscillator calculations, a SGD split/dividend/fee/FX hand-ledger, exact reruns and 74 focused tests.

The isolated Docker project rebuilt and started successfully on `127.0.0.1:18080`. Deployed API → PostgreSQL → separate worker completed three explicitly synthetic MACD/stochastic/external smoke runs; the external rerun was exactly identical. Source review created a new immutable revision; its parent export stayed unchanged. Unreviewed input scheduling returned422. Existing baseline result hash remains `211578ea941eaa5a7a49f0c21c0bf7badccdf5c3ab4ff698b0f50c91ea0557aa`. Private smoke evidence: `.local/strategy-inputs-live-20261105/report.json`.

**Blocked/unverified:** real financial acceptance still requires qualified FX/corporate-action review; the actual SPY revision still rejects scheduling. No real Fear & Greed history or qualified automatic feed was imported. VIX with unknown original publication times cannot be approved for signals. Browser interaction/layout was not separately exercised; frontend workflows use component tests and deployed HTTP/assets. Source rights/publication claims remain a human review obligation, not proven by an approval checkbox. See [source workflow and required inputs](strategy-inputs.md). The earlier sections below retain their dated counts and engine 1.2 state.

After final app-container recreation, source/review revisions, dataset hashes and all three complete results survived unchanged; the latest frontend asset returned 200 with the new controls. Migrations completed and `alembic check` found no drift. The isolated database container/volume was retained. Before/after snapshots verified all **21 existing homelab containers** had unchanged identity, uptime and ports. Live configured `gpt-6-luna` generation produced a validated MACD proposal; modification added stochastic and external operands. Drafts stayed unchanged until explicit acceptance, publication remained separate and prior versions stayed unchanged. These are authoring smoke checks, not strategy quality/performance evidence. Private records: `persistence.json` and `llm-report.json` in the same evidence directory.

## Continuous development and additional data — 2026-11-05

User-selected workflow now iterates over all of 2018–2025, retaining published revisions and every run, with continuous year/quarter/month analysis rather than a mandatory holdout split. Added a separate immutable market-context library and UI. All nine live context imports pass; SPY/QQQ/SMH/XLE each have 2,514 real raw SIP bars for 2016–2025 including warm-up, no calendar gaps, and remain unreviewed. Current checks: **83 backend tests including PostgreSQL**, **12 frontend tests/build**, Ruff, applied migration 003 and no schema drift. Isolated stack is healthy at loopback 18080. Engine 1.2.0 and old result hashes are unchanged. No real return is claimed; FX/action acceptance is still required. See [continuous research evidence](continuous-research.md).

## Current Linux verification — 2026-11-05

FRED follow-up: supplied key authenticated successfully; retrieved 1,266 numeric initial-release USD/SGD observations and omitted 60 explicit missing values. A candidate CSV and retained-source audit are prepared, but not imported/accepted: 266 archival release-date checks found unavailable pages and date/observation mapping discrepancies requiring review. The candidate fails the default seven-day FX age at 1,073 requested-period clocks; the explicit 14-day setting passes all 3,024 clocks. Current backend total is **73 passing tests including PostgreSQL**, with Ruff lint/format passing. Engine/profiles remain unchanged. See [FX source review](fx-data-review.md).

Fresh checks on this homelab verified Docker build/start, migrations/head/drift, frontend/API/PostgreSQL connectivity, separate worker execution, persistence after restart/container recreation, and identical repeat synthetic results. Project `trading-lab-linux-verify-20261104` publishes only `127.0.0.1:18080` and owns its PostgreSQL volume; existing containers/data were untouched. All 63 backend tests including PostgreSQL, 10 frontend tests, production build and Ruff lint/format passed in Linux containers.

Live Alpaca import again returned 201: 1,259 real raw SPY SIP bars, no missing sessions, hash matching the earlier reported import. Live `gpt-6-luna` generation **and modification now pass**, including schema validation, separate proposal acceptance/publication, and preserved earlier versions. The earlier LLM quota failure is historical. Qualified FX/action review and the three real SGD backtests/independent reconciliation remain **blocked**. No real return is claimed. See [current evidence and required inputs](verification-linux-2026-11-05.md).

The following dated sections retain earlier evidence and limitations as they stood then; current status above supersedes their pending Linux/LLM statements. Earlier private Windows artifacts were not present in this checkout.

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
