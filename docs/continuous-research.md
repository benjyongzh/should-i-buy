# Continuous 2018–2025 strategy research

Current follow-up: reviewed combined SPY revision `051e4285-e374-4b44-b82c-a54ffc8a6a6e` has completed buy/hold, SMA20/50 and RSI14 over 2018–2025, each with an identical repeat and independent financial reconciliation. [Actual results and yearly performance](real-spy-acceptance-2026-11-05.md) disclose 95% entry sizing,14-day reference-FX policy and source limits. QQQ/SMH/XLE remain unreviewed. MACD/stochastic and reviewed external operands are also implemented in engine1.3; external signal approval remains separate from accounting FX/actions. The dated import-only batch below records the earlier1.2 state and its then-unresolved SPY blockers.

The selected workflow uses **all of 2018–2025 for iterative development**. Simulations still progress session by session with restricted historical inputs. Each strategy revision runs across the full period; year/quarter/month results identify improvements and regressions. No prescribed holdout split is required. Repeatedly inspecting and tuning against these years makes them development data, and improvements are not a guarantee of future performance.

## Work cycle

1. Choose a reviewed immutable dataset, one shared profile and published versions. Include 2016–2017 history for indicator warm-up; the research profile begins on 2018-01-01 and ends on 2025-12-31.
2. Submit a new run. Existing persistent run storage already retains strategy/config hash, profile snapshot/hash, dataset revision/hash, engine metadata, signals, fills, ledger, equity, benchmark and outcome. A rerun creates another run; it does not replace earlier results.
3. Inspect **Run details → Performance through time**. Group by year, quarter or month; optionally restrict the date range. The starting equity for a period is the preceding stored mark, or initial capital for the first period. Positions, receivables and cash carry through; no annual liquidation/reset is simulated. The table reports period return, benchmark return, within-period drawdown, executed orders and commissions. It is a read-only derivation of saved results, not a new simulation. Partial periods show actual covered dates and session counts. Returns starting from zero equity are undefined, shown as unavailable.
4. Record a concrete hypothesis in the next published version's existing change summary: change one rule, expected effect and periods being investigated. Publish explicitly and run again with the same dataset/profile. Use Compare plus the period breakdowns to identify changes in returns, risk and costs, including deteriorations. Keep unsuccessful attempts too. There is no automatic optimizer, auto-publication, ML training or historical news oracle.

## Added data and actual live checks — 2026-11-05

Four new, separate real raw SIP price revisions each contain **2,514 bars**, 2016-01-04–2025-12-31, with no missing sessions under the app calendar:

| ETF | Research role | New dataset ID |
| --- | --- | --- |
| SPY | Broad US equity baseline | `77640317-c59e-4030-8950-38c5fab8cfd2` |
| QQQ | Nasdaq-100 ETF | `28c2e948-62ef-4bd9-9015-3508ae75c2eb` |
| SMH | Semiconductor ETF | `afd7553a-24fd-4c8d-96f5-b791004adc51` |
| XLE | Energy-sector ETF | `5886d8f5-a2d0-45da-a055-990e3043d709` |

These are **unreviewed price revisions**, each with zero imported FX/actions and no corporate-action attestation. They cannot yet support accepted real backtests. ETF prices are tradable-instrument histories, not historical index membership or proof of an economic narrative. SMH/QQQ/XLE have their own action histories to review; the SPY action check does not certify those instruments. Existing earlier revisions/results remain unchanged. Private preparation files and hashes are under `.local/research-history-2016-2025/`; reproduce with `python -m scripts.prepare_research_history` from `backend` in a process with server-side Alpaca credentials. Its `--api-url` optionally imports only unreviewed revisions into the designated local app; it never schedules backtests.

New profile `7367a755-85e9-44a0-9462-28b99343b46a`: SGD 10,000, SGD 2.50/order, slippage 0.0005, whole shares, no leverage/shorts, 2018–2025, `research_label=in_sample`. Its name explicitly discloses 14-day maximum reference FX age. This records the existing candidate's weekly-release compromise rather than changing older profiles. Source acceptance must still succeed before using it for real runs.

An extended FX candidate CSV is retained at `.local/context-live-20261105-final/usd-sgd-2016-2025-candidate.csv`, with source snapshot `2205761a-4d85-4e68-a4c4-8120c225bf53`. All 6,033 required 2018–2025 clocks have an eligible observation: seven-day age fails at 2,139 clocks, 14 days passes all, and maximum age is 12.3541667 days. CSV SHA-256 `23396f12edd6d394d676bd8ce62119e8d1a54baa064350138dedf9a16c8795c5`; detailed audit is `fx-candidate-audit.json` beside it. This is preparation/freshness evidence, not acceptance of the still-unresolved historical source review in `fx-data-review.md`. No FX rate was imported into the ETF revisions or substituted into completed runs.

## Market context library

Open **Market context** (`/context`) on the deployed app. Server-side fetch controls default to 2018–2025. Inspect charts, source policy, counts and revision hashes; complete JSON exports retain source hashes and vintage windows. Every snapshot is immutable at the database boundary. These source series are separate from tradable market datasets and cannot be selected as a strategy/FX input.

Actual API imports through Nginx returned HTTP 201, and complete exports validated successfully:

| Series | Source | Numeric observations | Missing initial values omitted |
| --- | --- | --- | --- |
| VIX close | Public Cboe CSV | 2,038 | 0 |
| DGS2 / 2-year yield | ALFRED initial releases | 1,998 | 90 |
| DGS10 / 10-year yield | ALFRED initial releases | 1,998 | 90 |
| DFF / effective Fed funds | ALFRED initial releases | 2,922 | 0 |
| CPIAUCSL / seasonally adjusted CPI | ALFRED initial releases | 95 | 1 |
| UNRATE / unemployment | ALFRED initial releases | 95 | 1 |
| DCOILWTICO / WTI spot | ALFRED initial releases | 1,992 | 96 |
| DCOILBRENTEU / Brent spot | ALFRED initial releases | 2,045 | 43 |
| DEXSIUS / USD–SGD reference FX | ALFRED initial releases, 2016–2025 including warm-up | 2,494 | 115 |

Monthly/daily observation dates differ from release dates. The macro charts use observation dates for retrospective analysis. Initial missing values remain missing; this is not a replay of every later revision. Macro availability is conservatively midnight New York **after** the FRED first-release date, not a measured original release time. VIX is current revised history with **null original availability**, and must not be treated as certified historically known data. Currency/units differ between series; negative WTI prices are valid context observations and are not forced positive.

FRED's source-day cutoff differs from UTC near midnight. Live testing caught and fixed that issue. Long histories also exceeded its 2,000-vintage JSON limit; retrieval now uses nonoverlapping four-calendar-year **release** windows with the full requested observation bounds. Live checks verified output type 4 does not repeat older releases in later windows. Keeping observation bounds unchanged preserves late first releases, including observations published after their represented period. The exact windows and source day are exported; there is no fallback to revised/latest values. Fixed catalog URLs and series IDs avoid arbitrary server URL fetching; responses, rows, date ranges and pagination are bounded.

Sources: [Cboe daily VIX downloads](https://www.cboe.com/tradable_products/vix/vix_historical_data), [FRED v1 initial-release and vintage documentation](https://fred.stlouisfed.org/docs/api/fred/series_observations.html).

## Keys and next additions

**No new keys were required for this batch.** Existing `ALPACA_API_KEY`/`ALPACA_SECRET_KEY` and `FRED_API_KEY` worked; VIX is a public download. Root Compose `.env` supplies server settings; native processes must receive the same settings in their own environment/current-directory `.env`. Browser code never receives keys.

RSI, EMA200, SMA, volume/average volume and momentum already work in the declarative interpreter. MACD is not added in this pass. Macro/context-to-signal integration would require a clock-filtered feature contract and the applicable financial/causal/reproducibility review. News/event timelines, Fear & Greed history, geopolitical factors, earnings and inventory-release surprises are not implemented here. WTI/Brent and sector ETF histories offer immediate context for oil/semiconductor research; they do not establish causal explanations. Any later news source must preserve publication/first-seen/update timestamps and applicable access rights before use in simulation. No additional API credential should be purchased just for this batch.

## Verification and remaining gate

- 83 backend tests pass including PostgreSQL migrations/check/rollback/reapply and context update/delete rejection. Ruff lint/format passes.
- 12 frontend workflow tests and TypeScript/Vite production build pass. Existing dependency warnings and the bundle-size advisory remain. Interactive browser use was not separately exercised in this pass.
- New migration `003_context_snapshots` applied successfully in the isolated project; `alembic check` reports no drift. API/database/frontend are healthy; worker is running. Only project `trading-lab-linux-verify-20261104` app services were recreated, with its retained volume and `127.0.0.1:18080`. Pre-existing homelab services were untouched.
- The old synthetic baseline result hash is still `211578ea941eaa5a7a49f0c21c0bf7badccdf5c3ab4ff698b0f50c91ea0557aa`. Linked yearly returns, order totals and commissions from the live report reconcile with that saved result. This is synthetic diagnostic evidence only.
- Engine/interpreter/ledger behavior remains 1.2.0; no strategy-editor changes or trading-context integration occurred. Existing independent engine review remains the applicable gate. New tests independently check carried capital, within-period loss, year-boundary local timestamps, zero equity, immutable snapshots and source availability. The new analysis does not mutate stored results.
- Real continuous runs remain blocked by qualified FX/action review. Context import does not waive that requirement. No real 2018–2025 returns were generated.

Private live evidence: `.local/context-live-20261105-final/` contains all nine full snapshot exports and `report.json`; `.local/context-live-20261105/` retains the earlier failed macro requests and successful VIX check. The initial HTTP 400 failures were fixed and the final nine imports passed. Existing Windows evidence/status paragraphs in older documents should be read as historical; current status is recorded here.
