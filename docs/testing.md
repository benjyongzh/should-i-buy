# Automated testing before credentials

## Historical capability extension checks

Current extension: **183 backend tests including PostgreSQL** and **31 frontend
tests** pass; Ruff lint/format, Prettier and production build pass. The independent
Milestone 3 review includes 16 causal/financial groups, 2,041 exact Decimal
indicator comparisons, protected-source/identity adversaries and legacy full-result
baselines. Mocked provider checks cover minute aggregation/missing intervals,
news versions/keyword lineage and ratings nominal targets/version clocks/token
redaction. UI tests cover public-event operands, historical timing/selection/sizing,
source review/availability, LLM blocked plans/draft-only acceptance and retained
intraday timeline marks. Live entitlement checks are separate evidence.

Latest reporting follow-up (2026-11-05): **140 backend tests including PostgreSQL,
26 frontend tests**, lint/format/build pass. Four cash-reporting tests check
Decimal capital-flow chronology and API/result isolation. Six added frontend
checks cover timeline dates/reasons, chart selection, version/strategy overlays,
reference deduplication, currency isolation and missing marks. Twelve bounded
real Chromium checks additionally verify deployed desktop/mobile charts and
interactions. Engine behavior is unchanged. See [reporting evidence](performance-timeline.md).

Current funding/sizing extension (2026-11-05): **136 backend tests including
PostgreSQL**, 20 frontend tests, Ruff lint/format, Prettier and production build
pass. `test_funding_trading.py` adds 15 financial, causal, schema and immutable
API-worker cases. PostgreSQL executes a funded policy in a random owned schema.
Independent financial review passed before editor work. Separate live checks
include three real SPY funded smoke cases/three exact repeats, stdlib accounting
reconciliation, LLM authoring and application restart persistence. See
[dated evidence](funding-verification-2026-11-05.md). Older counts below describe
their dated phases.

Real-source acceptance follow-up (2026-11-05): **121 backend tests including PostgreSQL** and Ruff lint/format pass. Twelve `test_combined_source_review.py` cases cover weekly-release floors, evidenced later publication, invalid chronology, missing-value preservation, DST, original USD versus later FX notices, minute precision, CDI-date isolation and rejection of naive/late/unrelated evidence. Later payment-date evidence gates the complete action timestamp and cannot be waived past the effective open. Credentialed data review and six real runs/six identical repeats are separate from mocked pytest. A stdlib-only reconciliation checks every strategy/benchmark daily cash/equity mark, all strategy signals/quantities/fills and dividend/fee accounting. See `real-spy-acceptance-2026-11-05.md`. Frontend code is unchanged; its latest17-test/build result is retained. No engine behavior changed.

Engine 1.3 strategy-input checks (2026-11-05): **109 backend cases including PostgreSQL**, **17 frontend tests**, production build and lint/format pass. `test_strategy_inputs.py` adds26 cases for MACD/stochastic hand calculations and warm-up, declarative bounds/hash compatibility, publication/previous-clock isolation, split-day mixed crossover, independently calculated SGD fills/gross replay, future-mutation/repeat invariance, explicit source review, frozen worker revisions and content/manifest rejection. Frontend tests exercise operand controls, CSV import, review acknowledgement, exact source selection/synthetic acknowledgement and external-manifest comparison warnings. The independent financial/causal review and separate live Docker checks are recorded in `milestone-3-review.md` and `verification.md`. Automated tests use synthetic fixtures or mocked providers, not real historical performance.

Current research-extension checks (2026-11-05): **83 backend tests pass including PostgreSQL**, **12 frontend tests/build pass**, and Ruff passes. New tests cover context source bounds/credentials, first releases/pagination/DST/source day, long-history release windows and late first releases, VIX unknown availability, exports/hash preservation, SQLite/PostgreSQL update/delete rejection, and continuous-period arithmetic/year-boundary/zero-equity behavior. Engine 1.2.0 is unchanged; no engine/editor review gate was bypassed. Live source imports and old-result reconciliation are recorded separately in `continuous-research.md`.

Latest FX-preparation checks (2026-11-05): **73 backend cases passed including PostgreSQL**, with ten new cases for conservative FRED publication gating, DST, missing values, invalid/duplicate/reversed source rows, observation-based age limits, old/new Fed table layouts, year boundaries, sanitized provider errors and preservation/flagging of incomplete source evidence. Tests also clear inherited `FRED_API_KEY`. This adds a standalone source-preparation utility; engine 1.2.0 behavior is unchanged. The current source audit and any unresolved evidence are recorded in `fx-data-review.md`.

Current result (2026-11-04): **63 backend cases passed in a disposable Linux container**, including isolated PostgreSQL integration. The process was deliberately given nonempty dummy Alpaca/LLM credentials to verify isolation. Native Windows: **62 passed, one PostgreSQL test skipped** because `TEST_POSTGRES_URL` was unset. Ruff lint and formatting pass. The unchanged frontend previously passed **10 workflow tests** and its production build, including a Linux image build.

The backend total includes unit and integration tests; it is not a count of unit tests alone. No code-coverage percentage has been measured.

| Layer | Main coverage | Files under backend/tests |
| --- | --- | --- |
| Financial unit/regression tests | Next-open execution, Decimal cash/fees/P&L, affordability, exposure, order limits, split accounting, dividend entitlements/payment, final marks and metrics | `test_engine.py`, `test_risk_and_metrics.py`, `test_corporate_actions.py` |
| Causality and independent-review regressions | Future price/volume/FX isolation, publication gating, chronological opening/protective fills, post-cost risk limits, malformed timestamps and total-loss behavior | `test_temporal_data.py`, `test_milestone3_review.py` |
| Strategy units | Indicators, warm-up, comparisons/crossover events, expression trees and strict schema bounds | `test_strategy.py` |
| Provider boundary units | Mocked Alpaca SIP/IEX parameters/pagination/availability and errors; strict LLM response, invalid schema, refusal, truncation and HTTP errors | `test_providers.py`, `test_llm_client.py` |
| Historical FX preparation | Initial-release normalization, conservative publication gating/DST, missing/invalid inputs, age limits, archive parsing and sanitized errors | `test_fred_preparation.py` |
| Credential/network isolation | Inherited keys/model cleared; synchronous and asynchronous unmocked HTTPX requests fail before network access | `conftest.py`, `test_provider_isolation.py` |
| API/SQLite integration | Validated imports, retained feed/actions/attestations and hashes, publish/schedule/worker/result lifecycle, immutable snapshots, cancellation/failure and explicit LLM draft acceptance | `test_workflow.py`, `test_providers.py`, `test_foundation.py` |
| PostgreSQL integration | Migrations/check/rollback/reapply, immutable-input enforcement, eight concurrent job claims and persisted worker result in a random test-owned schema | `test_postgres.py` |

Frontend `src/pages/workflows.test.tsx` tests editor/profile/import/result workflows with a mocked API. It does not contact Alpaca or an LLM. Actual Docker HTTP/worker/restart tests are separate deployment smoke checks, recorded in `deployment-verification.md`.

## Credential isolation

An audit found that the missing-key LLM workflow test previously inherited configured environment variables. That could have enabled a live request after a developer configured keys. The autouse backend fixture now clears `LLM_API_KEY`, `LLM_MODEL`, `ALPACA_API_KEY`, `ALPACA_SECRET_KEY` and `FRED_API_KEY` in the **test process**, clears cached settings, and blocks real HTTPX transports. Provider tests explicitly construct settings with fixture keys and use `MockTransport`; FastAPI's in-process TestClient transport continues to work. Both synchronous and asynchronous HTTP boundaries have regressions. The fixture does not edit `.env` or change running services.

The full suite passed with visibly fake `TEST_SENTINEL_NOT_A_REAL_KEY` values supplied before pytest startup. No real user key was supplied or used. Ordinary pytest execution must remain credential-independent; live provider smoke tests should be explicit separate operations rather than additions to this suite.

## Running checks

From `backend`, in PowerShell:

```powershell
..\.venv\Scripts\python -m pytest -q
..\.venv\Scripts\python -m ruff check .
..\.venv\Scripts\python -m ruff format --check .
```

For PostgreSQL integration, set `TEST_POSTGRES_URL` in that shell to a **dedicated test database**, then rerun pytest. The test creates/removes a random schema; it must never be pointed at an unrelated production database. The current Docker verification uses its isolated bundled database and a disposable test container. Local evidence is `.local/provider-isolation-tests.log` and `.local/docker-provider-isolation-tests.log`; image build evidence is `.local/docker-test-isolation-build.log`.

From `frontend`: `npm test` and `npm run build`.

## What passing tests do not establish

Tests do not establish Alpaca account entitlements, actual 2018–2022 bar coverage, original publication vintages, complete SPY actions, qualified historical FX, live model compatibility or the quality of generated strategies. Synthetic and mocked inputs verify behavior under controlled conditions. Real historical acceptance still requires source review, immutable imports and an independent comparison of selected real fills and portfolio calculations. Engine 1.2.0 behavior is unchanged by this test-isolation patch.
