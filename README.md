# Trading Lab

A self-hosted, single-user US equity/ETF research platform. Create declarative strategies, publish immutable versions, configure shared financial assumptions, run chronological daily backtests, and compare performance. No brokerage execution is implemented.

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

Docker is not installed on the development host, so container build/start verification remains outstanding. Native PostgreSQL 16 migrations, rollback/reapply, immutability triggers and concurrent claiming were tested.

## First research workflow

1. **Market data:** import raw daily OHLCV CSV plus USD/SGD FX and corporate actions as one immutable revision. Inspect coverage and provenance. For real raw data, review corporate-action history, supply all effective splits, and attest that review in the import form before scheduling. Alternatively configure server-side Alpaca keys; its read-only adapter fetches raw IEX daily bars. Missing credentials or coverage produce explicit errors.
2. **Strategies:** create a strategy, choose a template or compose typed conditions, edit sizing/risk, validate, save the working draft, then publish a version. The advanced JSON editor uses the same backend schema.
3. **Backtest profiles:** save capital, currency, dates, symbols, benchmark, fees, slippage and constraints. The standard defaults are SGD 10,000 and SGD 2.50 per executed order.
4. **New backtest:** select one or more published versions, one profile and one dataset. Jobs execute in the separate worker. Synthetic datasets require explicit acknowledgment.
5. **Results / Compare:** inspect net/gross returns, benchmark, equity, drawdown, fees, orders, trades, signals and ledger. Different input/profile hashes produce a comparison warning.
6. **Versioning:** change a draft and publish again. Old versions and completed results remain unchanged.
7. **Optional assistant:** configure `LLM_API_KEY`, `LLM_BASE_URL` and `LLM_MODEL`. Proposals are strictly validated JSON; accepting changes only a draft. Publication is a separate action. Manual authoring works without credentials.

For an explicitly synthetic, end-to-end 2019–2022 demonstration:

```powershell
# From backend, after migrations; use an idle worker/queue for this command.
..\.venv\Scripts\python -m app.demo
```

This creates labeled demo data, three strategies, a revised MA version and four persistent results, then asserts version/profile immutability and future-price/FX mutation invariance. See [the measured demo report](docs/demo-report.md). These are synthetic results, not historical SPY performance. No real data or LLM credentials were supplied during verification.

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

## Architecture and feature status

React/TypeScript/Vite/Tailwind + TanStack Query/Router/Recharts → FastAPI/Pydantic → SQLAlchemy/Alembic/PostgreSQL. The Python worker uses transactional row claiming, ownership tokens, progress/heartbeat leases, cancellation and visible stale-job failures. Strategies have no network, filesystem, arbitrary Python or unrestricted data access.

See [architecture](docs/architecture.md), [data model](docs/data-model.md), [strategy DSL](docs/strategy-schema.md), [event ordering and accounting](docs/backtesting-engine.md), [data isolation](docs/point-in-time-data.md), [provider notes](docs/data-providers.md), [milestone verification](docs/verification.md), and [known limitations](docs/known-limitations.md).

Implemented through the local synthetic MVP workflow. Remaining release verification: actual Docker deployment, credentialed provider/LLM calls, and the real 2019–2022 equity/FX/corporate-action scenario. No fabricated real-data returns or live trading are included.
