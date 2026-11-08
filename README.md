# Trading Lab

[Full 2018–2025 earnings experiment](docs/full-history-earnings-experiment-2026-11-08.md):
64 original quarterly pairs, 35,854 current-version news records and 1,262 literal
analyst announcements. Only the explicit daily earnings research proxy is reviewed.
The controlled entry gate reduces drawdown but lowers ending equity. 339 backend/
PostgreSQL and 62 frontend tests pass. [Flowchart and visual comparison](docs/earnings-experiment.html).
A large-catalog runtime fix is verified in isolation; the existing deployment still
needs that fix. One automatic API restart was observed; prior immutable data is
preserved and no existing container was manually restarted or replaced.

[Free-source qualification](docs/retail-source-qualification-2026-11-08.md): pinned
Congress inventory/document checks, 98 news-derived analyst announcements retained
for review, and two checked issuer/SEC earnings pairs. Historical coverage and
public clocks remain explicit review gates.

[Retail information pilot](docs/retail-information-pilot-2026-11-08.md): real
AAPL/MSFT news, insider and earnings samples are retained for review; continuous
historical coverage is not yet approved. Quiver API is paid, optional and not
configured. Existing services remain unchanged.

A self-hosted, single-user US equity/ETF research platform. Create declarative strategies, publish immutable versions, configure shared financial assumptions, run chronological daily/intraday historical backtests, and compare performance. No brokerage execution is implemented.

Strategy rules support RSI, EMA/SMA, volume, MACD, stochastic and explicitly reviewed external observations such as macro series. Read [strategy inputs](docs/strategy-inputs.md) for timestamped source import, immutable review revisions and run selection. Adding a signal source does not waive the separate historical FX/corporate-action acceptance requirements.

Engine **2.0.0** adds reviewed intraday execution, historical sector/ranking
controls, conditional sizes, and publication-gated news, analyst, economic and
Congress-disclosure rules. Natural-language plans remain reviewed drafts until
explicit publication. Read [capabilities](docs/strategy-capabilities.md) and the
[exact data/key checklist](docs/historical-input-checklist.md). These capabilities
do not supply missing historical observations or original vendor vintages.

The [streaming strategy conversation](docs/strategy-conversation.md) asks for
clarification, shows selected-source audits and labels evidence-based research
estimates. Each strategy has one permanent conversation with full eligible recall
and [read-only publication transcripts](docs/conversation-history-verification-2026-11-07.md).
Review, draft acceptance and publication remain separate. Latest checks:
339 backend/PostgreSQL tests and 62 frontend pass. [Intraday source qualification](docs/intraday-congress-verification-2026-11-07.md)
supplies 92 complete monthly partitions; four incomplete months and broad Congress
histories remain blocked. [Congress qualification](docs/congress-qualification-2026-11-07.md)
now retains original reports and bounded archive-clock evidence; no complete
Congress stream is approved. The [research journal](docs/research-journal.md) now records hypotheses, frozen
comparisons, attempts and conclusions, with selected outcome analysis in the same
strategy conversation. [Real acceptance](docs/research-journal-verification-2026-11-08.md)
uses a new isolated18088/15446 project; pre-existing containers remain untouched.

The [Congress source-review workflow](docs/congress-source-workflow.md) now
qualifies a narrow House filing cohort with canonical amendment handling and
[real test/repeat evidence](docs/congress-ledger-verification-2026-11-08.md).
The [full Congress acquisition](docs/congress-full-coverage.md) now runs in the
latest isolated app on 18092/15450, with 6,234 House PTR records inventoried.
Full qualification remains pending; Senate still returns403 from this environment.

## Start locally

Requires Python 3.12+ (tested on 3.13) and Node 22.12+ or 24 LTS. From the repository root, on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.lock
Copy-Item .env.example .env
cd backend
..\.venv\Scripts\python -m alembic upgrade head
..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal, from `backend`:

```powershell
..\.venv\Scripts\python -m app.worker
```

In another terminal, from `frontend`:

```powershell
npm ci
npm run dev
```

Open [Trading Lab](http://127.0.0.1:5173). API docs: [OpenAPI UI](http://127.0.0.1:8000/docs). With no `DATABASE_URL` in the environment, local development uses `backend/trading_lab.db` (SQLite, single worker). For PostgreSQL, export `DATABASE_URL=postgresql+psycopg://…` **before** running migrations, API, and worker. Environment variables are read in each process; local `.env` is read from its current working directory. For local secrets, copy the root `.env` to `backend/.env`, or export the variables. Never commit either file.

On Linux/macOS, use `.venv/bin/python` instead of `.venv\Scripts\python`. Node 22.14 and Python 3.13 were used for verification.

## Docker Compose on Ubuntu

```bash
cp .env.example .env
# Set POSTGRES_PASSWORD to a long random URL-safe value in .env.
docker compose up --build -d
docker compose ps
```

Open [localhost:8080](http://localhost:8080). Compose runs PostgreSQL, a one-shot migration service, FastAPI, a separate worker, and an Nginx-served frontend. PostgreSQL and the API have no public host ports. The frontend binds loopback by default. Data persists in the `postgres_data` volume. Do not use `docker compose down -v` unless you intend to erase that database.

To use an existing PostgreSQL instance, set `DATABASE_URL` and use `docker compose -f compose.external.yml up --build -d`; the external configuration has no bundled database. Percent-encode reserved characters in connection URLs. Restrict access through an authenticated reverse proxy or trusted VPN before allowing non-local access. This MVP intentionally has no account/login system.

Docker deployment is now verified on this Linux homelab as well as in the earlier Windows record. The isolated project uses loopback port 18080 and its own database volume; existing homelab services are untouched. That earlier reporting deployment passed 140 backend tests including PostgreSQL, 26 frontend tests/build, Ruff and migration drift. Current isolated code checks are recorded in [verification](docs/verification.md). Selected reporting/comparison desktop/mobile browser checks also pass. External-database deployment and reboot autostart remain unverified. Backup restoration now passes in the [new isolated full-cycle project](docs/full-cycle-verification-2026-11-06.md). Use the [pinned isolated deployment commands](docs/verification-linux-2026-11-05.md), rather than default port 8080 on this host.

## Requested-company onboarding (verified in a separate Docker test project)

The `/companies` page queues ticker/date requests, retains Alpaca/SEC evidence,
reports blockers and requires explicit review before publishing an immutable
package. Daily accounting and SEC filing-presence collection are implemented;
other requested capabilities remain blocked. Migration 005 and updated API,
worker and frontend are required. See [workflow and configuration](docs/company-onboarding.md)
and [actual isolated verification](docs/company-onboarding-verification-2026-11-06.md).
A separate full-cycle stack now runs on loopback 18082 with its own database volume;
[real-data, funded replay and backup-restore evidence](docs/full-cycle-verification-2026-11-06.md)
is recorded. Existing homelab containers and project deployment on port 18080 remain unchanged.

## First research workflow

1. **Market data:** import raw daily OHLCV CSV plus USD/SGD FX and corporate actions as one immutable revision. Inspect coverage and provenance. For real raw data, review corporate-action history, supply all effective splits, and attest that review in the import form before scheduling. Alternatively configure server-side Alpaca keys; its read-only adapter fetches raw SIP or IEX daily bars (explicit selection; UI defaults to SIP). Missing credentials or coverage produce explicit errors.
2. **Strategies:** create a strategy, choose a template or compose typed conditions, edit sizing/risk, validate, save the working draft, then publish a version. The advanced JSON editor uses the same backend schema.
3. **Backtest profiles:** save capital, currency, dates, symbols, benchmark, fees, slippage and constraints. The standard defaults are SGD 10,000 and SGD 2.50 per executed order.
4. **New backtest:** select one or more published versions, one profile and one dataset. Jobs execute in the separate worker. Synthetic datasets require explicit acknowledgment.
5. **Results / Compare:** inspect net/gross returns, benchmark, equity, drawdown, fees, orders, trades, signals and ledger. Different input/profile hashes produce a comparison warning.
6. **Versioning:** change a draft and publish again. Old versions and completed results remain unchanged.
7. **Optional assistant:** configure `LLM_API_KEY`, `LLM_BASE_URL` and `LLM_MODEL`. Proposals are strictly validated JSON; accepting changes only a draft. Publication is a separate action. Manual authoring works without credentials.
8. **Continuous research:** use 2018–2025 as the full development period, retain every run/version, and inspect year/quarter/month breakdowns in Run details. Periods carry the continuous portfolio forward instead of resetting capital. **Market context** stores separate immutable VIX, rates, inflation, unemployment, oil and FX source snapshots for analysis; these are not trading inputs. See [continuous research and current source evidence](docs/continuous-research.md).

For an explicitly synthetic, end-to-end 2019–2022 demonstration:

```powershell
# From backend, after migrations; use an idle worker/queue for this command.
..\.venv\Scripts\python -m app.demo
```

This creates labeled demo data, three strategies, a revised MA version and four persistent results, then asserts version/profile immutability and future-price/FX mutation invariance. See [the measured demo report](docs/demo-report.md). These are synthetic results, not historical SPY performance. That original demonstration used no real data or LLM credentials; subsequent credentialed integration checks are recorded in the deployment runbook.

## Checks

```powershell
# From backend
..\.venv\Scripts\python -m pytest -q
..\.venv\Scripts\python -m ruff check .
..\.venv\Scripts\python -m ruff format --check .
..\.venv\Scripts\python -m alembic check
# Optional isolated PostgreSQL acceptance (creates/removes a random test-owned schema)
$env:TEST_POSTGRES_URL='postgresql+psycopg://user:password@localhost:5432/test_database'
..\.venv\Scripts\python -m pytest tests/test_postgres.py -q
# From frontend
npm test
npm run build
npm audit
```

The Python lock records all transitive versions. Update `requirements.in`, resolve in a clean virtual environment, regenerate `requirements.lock`, and run the checks. Frontend resolution is pinned by `package-lock.json`.

Automated tests require no market-data or LLM credentials. Backend tests clear inherited provider keys/model and block unmocked HTTPX requests; provider responses are controlled fixtures. See the [unit/integration coverage and isolation notes](docs/testing.md). Live credentialed smoke tests are separate from pytest.

## Architecture and feature status

The mandatory [Milestone 3 correctness gate](docs/milestone-3-review.md) runs before strategy-editor work and after material engine changes. Engine **2.0.0** passed independent financial/causal review before its timing/source editor changes and is deployed for fresh runs. Engine 1.4.0 funding and daily behavior remains on the legacy path. Four full financial baselines still match 1.2.0 exactly; legacy configuration/profile hashes also match 1.3.0. Completed results retain their original assumptions and are never rewritten.

React/TypeScript/Vite/Tailwind + TanStack Query/Router/Recharts → FastAPI/Pydantic → SQLAlchemy/Alembic/PostgreSQL. The Python worker uses transactional row claiming, ownership tokens, progress/heartbeat leases, cancellation and visible stale-job failures. Strategies have no network, filesystem, arbitrary Python or unrestricted data access.

See [architecture](docs/architecture.md), [data model](docs/data-model.md), [strategy DSL](docs/strategy-schema.md), [event ordering and accounting](docs/backtesting-engine.md), [data isolation](docs/point-in-time-data.md), [provider notes](docs/data-providers.md), [milestone verification](docs/verification.md), and [known limitations](docs/known-limitations.md).

Implemented through the MVP workflow, isolated Linux Docker verification and live LLM generation/modification. A reviewed SPY revision supports real 2018–2025 buy/hold, SMA20/50 and RSI14 runs under engine 1.3, with exact repeats and independent financial reconciliation. [Measured returns and source limits](docs/real-spy-acceptance-2026-11-05.md) disclose 95% entry sizing and lagged reference FX. Engine 1.4 adds [trade timing, sizing and monthly funding](docs/funding-and-trade-controls.md): **183 backend/PostgreSQL and 31 frontend tests pass**, with separate real Q1-2019 funded smoke runs/repeats and [independent reconciliation](docs/funding-verification-2026-11-05.md). The [performance timeline](docs/performance-timeline.md) links account curves to saved decisions and overlays versions/strategies with cash and buy-and-hold references. QQQ/SMH/XLE still require action reviews. No live trading is included.

The [deployment and real-data runbook](docs/deployment-verification.md) records current checks, credentials to configure locally, a free-first source plan and isolated Docker verification commands that avoid existing homelab databases and ports.
