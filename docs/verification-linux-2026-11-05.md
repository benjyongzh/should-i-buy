# Linux deployment and integration evidence — 2026-11-04–05

Current 2.0 deployment, migration, restart/isolation and bounded live-source checks
are recorded in [historical capability verification](historical-capabilities-verification-2026-11-05.md).
Earlier dated commands/results below retain their original engine and scope.

Latest follow-up: SPY combined-data acceptance is now complete under the stated research policy. Dataset `051e4285-e374-4b44-b82c-a54ffc8a6a6e` supports three real2018–2025 strategies plus original2019–2022 acceptance, all six exact repeats and independent financial reconciliation. Backend/PostgreSQL count is121; engine remains1.3.0 in this source-only pass. [Current measured report](real-spy-acceptance-2026-11-05.md) supersedes this document's earlier unaccepted-candidate/missing-input statements. QQQ/SMH/XLE and stricter vendor-vintage certification remain outside this SPY acceptance.

Subsequent FX preparation: FRED key supplied, live initial-release retrieval passed, and a private candidate CSV/source audit was generated. The candidate remains unaccepted pending source-evidence disposition and explicit FX-age policy review. Current backend count is 73 passing tests including PostgreSQL; engine 1.2.0 is unchanged. See [fx-data-review.md](fx-data-review.md). Remaining-input statements below describe the state before this follow-up.

## Scope and result

Inspected the actual Compose files, Dockerfiles, Nginx, settings, migrations, worker, import UI/API, Alpaca adapter, declarative schemas, LLM proposal/accept/publication routes, engine 1.2.0 and its financial regression tests. No application or engine changes were necessary. No independent engine re-review was triggered because simulation behavior was unchanged. Existing review limits in `milestone-3-review.md` still apply.

| Check | Actual result |
| --- | --- |
| Linux Docker build/start | PASS, Engine 29.6.1 / Compose 5.3.1 |
| PostgreSQL migrations | PASS, `002_immutable_inputs (head)`; `alembic check`: no new operations |
| Frontend/Nginx/API/database | PASS, frontend HTTP 200 and proxied health `status: ok, database: connected`; host loopback health also passed |
| Separate worker | PASS, HTTP-queued job completed without invoking worker processing from the probe |
| Persistence | PASS, dataset export/result hashes unchanged after service restart and after `down`/`up` with retained volume |
| Repeat execution after recreation | PASS, complete result equals baseline |
| Backend | 63 passed, including PostgreSQL migration/rollback/reapply, concurrency, immutable-input and worker tests |
| Frontend | 10 tests passed; TypeScript/Vite production build passed; npm install audit reported zero vulnerabilities |
| Ruff | Lint and formatting passed (52 files), with `RUFF_NO_CACHE=true` |
| Live Alpaca import | PASS, 1,259 raw SPY SIP bars, 2018-01-02–2022-12-30, no missing sessions |
| Live LLM generation/modification | PASS with configured `gpt-6-luna`, including separate acceptance/publication and earlier-version preservation |
| Real SGD backtests and independent financial reconciliation | BLOCKED, qualified FX and reviewed actions are missing; no real return is reported |

Native commands could not run: `python` was absent and frontend dependencies were not installed. The required checks ran successfully in disposable Linux containers instead. Backend emitted five existing dependency warnings; frontend emitted the existing bundle-size advisory. The first container Ruff command could not write its cache under non-root `/app`; no-cache invocation passed. These are recorded rather than hidden.

## Isolation and lifecycle

Project `trading-lab-linux-verify-20261104` uses only its own network and named volume `trading-lab-linux-verify-20261104_postgres_data`. Only frontend port **127.0.0.1:18080** is published. API 8000 and PostgreSQL 5432 are internal container ports. Runtime inspection confirmed database host `db`, port 5432, database `trading_lab`; no external database override was inherited. `/app/.env` is absent from the backend image. Root `.env` was not edited.

The existing homelab occupies host 80/443, 5432, 8080, 8081 and several other ports. All lifecycle commands targeted only the newly created project. Existing containers remained running with their prior uptime. The new project remains running for inspection; its retained volume contains both explicitly synthetic diagnostic inputs/results and the unreviewed real price revision.

The ignored `.local/compose-linux-verify.env` supplies this project's database password and port (permissions 0600); root `.env` supplies server-side provider credentials. Use these pinned commands from the repository:

```bash
docker compose -p trading-lab-linux-verify-20261104 -f docker-compose.yml --env-file .local/compose-linux-verify.env ps -a
docker compose -p trading-lab-linux-verify-20261104 -f docker-compose.yml --env-file .local/compose-linux-verify.env up -d --wait --wait-timeout 120
# Stop/remove only these project containers; retain PostgreSQL data:
docker compose -p trading-lab-linux-verify-20261104 -f docker-compose.yml --env-file .local/compose-linux-verify.env down
```

Do not append `--volumes` to the teardown command. Do not use default port 8080 on this host. To access from another computer, use an SSH tunnel to host loopback, for example `ssh -L 18080:127.0.0.1:18080 <user>@<homelab-host>`, then browse `http://localhost:18080`. No remote/public/authenticated deployment, host reboot autostart or backup restoration was tested. External-database Compose mode remains inspected only.

## Persisted diagnostic evidence

The deployment diagnostic explicitly selected synthetic data. Its results provide deployment/reproducibility evidence only.

- Dataset: `729255ba-78c6-4a1b-9e7a-ce037e497d7c`; content hash `35a0e4211fa7dad44e340dba64997da8e812215e9ac7352b2c0d3a82f957541b`.
- Canonical full dataset export SHA-256: `00c56510116c7e7dd2b6f98c1a1fb67aecc66cd1be689ed54d5288117a984d91`.
- Strategy version: `6d5d8772-88ee-4e9a-a8a3-608b78a4379d`; config hash `0665ea2e5c28d0456e35dee8fe9d307b1cbed35011690f989f985d239997ccd5`.
- Profile: `d6ccebdb-b11b-4d1b-acdc-98f7c5c64b7f`; profile hash `f552a6fcce92f9f932078797a1808b0ac9f63b43eafad00dd90d07f8a61511ba`.
- Baseline run: `1932cb8d-444f-4625-ad63-4f6295fb1566`; repeat after recreation: `d4349e33-31d8-4de0-9a04-262df5f88e56`.
- Both completed under `1.2.0` / `chronological-open-close-v2`, with one executed order and identical complete results. Canonical result SHA-256: `211578ea941eaa5a7a49f0c21c0bf7badccdf5c3ab4ff698b0f50c91ea0557aa`.

Canonical hashes here use sorted-key compact JSON. Restart and recreation comparisons checked full dataset exports and full results; the report does not claim a byte-for-byte comparison of every database row. Earlier Windows private `.local` artifacts referenced in older documentation were absent in this checkout. They remain historical reported evidence; this pass produced fresh checks.

## Real data and remaining inputs

The actual UI endpoint `POST /api/market-data/alpaca`, called through Nginx, returned 201. Current real revision: `5333f86e-ec6d-43a4-b0ce-13efcbe78c65`, hash `5fd1c37ccd280c6f83e4904cb17853eb8c4a07dd6f8a6c8fe639c6f77ee3b739`. This matches the earlier documented price-content hash. It has zero FX/actions and both review/completeness flags false. Scheduling returned structured HTTP 422 for missing corporate-action review, with the run list unchanged. Interactive browser import was not tested.

UI workflow: open Market Data, select SIP, SPY, 2018-01-01–2022-12-31, attach FX/actions CSV, and attest review only after reconciliation. Inspect counts, gaps and revision hash after import. Existing revisions cannot be amended; attach qualified inputs on a fresh import or export/merge/re-import to a new immutable revision. Combined source/availability provenance should describe all sources, not just Alpaca bars.

Alpaca key/secret already work here. No new market-data subscription or brokerage access is required for the demonstrated import. The adapter fetches raw prices and labels its assumed evening availability and revised history; this does not establish vendor publication vintages. SIP is suitable for US equities across venues, including Nasdaq-listed stocks; SPY itself tracks the S&P 500.

Remaining inputs/procedure:

1. **FX:** choose ALFRED initial-release `DEXSIUS` observations (SGD per USD), retain publication/vintage evidence, and normalize `observed_at,available_at,rate`. A registered FRED API key supports automated bulk retrieval; set it privately for the preparation process. The application has no FRED adapter/setting. Alternatively, the [Fed's keyless dated H.10 archive](https://www.federalreserve.gov/releases/h10/20190107/) was inspected: the January 7, 2019 release contains the prior week's daily Singapore rates and explicitly marks missing observations. This is evidence of an archive route, not full 2018–2022 coverage verification. Full extraction/publication-time review is pending. Preserve missing values as missing. Weekly release lag must be checked at every engine clock; explicitly review any move from default seven-day FX age to the supported 14 days. Reference FX is not an executable quote.
2. **Actions:** the [issuer's historical workbook](https://www.ssga.com/library-content/products/fund-data/etfs/us/spdr-etf-historical-distributions.xlsx) was downloaded and its XML inspected. It contains 20 SPY records in 2018–2022 with ex-date, record date, payable date and distribution amounts. It lacks declaration/publication timestamps and split coverage. The 2022 December payment extends into January 2023. Obtain original dated announcements or qualified vendor records proving pre-open availability, cross-check amounts/dates, and review all effective splits. No timestamp or no-split attestation was invented, and no action row was imported as certified.
3. **Acceptance:** once one qualified combined revision exists, use SGD 10,000, SGD 2.50/order, slippage 0.0005, 2019–2022, long-only/unlevered; use 2018 for warm-up. Record sizing, fractional-share policy and RSI thresholds explicitly. The existing proposed convention is 95% equity, whole shares, RSI14 below 30/above 65, no protective stops. The original request does not specify those choices. Schedule buy/hold, SMA20/50 crossover and RSI against shared snapshots; repeat and compare complete results. Independently reconcile entry/exit/re-entry, eligible FX clocks/ages, fees/slippage, ex-date entitlement, payment without double counting and final holdings/receivables. These real calculations remain unperformed.

## Live LLM smoke evidence

Server settings: `LLM_BASE_URL=https://api.openai.com/v1`, `LLM_MODEL=gpt-6-luna`, nonempty `LLM_API_KEY`. Two successful calls used the existing Chat Completions strict JSON Schema interface and backend Pydantic revalidation. The earlier HTTP 429 blocker is resolved for this smoke test. No model-price or quality benchmark is claimed.

Strategy `122d06da-2e98-4d18-84e8-0649559106fb`:

- Generate proposal `43110a21-5eb4-4268-95a2-ecb40c6f64bf`: SMA20 crosses above/below SMA50, 95% equity, maximum allocation 1, one position, null stops. Explicit smoke-test acceptance then separate publication created version `521cb572-79b4-4304-9de2-189f2ad8af76`.
- Modify proposal `b854b3e1-6b37-4c76-85fc-734d7b6d0d80`: periods changed to 10/30, other fields retained. Separate acceptance/publication created `3e55ea8d-823a-4513-9302-7f0c8fbad514`.
- Before each acceptance, the full draft and version list were unchanged. Acceptance alone left the version list unchanged. After modification/publication, the earlier complete published version was unchanged. These versions were not used to generate real backtest results.

For replacement credentials, edit ignored root `.env` locally. A funded API project key and access to the configured model are required; no key needs to be sent through chat. Recreate only this project's API/worker/frontend to load changed settings. The existing code sends strict `json_schema`, checks refusal/completion, and validates the returned configuration before proposal persistence; see [official OpenAI structured-output guidance](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat). This smoke test exercises API approval steps, not interactive browser review or general strategy quality.
