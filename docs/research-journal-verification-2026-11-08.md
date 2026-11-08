# Research journal and bounded Congress review — 2026-11-08

## Verified result

The research journal is implemented around existing versions, conversations and
backtest jobs. It was exercised through a live browser with reviewed real AAPL
2018–2025 data, actual LLM amendment/discussion, explicit publication, a primary
candidate run and exact repeat, period/benchmark comparison and an immutable
conclusion. Engine **2.0.0** and all financial execution behavior are unchanged.

**259 backend tests including PostgreSQL and 54 frontend tests pass.** Ruff,
format checks, TypeScript/Vite production build, migrated-schema drift and real
PostgreSQL immutability checks pass. No coverage percentage is claimed. Existing
third-party deprecations and the Vite bundle-size warning remain visible.

## Isolated deployment and persistence

Project `trading-lab-research-journal-20261108` uses UI/API loopback **18088**,
PostgreSQL **15446**, and its own `postgres_data` volume. Ports were bind-checked
before creation. A read-only `pg_dump` of the prior isolated 15444 project was
restored only into this new volume, then migrated to **008_research_journal**.
The restore artifact SHA256 is
`1638511a77c731f5127252c4c61a261195dc54cf75fb0e01c53f551f7b9fde27`.

API, worker, frontend and PostgreSQL connectivity pass; the worker processed the
real runs. The newly created application's containers were recreated with final
images and its database restarted. Journal contents, results and transcript hashes
persisted. The database restart affects only this turn's newly created project.
All **42 pre-existing container IDs/start times/restart counts/mounts** match their
baseline. The older project's **35** completed result hashes remain unchanged;
all **3** source-project results, **23** existing conversation turns and **5**
publication transcripts are identical in the copied project. No homelab data,
pre-existing container, provider subscription or existing port was changed.

## Actual user workflow

1. Create/publish a new strategy with the prior real AAPL RSI baseline's exact
   configuration and replay 2018–2025 under the same funded profile. Its full
   financial result equals the prior result exactly.
2. Register the prospective question, hypothesis, sole intended change and
   evaluation criteria through the new journal UI before candidate publication.
3. Select that plan in the strategy's existing chat evidence picker. Send a natural
   request to change only RSI14 entry from 30 to 25, preserving RSI65 exit, 95%
   equity sizing, risk/execution rules and the independent profile. The actual
   `gpt-6-luna` reply proposes exactly that structural JSON change. **175 streamed
   delta events** were observed for this call.
4. Confirm acceptance is disabled until review. Accept into draft, confirm there
   is still only one published version, then publish v2 explicitly. Bind it as the
   candidate through the journal UI.
5. Schedule a primary and repeat attempt through the UI. Both complete under the
   same profile/dataset/source/engine controls and return the same full-result
   hash. Open the comparison with baseline and both attempts selected; inspect
   existing account timelines, yearly periods and cash/SPY references.
6. Record a mixed conclusion and next hypothesis. The immutable conclusion retains
   both completed attempt snapshots. Closed plans reject new attempts; later
   commentary can be an appended note or linked follow-on plan.
7. Send a second live message asking the same conversation to analyze recorded
   outcomes and missed positive years, distinguish facts from hypotheses, and
   discuss a possible next test without changing rules. The actual context includes
   all eight baseline years and both eight-year candidate reports. The reply cites
   the journal and has no proposed configuration. The conversation now has two
   user turns; v2's one-turn publication transcript remains byte-equivalent.

The journal plan is `f874e14a-7ee6-4941-9d85-107f8b1b91c9`. Baseline run:
`772c0e82-c5ca-430a-ae2c-f6775fc6eb65`; candidate:
`a2c96ae3-dd0d-4fe7-adaa-8ee7f58a5be3`; repeat:
`9f826e98-bbcb-49e0-b9ad-9f665e365686`.
The common candidate result SHA256 is
`47608c113e8596cfd53f050d3ea72a96967ec4438698ce76b4b43dce2d8eb52f`.

## Real comparison and independent checks

The frozen profile uses SGD10,000 starting capital, SGD500 on the first trading
session of each month, SGD2.50 per executed order, 0.05% slippage, whole shares,
long-only/unlevered holdings, a SPY reference and a 14-day historical-reference-FX
age policy. There are 96 contributions, totaling SGD48,000. Strategy entry/exit
conditions remain RSI14 below the threshold / above65, with95% equity sizing.

| Measure | RSI30 baseline | RSI25 candidate |
| --- | ---: | ---: |
| Ending account value, SGD | 66,282.58856119300 | 70,879.37750435250 |
| Flow-adjusted total return | 50.6044% | 51.0141% |
| Maximum flow-adjusted drawdown | -27.8462% | -10.2075% |
| Executed orders | 18 | 8 |
| Total fees/slippage, SGD | 371.10670280700 | 162.79072864750 |

Candidate minus baseline ending value is **SGD4,596.78894315950**. This is not
that difference divided by starting cash expressed as an investment return;
the flow-adjusted return calculation accounts for monthly injections. Matching
cash ends at SGD58,000; the simulator's funded SPY reference ends at
SGD113,823.31162360955, above both strategies. These references retain the existing
execution and cash-flow assumptions; cash earns zero interest.

| Year | RSI30 flow-adjusted return | RSI25 flow-adjusted return |
| --- | ---: | ---: |
| 2018 | 1.67% | 21.09% |
| 2019 | 21.23% | 7.72% |
| 2020 | 18.45% | 0.00% |
| 2021 | 9.22% | 0.00% |
| 2022 | -10.01% | 0.00% |
| 2023 | 11.78% | 0.00% |
| 2024 | 3.14% | 7.38% |
| 2025 | -8.97% | 7.82% |

The candidate misses several positive years. Better aggregate ending value and
lower drawdown do not establish uniformly better period performance or future
superiority. All2018–2025 remains in-sample development history as requested.

The existing standalone stdlib/Decimal34 checker was reused **without importing
application code**. It reconstructs both strategy accounts and matching SPY
references directly from retained bars, FX and actions: **8,044 daily marks,
4,022 decisions, 218 fills and 238 strategy ledger entries** pass. All monthly
contributions, historical FX clocks, dividends, the Apple split, order sizing,
cash affordability/costs, yearly/quarterly/monthly carry and cash references match.
Tolerance is1e-18SGD for cash,1e-12 for floating returns, and an IRR discounted
residual below1e-7SGD. Selected fill calculations are retained in the private
reconciliation report. Journal scalar differences and immutable content hashes
also match independent Decimal/hash calculations.

## Adversarial and browser checks

New synthetic tests verify prospective chronology versus retrospective labels,
cross-strategy rejection, idempotent requests, synthetic acknowledgement, edited
profile and engine/control mismatch rejection, rollback after queue construction,
retention of failed/repeated attempts, terminal-state conclusion requirements,
immutable conclusions and note conflicts, conversation isolation and withholding
future outcomes/yearly periods. Actual PostgreSQL migrations enforce immutable
plan/event update/delete protection. Existing financial/causal tests continue to
pass; this phase changes orchestration and research views, not simulation behavior.

Desktop and390px mobile journal views, deep-linked comparisons, closed-plan
controls, read-only candidate conversation and the live analysis chat pass browser
checks without runtime errors. Mobile page width does not overflow; tables retain
local horizontal scrolling. The exact browser driver initially hit a hidden-details
selector and a key-order-sensitive JSON assertion; these test issues were corrected.
A transcript assertion was changed to wait for its asynchronous history data.
No financial result or LLM response was substituted to make those checks pass.

Private evidence is under `.local/research-journal-20261108/`: test/build logs,
container/copy audits, live request/stream records, screenshots, immutable hashes,
period reports and independent reconciliation. Runtime data and credentials are
ignored and uncommitted. No additional key was needed.

## Still blocked or unverified

The [bounded Congress review](congress-bounded-review-2026-11-08.md) verifies two
March2022 House filings and their public archive bounds, and identifies an Apple
amendment that must not become a second purchase. It approves no eligible source
revision. Broad Congress coverage/amendment/clock reconciliation and Senate access
remain blocked; no Congress-driven performance is claimed. The four incomplete
intraday partitions remain blocked. Original-vintage news, analyst histories and
historical sector classifications remain separate source-qualification work.

The journal does not automatically attach externally scheduled runs, judge
statistical significance, optimize parameters or certify model reasoning. It has
one candidate/conclusion per plan and bounded records; follow-on plans retain the
research chain. A profile/data/source/engine change requires a separately baselined
comparison. Exhaustive device/accessibility coverage and production operations
beyond these isolated deployment checks remain unverified. See the
[journal workflow](research-journal.md) and [known limitations](known-limitations.md).
