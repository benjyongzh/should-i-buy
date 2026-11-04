# Automated testing before credentials

Current result (2026-11-04): **63 backend cases passed in a disposable Linux container**, including isolated PostgreSQL integration. The process was deliberately given nonempty dummy Alpaca/LLM credentials to verify isolation. Native Windows: **62 passed, one PostgreSQL test skipped** because `TEST_POSTGRES_URL` was unset. Ruff lint and formatting pass. The unchanged frontend previously passed **10 workflow tests** and its production build, including a Linux image build.

The backend total includes unit and integration tests; it is not a count of unit tests alone. No code-coverage percentage has been measured.

| Layer | Main coverage | Files under backend/tests |
| --- | --- | --- |
| Financial unit/regression tests | Next-open execution, Decimal cash/fees/P&L, affordability, exposure, order limits, split accounting, dividend entitlements/payment, final marks and metrics | `test_engine.py`, `test_risk_and_metrics.py`, `test_corporate_actions.py` |
| Causality and independent-review regressions | Future price/volume/FX isolation, publication gating, chronological opening/protective fills, post-cost risk limits, malformed timestamps and total-loss behavior | `test_temporal_data.py`, `test_milestone3_review.py` |
| Strategy units | Indicators, warm-up, comparisons/crossover events, expression trees and strict schema bounds | `test_strategy.py` |
| Provider boundary units | Mocked Alpaca SIP/IEX parameters/pagination/availability and errors; strict LLM response, invalid schema, refusal, truncation and HTTP errors | `test_providers.py`, `test_llm_client.py` |
| Credential/network isolation | Inherited keys/model cleared; synchronous and asynchronous unmocked HTTPX requests fail before network access | `conftest.py`, `test_provider_isolation.py` |
| API/SQLite integration | Validated imports, retained feed/actions/attestations and hashes, publish/schedule/worker/result lifecycle, immutable snapshots, cancellation/failure and explicit LLM draft acceptance | `test_workflow.py`, `test_providers.py`, `test_foundation.py` |
| PostgreSQL integration | Migrations/check/rollback/reapply, immutable-input enforcement, eight concurrent job claims and persisted worker result in a random test-owned schema | `test_postgres.py` |

Frontend `src/pages/workflows.test.tsx` tests editor/profile/import/result workflows with a mocked API. It does not contact Alpaca or an LLM. Actual Docker HTTP/worker/restart tests are separate deployment smoke checks, recorded in `deployment-verification.md`.

## Credential isolation

An audit found that the missing-key LLM workflow test previously inherited configured environment variables. That could have enabled a live request after a developer configured keys. The autouse backend fixture now clears `LLM_API_KEY`, `LLM_MODEL`, `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` in the **test process**, clears cached settings, and blocks real HTTPX transports. Provider tests explicitly construct settings with fixture keys and use `MockTransport`; FastAPI's in-process TestClient transport continues to work. Both synchronous and asynchronous HTTP boundaries have regressions. The fixture does not edit `.env` or change running services.

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
