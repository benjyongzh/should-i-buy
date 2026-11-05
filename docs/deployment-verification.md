# Deployment and real-data verification — 2026-11-04

Current 2.0 deployment, migration, restart/isolation and bounded live-source checks
are recorded in [historical capability verification](historical-capabilities-verification-2026-11-05.md).
Earlier dated commands/results below retain their original engine and scope.

## Latest evidence — 2026-11-05

Real SPY acceptance follow-up: reviewed combined dataset `051e4285-e374-4b44-b82c-a54ffc8a6a6e` imported through the deployed API and persisted six real strategy runs plus six exact repeats in PostgreSQL through the separate worker. Independent daily financial/signal/benchmark reconciliation passed. All121 backend/PostgreSQL tests and Ruff pass. No app rebuild/restart or engine behavior change was required in this source/integration pass; the existing frontend's17-test/build result is retained. [Actual results and bounded source policy](real-spy-acceptance-2026-11-05.md) supersede the earlier SPY FX/action blocker statements below. No claim of new backup/recovery or real-run container-restart testing is made.

Engine 1.3.0 follow-up: 109 backend/PostgreSQL and 17 frontend tests pass, as do lint/format/build. Mandatory independent financial/causal review passed after a split-day crossover fix. The isolated project at loopback 18080 rebuilt/deployed the indicator/external-input extension. Three explicitly synthetic MACD/stochastic/external runs completed in the separate worker; an external rerun was identical. Reviewed source revisions and results survived final app recreation; migration succeeded and `alembic check` found no drift. All 21 homelab container identities/uptimes/ports remained unchanged; the isolated database container and volume were retained. Live LLM generation and modification passed the extended schema and explicit acceptance/publication checks. No real financial acceptance or qualified Fear & Greed source is claimed. See [current verification](verification.md) and [input workflow](strategy-inputs.md). The following paragraph records the earlier context-only batch.

The isolated Linux project now runs the context/period-reporting extension with migration `003_context_snapshots`, no drift, healthy frontend/API/database and running worker. All nine context imports passed after fixing FRED's US-day cutoff and 2,000-vintage limit. Existing result hashes reconcile unchanged. Current checks are 83 backend and 12 frontend tests/build, plus Ruff. See [continuous research](continuous-research.md) for the latest actual results; earlier sections below retain dated historical evidence.

FRED credentialed retrieval and standalone FX preparation have since completed. The candidate remains unaccepted pending source-flag disposition and FX-age policy review; see [FX review](fx-data-review.md). The historical table below's missing-FRED-key blocker no longer applies. Current backend checks pass **73 tests including PostgreSQL**; Ruff lint/format pass. No running service, immutable revision or profile was changed by preparation.

Linux Docker verification and live LLM generation/modification have now passed. Use the pinned Linux project/port commands and current evidence in [verification-linux-2026-11-05.md](verification-linux-2026-11-05.md). This is a separate project from the earlier Windows test below. It uses `127.0.0.1:18080`, an isolated bundled database/volume, and leaves all pre-existing homelab containers untouched. Real SPY bars were re-imported successfully; FX/actions and real backtest acceptance remain incomplete. The sections below preserve the earlier Windows record; their Linux-unverified and LLM-quota-blocked statements are historical.

## Status and required inputs

Docker build/start, network connectivity and persistence were demonstrated on this Windows machine using Docker Desktop's WSL 2 Linux engine after the user installed Desktop. Real-market and live LLM acceptance remain blocked. Engine 1.2.0 and its financial event ordering are unchanged. The Linux-host command examples below remain a procedure for a future Ubuntu deployment, not evidence of an Ubuntu-host test.

| Item | Actual status | User action needed |
| --- | --- | --- |
| Local automated checks | Latest backend: 63 passed in disposable Linux container including PostgreSQL with dummy credentials present; native rerun 62 passed/one PostgreSQL skip. Frontend previously passed 10 tests/build; Ruff passes | None |
| PostgreSQL migrations and jobs | Isolated native PostgreSQL 16 on loopback 55432; upgrade/check, rollback/reapply, immutable inputs, eight concurrent claims and persisted worker result passed | None for native test evidence |
| Docker build/start, Nginx/API/worker/DB networking, restart persistence | VERIFIED on Windows Docker Desktop/WSL 2: image builds, migration exit 0, health, HTTP job processing, service restart and container recreation with retained volume | None for this local test; Ubuntu/external-DB deployment remains untested |
| Alpaca live import | VERIFIED: paper account credential check HTTP 200; 1,259 raw SPY SIP bars imported through the UI's API route, 2018–2022, no missing sessions | Supply qualified FX/actions and review them before importing a new backtest-ready revision |
| Historical FX | BLOCKED: no vintage export/API credential supplied; candidate sources researched, observations not imported | Obtain a free FRED API key for ALFRED retrieval, or provide an official vintage export with publication evidence. There is no FRED adapter in the app; conversion to the existing CSV contract is a preparation step |
| Corporate actions | BLOCKED: SPY 2018–2022 events and declaration-time evidence have not been reconciled | Obtain/review issuer records using the procedure below; source files can be prepared without credentials where publicly available |
| Three real SPY strategies, selected-fill audit and reproducibility | BLOCKED: real prices imported; FX/actions remain incomplete/unreviewed | Complete source review and import one combined revision first |
| Live LLM generation/modification | Key supplied; live GPT-5.4 Mini request reached OpenAI but returned HTTP 429 `credit_balance_exhausted` / `insufficient_quota`; no completion produced | Restore usable API credit/billing; select `LLM_MODEL`. GPT-6 Luna is the recommended cost-focused candidate, not a live-validated model here |

No homelab database, volume or existing service port was changed. Native test PostgreSQL uses a separate test cluster on 55432; Docker verification uses its own new named volume. PostgreSQL integration tests own randomly named schemas. The original 61 backend cases passed inside the Linux API image; after two credential-isolation regressions were added, all 63 passed in a disposable container with dummy provider credentials deliberately present. Five existing third-party deprecation warnings remain. Container Ruff checks passed; current native Ruff checks also pass. The frontend compiled inside the Linux Node build stage; its 10 workflow tests were previously run on Windows. The frontend bundle-size advisory remains visible. See `testing.md` for isolation guarantees and the coverage map.

## Recorded Windows Docker verification

- Engine 29.9.2; Compose 5.6.1; context `desktop-linux`. The original `npipe:////./pipe/docker_engine` failure occurred before the Desktop engine was available. `docker desktop start --timeout 45` timed out while initialization continued; a subsequent `docker info --format "{{.OSType}}"` returned `linux`. No Docker reset, WSL unregister or data deletion was needed.
- Project: `trading-lab-verify-20261104080751`; loopback URL: `http://127.0.0.1:18080`; volume: `trading-lab-verify-20261104080751_postgres_data`. Database/API have no published host ports. Resolved Compose configuration was checked to use `@db:5432/trading_lab`, never an inherited external database URL.
- Both images built; PostgreSQL/API/frontend health checks passed; migrate exited 0; `alembic check` found no pending operations. API UID is 1000 and `/app/.env` is absent. Nginx served the SPA and its JavaScript/CSS assets, and proxied API health as `database: connected`.
- An explicitly synthetic 2018–2022 revision and SGD profile were imported/created through real HTTP calls. A published buy/hold version was queued and completed by the independently running worker, engine 1.2.0. The probe did not call `process_one` itself. No vendor prices or real returns were substituted.
- After restarting db/API/worker/frontend, the complete dataset export, dataset metadata/hash, strategy version, profile, completed run and results compared exactly equal. The same checks passed after `compose down` followed by `up`, retaining the named volume. This tests container recreation, not deletion/recreation of the database volume.
- A new job submitted after recreation completed in the new worker container: run `74d9cf0b-9bb1-41bc-a0ee-cc5ca4f47f1f`. Its complete result matched the baseline exactly, with the same canonical result hash. This demonstrates both worker reconnection and deterministic repeat execution for this synthetic diagnostic.
- Baseline run: `80a1af51-f86e-4499-a8c8-f99af06ed90c`; dataset hash `35a0e4211fa7dad44e340dba64997da8e812215e9ac7352b2c0d3a82f957541b`; canonical result SHA-256 `485ec49293a3ef28f40785671574bb807b2a7e58a6867725badd43c2527539a0`.
- Private local evidence: `.local/docker-build-start.log`, `docker-backend-tests.log`, `docker-initial-services.json`, `docker-images.json`, `docker-migration-current.log`, `docker-http-baseline.json`, and `docker-http-verification.jsonl`. `.local/compose-verify.env` contains the generated database secret and must remain private/ignored. Root `.env` was created from the template only because it did not exist; no user environment file was overwritten.
- Startup initially required refreshing this agent shell's PATH for `docker-credential-desktop`. Build context initially failed while traversing an inaccessible pytest cache: the unnecessary recursive `.env.example` exception was removed from `.dockerignore`, keeping caches and all environment files excluded. The retry built successfully.

For this existing verification stack, use PowerShell from the checkout:

```powershell
# The ignored helper pins the tested project, context, port and private interpolation file.
.\.local\compose-verify.ps1 ps -a
.\.local\compose-verify.ps1 up -d --wait --wait-timeout 120
# Stop only this project, retaining data:
.\.local\compose-verify.ps1 down
```

For a fresh Windows setup, launch Docker Desktop with WSL 2 and Linux containers, wait for its engine, and check `docker version`, `docker compose version`, and `docker info --format "{{.OSType}}"`. The last command must report `linux`; a Client section alone is insufficient. A fresh terminal may be needed after installation so Docker and its credential helper are on PATH. The Windows procedure does not require a separate Ubuntu VM. The retained test stack is for local verification; it does not establish unattended startup after a Windows reboot, backups or remote access.

## Credentialed checks after keys were supplied

On 2026-11-04, a read-only `GET https://paper-api.alpaca.markets/v2/account` returned HTTP 200 using the supplied credentials. Account details were neither printed nor retained. This confirms paper-account authentication; no live brokerage endpoint or order operation was called. The application adapter remains data-only. Alpaca requires historical bars at `https://data.alpaca.markets/v2/stocks/bars`, even with paper credentials; the paper trading base URL cannot replace this data endpoint. See [Alpaca authentication](https://docs.alpaca.markets/us/docs/authentication) and [historical API base URLs](https://docs.alpaca.markets/us/docs/historical-api).

The actual adapter fetched 1,259 raw SPY SIP bars from 2018-01-02 through 2022-12-30, with no missing sessions under the app's calendar. After recreating API/worker/frontend to load the user-supplied credentials, `POST /api/market-data/alpaca` through Nginx returned 201 and created real dataset `f9d78623-c8c5-4941-9489-7a1370638476`, hash `5fd1c37ccd280c6f83e4904cb17853eb8c4a07dd6f8a6c8fe639c6f77ee3b739`. This exercises the same endpoint used by the UI form; no interactive browser import was performed in this check. No paid subscription was purchased or changed.

The revision deliberately has zero FX observations and no corporate-action review/dividend-completeness attestation. An attempted scheduling request returned 422 with the reviewed-corporate-action requirement, and the run list remained unchanged. No real backtest was created. Complete FX/action source review and a new immutable combined revision are still required. Retrieved bars retain the existing assumed evening availability and revised-history flags; successful retrieval does not certify original publication vintages.

Private evidence: `.local/alpaca-live-verification.json`, `alpaca-spy-raw-pages.json`, `alpaca-spy-2018-2022-unreviewed.json`, `alpaca-live-import-report.json`, and `alpaca-imported-unreviewed-export.json`. These contain private vendor data and remain ignored by Git. Secrets and the paper account response are excluded.

The user's OpenAI key is now present; the saved `LLM_MODEL` was still blank at inspection. A temporary process-level `gpt-5.4-mini-2026-03-17` override was used for the separate live authoring smoke attempt, with an isolated SQLite database. The first restricted-network attempt failed to connect; host-network requests returned HTTP 429. A bounded diagnostic captured provider code `credit_balance_exhausted`, type `insufficient_quota`. Further retries stopped. There were no successful completions, persisted proposals, acceptances or publications. `.env` was not edited. The modification/semantic/review checks remain unverified against a live successful completion. Evidence: `.local/llm-live-smoke-report.json` and `llm-live-smoke.log`. See [OpenAI error-code guidance](https://developers.openai.com/api/docs/guides/error-codes).

For regular constrained JSON authoring, recommend `LLM_MODEL=gpt-6-luna` as the cost-focused candidate to evaluate after credit is available. Both Luna and GPT-5.4 Mini document Chat Completions and structured-output support. Standard short-context prices per million tokens are Luna USD 0.10 input/0.50 output and Mini USD 0.75 input/4.50 output. This is not an app-specific quality or latency benchmark. The current client does not set reasoning effort: Luna defaults to medium, Mini to none, so lower token price alone does not establish lower latency or exact per-request cost. Reasoning tokens also consume the output budget. Model choice does not change engine accounting or publication validation. Sources: [Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [Mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini).

## Credentials and configuration

Use `.env.example` as a template and edit the ignored `.env` locally. Do not paste secret values into chat or commit them. Compose reads root `.env`; native API and worker launched from `backend` read `backend/.env` or process environment, so configure both processes consistently. Settings are cached per process. Native processes need restarting after changes. Compose environment-file changes require **container recreation**, not merely `docker restart`; for the retained verification stack run `.\.local\compose-verify.ps1 up -d --force-recreate api worker frontend`. Recreating the frontend also refreshes Nginx's upstream resolution after API replacement.

```dotenv
POSTGRES_PASSWORD=<long-random-URL-safe-local-password>
WEB_PORT=18080
ALPACA_API_KEY=<your-market-data-key-ID>
ALPACA_SECRET_KEY=<your-market-data-secret>
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-6-luna
LLM_API_KEY=<optional-project-API-key>
```

The example model is a documented Chat Completions/structured-output candidate, not a live-tested compatibility promise. Confirm access in your API project. No broker funding or execution permission is needed by this app. Alpaca keys go only to the read-only `data.alpaca.markets` adapter. LLM keys go only to the configured server-side provider. FRED credentials are for external data preparation, not an implemented application setting. A ChatGPT/Codex login does not configure this application's LLM client.

## Docker inspection and safe verification procedure

Inspected both Compose files, both Dockerfiles, Nginx, `.dockerignore`, `.env.example`, backend settings, migrations and worker entry point. The bundled stack was tested as recorded above; external-database mode was inspected only. Bundled PostgreSQL/API publish no host ports. The frontend binds loopback. Migration completion gates API/worker startup; database/API/frontend have health checks. The worker has no health endpoint: successful processing of a queued job is the connectivity check. Backend runs as user `lab`; frontend uses a Node build stage and Nginx runtime. All environment files, including nested ones, are excluded from the build context.

The default Compose project name is `trading-lab`. For verification use a **new project name** so it cannot reuse an existing project's PostgreSQL volume. Start with the bundled database, not `compose.external.yml`. These commands are for the chosen Linux Docker host and have **not** run here:

```bash
# From this checkout; create .env from the template only if it does not exist.
test -e .env || cp .env.example .env
mkdir -p .local
# Populate this separate, ignored interpolation file; do not print its contents.
(umask 077; printf 'POSTGRES_PASSWORD=%s\nWEB_PORT=18080\n' "$(openssl rand -hex 24)" > .local/compose-verify.env)
VERIFY_PROJECT="trading-lab-verify-$(date +%Y%m%d%H%M%S)"
# Check this host's running projects and listeners; choose another port if occupied.
docker compose ls
ss -ltn '( sport = :18080 )'
# Require a new project and no existing <project>_postgres_data volume before proceeding.
docker volume ls --filter "name=${VERIFY_PROJECT}_postgres_data"
unset DATABASE_URL WEB_PORT POSTGRES_PASSWORD
dc() { docker compose -p "$VERIFY_PROJECT" -f docker-compose.yml --env-file .local/compose-verify.env "$@"; }
# The separate interpolation file deliberately has no external DATABASE_URL.
# Explicit backend environment wins over DATABASE_URL inside the service .env file.
dc config --quiet
dc up --build -d --wait --wait-timeout 180
dc ps -a
dc logs --no-color migrate
dc exec -T api python -m alembic current
dc exec -T api python -m alembic check
curl --fail http://127.0.0.1:18080/ > .local/docker-index.html
curl --fail http://127.0.0.1:18080/api/health
# Build current tests without replacing the running application container.
dc build api
# A disposable test container uses this new project's DB and a random test-owned schema.
# Provider keys are unnecessary; pytest also independently clears them and blocks HTTP.
dc run --rm --no-deps -T -e LLM_API_KEY= -e LLM_MODEL= -e ALPACA_API_KEY= -e ALPACA_SECRET_KEY= api python -c 'import os,pytest; from app.core.config import settings; os.environ["TEST_POSTGRES_URL"]=settings().database_url; raise SystemExit(pytest.main(["-q","-p","no:cacheprovider"]))'
```

Confirm `migrate` exited 0; db/API/frontend healthy; worker running; proxied API health succeeds. Inspect failures before continuing. Do not print expanded `compose config`, environment dumps or connection strings into shared logs. Set an SSH tunnel to host loopback if accessing from another machine; this app has no login.

In the UI explicitly load the **synthetic** dataset for deployment diagnostics, publish a test strategy, create the standard profile and queue a run. Wait for completion in the separate worker. Record its dataset ID/hash, strategy version/hash, profile snapshot, run ID/provenance and result. This proves the API/DB/worker path; synthetic profit is not historical evidence. The existing `app.demo` directly calls the worker service and writes repository documentation, so it is not the appropriate container connectivity test.

```bash
# Substitute the completed diagnostic run's actual ID.
RUN_ID='paste-completed-run-ID'
curl --fail "http://127.0.0.1:18080/api/backtests/$RUN_ID/results" > .local/docker-result-before.json
dc restart db api worker frontend
# Wait for healthy services and verify the worker is running again.
dc up -d --wait --wait-timeout 180
curl --fail "http://127.0.0.1:18080/api/backtests/$RUN_ID/results" > .local/docker-result-after.json
cmp .local/docker-result-before.json .local/docker-result-after.json
# Also prove persistence after container recreation, retaining the same project/volume.
dc down
dc up -d --wait --wait-timeout 180
curl --fail "http://127.0.0.1:18080/api/backtests/$RUN_ID/results" > .local/docker-result-recreated.json
cmp .local/docker-result-before.json .local/docker-result-recreated.json
```

Recheck the recorded inputs and queue a second diagnostic run after recreation. Retain project name, image IDs, migration revision, health output, run IDs and comparisons as evidence. Stop only this project with `dc down` when finished. Never use `down -v`, volume pruning, or an existing production database for this verification. For eventual external PostgreSQL deployment, provision a dedicated Trading Lab database and restricted user, then migrate it using `compose.external.yml`; do not point migration at an unrelated homelab database.

## Import real SPY history through the existing UI

1. Configure Alpaca server credentials. In **Market data → Fetch Alpaca historical bars**, select **SIP**, symbol **SPY**, dates **2018-01-01 through 2022-12-31**. These controls now select the actual feed, recorded as `alpaca-sip` or `alpaca-iex` in the immutable revision. Legacy API requests omitting `feed` retain IEX; the UI explicitly defaults to SIP. Failed entitlement/rate-limit requests remain errors; there is no fallback feed.
2. Prepare FX CSV with `observed_at,available_at,rate`, SGD per USD, timezone-aware timestamps. Include observations before the first bar so a genuinely available, sufficiently fresh rate exists at every required clock; continue through final valuation. Do not put today's revised daily FRED export into the app with same-day availability. See the source assessment in `data-providers.md`.
3. Prepare actions CSV with `symbol,session_date,available_at,kind,value,payment_date`. Use US SPY issuer distributions, not Australian SPY depositary-interest records. Reconcile every 2018–2022 ex-date and any payment dates extending into 2023. Use the issuer's historical distributions and original dated announcements for amounts, ex-dates, pay dates and prior knowledge. Review splits over the complete imported interval; absence of rows alone does not prove no splits. Cross-check a second source where available and record discrepancies.
4. Dividend values are USD/share; `session_date` is ex-date, not payment date. Split values are new/old share ratio. `available_at` must be supported by declaration/publication evidence and be no later than effective market open. A date-only declaration on the ex-date cannot prove pre-open availability. Missing declaration time, payment date or split coverage blocks certification; do not guess timestamps or silently insert zero actions. A latest revised distribution spreadsheet alone does not establish historical publication timing.
5. Attach the FX/actions files in the Alpaca form. Tick corporate-action review only after that review; tick complete dividends only after full reconciliation. Both attestations are user assertions, not automated source audits. API imports now retain the dividend-completeness flag. Fetch, then inspect coverage, missing sessions, count, source and hash. An initial unreviewed revision can be imported for inspection, but cannot be scheduled as reviewed real history. Amend by export/re-import to a **new** revision, never mutate the original.
6. Retain raw responses/files, retrieval dates, SHA-256 digests, source URLs, publication evidence, transformation instructions and review notes privately. When combining sources, export the dataset and add an accurate combined `availability_policy`/source label before re-importing; the Alpaca default policy only describes its bars. The canonical JSON export and hashes are the reproducible simulation inputs. Re-downloads can contain vendor revisions and must not replace an existing revision.

## Real historical acceptance procedure — pending data

Create one profile: SGD 10,000; fixed SGD 2.50 per executed order; slippage `0.0005`; 2019-01-01–2022-12-31; SPY only, long-only, max exposure `1`; no margin/shorting. Record whole/fractional shares, sizing, spread, percentage commissions, FX markup and every other profile field. Use 2018 only for indicator warm-up. If ALFRED's weekly release lag exceeds seven days, assess observed ages and explicitly choose the existing `max_fx_age_days=14` with that limitation recorded; never relax validation silently. Larger gaps remain errors.

Publish three versions: buy/hold; SMA20 crossing above SMA50 to enter and below to exit; RSI14 below 30 to enter and above 65 to exit. Use the existing templates and declare sizing (e.g. 95% of equity consistently, as in the synthetic demo), exit behavior and any risk stops. The user's RSI request does not specify thresholds; these are the existing demo convention and must be recorded. Do not assume a template's displayed name guarantees its configuration.

Schedule all three against the **same** dataset and profile snapshots. Repeat with identical inputs and compare deterministic results. Independently calculate the first buy, an MA/RSI exit and re-entry, an ex-dividend entitlement/payment, a split if one actually occurred, and final equity. Do not create a synthetic split inside the real dataset to exercise that path; use existing isolated tests.

For the requested zero-spread/zero-percentage-fee setup, independently check: buy fill price = raw opening USD price × `1.0005`; sale = opening × `0.9995`; SGD notional = shares × USD fill × latest eligible SGD/USD FX; buy cash debit = notional + SGD 2.50; sell credit = notional − SGD 2.50. Check the FX observation **and** publication clocks, age, cash affordability, post-cost exposure and next-open order eligibility. Confirm signal inputs were available at the preceding decision time. Check ledger ordering around opening fills and any protective exits against `backtesting-engine.md`.

Dividend entitlement uses eligible shares before ex-date opening orders; receivables contribute to equity but are unspendable before payment, and payment must not increase equity twice. Final equity includes cash, marked holdings and outstanding receivables using eligible FX; final holdings are not force-sold. Record Decimal calculations and raw source rows in an acceptance report alongside engine `1.2.0`, `chronological-open-close-v2`, profile/config/dataset hashes and result digests. No real selected-fill audit or real strategy return has been produced yet.

## Optional LLM smoke procedure

The client posts to `LLM_BASE_URL + /chat/completions` with `LLM_MODEL`, strict JSON Schema and a 5,000-token completion limit. Use an API model supporting this exact structured-output interface; a generic compatible chat endpoint alone is insufficient. See [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat) and [Luna's capabilities](https://developers.openai.com/api/docs/models/gpt-6-luna). A live request is currently blocked by exhausted API credit; this procedure has not passed with either model.

Generate a daily SPY MA20/50 proposal; inspect its parsed conditions, risk and sizing; verify the original draft/version list is unchanged before acceptance. Accept it into the draft, validate, then explicitly publish. Request a change to periods 10/30, inspect/accept it separately and verify the old published version remains unchanged. Record model ID, proposal IDs, prompt/schema metadata and statuses; never include the key. Refusal, truncation, unsupported fields and invalid schema must fail. Controlled HTTP tests now exercise those failure boundaries, while workflow tests cover draft acceptance and separate publication. These tests do not demonstrate live model compatibility, output quality or billing access.
