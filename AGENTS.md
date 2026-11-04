# Trading Lab engineering conventions

- Preserve point-in-time correctness: strategies see only completed observations available at or before their simulation clock. Never expose future market information.
- Published strategy versions and imported dataset revisions are immutable. Runs retain profile snapshots and engine/configuration/content hashes.
- Strategies are validated declarative JSON, never executable code. Profiles are independent of strategies.
- Maintain Decimal cash accounting, historical FX availability, cash affordability including costs, and long-only unlevered positions.
- Changes to simulation behavior require financial, causal, and reproducibility tests. Never silently fabricate historical financial results.
- Synthetic fixtures and demos must be visibly labeled and explicitly selected. Missing real data is an error.
- No live brokerage execution in the MVP. Avoid unnecessary infrastructure.
- Backend: Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, pytest, Ruff. Frontend: React, TypeScript, Vite, TanStack Query, Router, Recharts.
- Run `python -m pytest` and `python -m ruff check .` from backend; `npm test` and `npm run build` from frontend. PostgreSQL integration tests use TEST_POSTGRES_URL when available.
- Add migrations for schema changes. Keep docs and the feature status accurate; never claim unverified deployment or real-data performance.
- Use small modules with typed boundaries, structured API errors, bounded inputs, and server-side credentials. Do not commit secrets or runtime data.
