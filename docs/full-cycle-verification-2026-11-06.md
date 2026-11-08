# Full-cycle Docker and real-data research verification — 2026-11-06

Started 2026-11-06; final Docker browser and evidence audit completed 2026-11-07.

## Outcome and subsequent live LLM verification

**The local full cycle passes:** isolated Docker build/start, migration 005, real-data import, requested-company review, baseline publication, a one-field strategy amendment, full 2018–2025 replay, period comparisons, exact repeats, independent accounting, backup restoration and restart persistence.

**At the end of the original cycle the external LLM step had not run:** automatic
approval review rejected disclosure of derived results without clearer permission.
The quantitative cycle below therefore used an explicitly reviewed local amendment.
The user subsequently approved testing. The [November 7 live editor follow-up](llm-user-workflow-verification-2026-11-07.md)
now verifies seven prompts to configured OpenAI, reviewed publication, four real
cases and exact repeats, preserving the original 27 results. The isolated project
now has 35 completed results. One unnecessary model refusal and all missing-source
blockers remain documented; the original local-cycle provenance is unchanged.

The research journal is retained as test evidence (`research-journal.json`), using the existing version/run APIs. A structured journal product UI and automatic results-to-proposal feature remain future work.

## Deployment and isolation

- New project: `trading-lab-full-cycle-20261106`; frontend `http://127.0.0.1:18082`.
- Own database volume: `trading-lab-full-cycle-20261106_postgres_data`; test-only PostgreSQL host binding `127.0.0.1:15440`.
- PostgreSQL 16, API, frontend and worker start successfully; migration service exits 0 at `005_company_intakes`. `alembic check` detects no drift. Queue execution proves worker/API/database connectivity.
- The pre-existing deployment on 18080 was not modified by this work. The November 6 audit confirmed all 27 original container IDs/start times/restart counts/mount memberships unchanged. On November 7 continuation, 23 original IDs remain and match; four original IDs are no longer present. No operations were performed on those resources. This later observation is retained separately, and does not justify claiming the entire original host snapshot is still unchanged. Docker mount listings are compared by membership, not array order.
- Only this newly created test project was restarted/rebuilt. Separate temporary restore resources on 15441/18083 were removed. The source test project remains available for review, with its volume retained.

Images tested:

| Service | Image ID |
| --- | --- |
| api-1 | `sha256:3ac6d8923fd2b74603f70e6bdfa2d54126f5dd645f352d850b1a19af8b087d02` |
| frontend-1 | `sha256:6b9e2f5b0d60237da756836c95aeb2b0e1d66def163534e3e46e64bc95d4b47a` |

Private evidence is under `.local/full-cycle-20261106/`, including source/review receipts, frozen configurations, all results, period exports, independent checkers, screenshots, backup and journal. Secrets/runtime data are not committed. New stack environment files contain generated test credentials and are ignored. Root API credentials remain server-side.

## Real sources and onboarding scope

The test imports the **previously reviewed** AAPL/MSFT/SPY accounting revision through the new API: 7,542 raw daily bars (2016–2025 warm-up included), 2,494 reviewed ALFRED reference-FX observations and 121 issuer-reviewed actions. This is reuse of qualified real revisions, not a fresh vendor download or synthetic replacement. The frozen accounting content hash is `bc123cb86fd083ab04555343158ec4608a527d72cb9077ef9f9bf19f116f5db7`.

An existing raw 145-event AAPL/MSFT SEC 8-K/8-K/A revision is imported and explicitly approved as a new child with preserved parent/hash lineage. Its retained original evidence and next-session-close research policy are reused.

The Docker-served UI submits and reviews actual 2018–2025 requests for AAPL, MSFT and SPY. The background worker resolves current SEC identity and reuses qualified revisions. AAPL/MSFT approve daily accounting and SEC capability; SPY approves accounting only. Its separately collected ETF filing candidate remains **unreviewed and unused**. Requested historical sectors stay blocked. Current mapping still requires historical security-continuity review.

No new source key was required. Original vendor delivery vintages, exhaustive issuer/news coverage, executable FX, historical sectors, intraday, analyst archives and Congress collection are not established by this test. Existing research policies remain explicit: revised raw SIP history, assumed 20:15 New York daily-bar availability/20:30 decisions, conservative SEC next-session-close clocks and reviewed reference FX with 14-day maximum age.

## Predeclared experiment and full-period cases

Every profile starts at SGD 10,000, fee SGD 2.50 per executed order, slippage 0.05%, whole shares, long-only/unlevered, 2018-01-01–2025-12-31. Funding cohorts use SGD 0 or SGD 500 monthly. Deposits occur at each calendar month’s first exchange-session open, including January 2018: 96 deposits totaling SGD 48,000, for SGD 58,000 contributed capital in funded runs.

The amendment changes **only** RSI14 entry threshold 30→25; exit 65, 95% equity sizing, timing, risk, source revisions, engine and each comparison profile stay fixed. Schema validation, draft isolation, explicit v2 publication, parent-version link and preserved v1 configuration pass. The hypothesis predicts fewer entries/costs; improved return is not a condition of passing. All 2018–2025 is in-sample development history; year boundaries do not reset the account.

Hold enters once at 95% sizing; MonthlyDCA deploys 95% of then-available cash at monthly decisions with additions enabled. Monthly decisions normally fill at the next session open. SMA20/50 and RSI rules use completed daily histories; the SEC diagnostic enters on Item 2.02 presence and exits after 20 held sessions.

| Company | Rule | Monthly SGD | Ending equity SGD | Net/TWR return | Max drawdown | Filled orders |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| AAPL | RSI30 | 0 | 15,203.18 | 52.03% | -27.88% | 18 |
| AAPL | Hold | 0 | 58,146.14 | 481.46% | -35.91% | 1 |
| AAPL | MonthlyDCA | 0 | 63,754.15 | 537.54% | -38.16% | 9 |
| AAPL | SMA20_50 | 0 | 34,425.15 | 244.25% | -25.10% | 45 |
| AAPL | RSI25 | 0 | 15,167.44 | 51.67% | -10.14% | 8 |
| AAPL | SEC_filing | 0 | 24,340.21 | 143.40% | -23.98% | 64 |
| AAPL | Hold | 500 | 109,757.28 | 194.38% | -26.65% | 1 |
| AAPL | MonthlyDCA | 500 | 194,342.04 | 540.29% | -37.87% | 96 |
| AAPL | SMA20_50 | 500 | 118,394.52 | 239.04% | -25.03% | 45 |
| AAPL | RSI30 | 500 | 66,282.59 | 50.60% | -27.85% | 18 |
| AAPL | RSI25 | 500 | 70,879.38 | 51.01% | -10.21% | 8 |
| AAPL | SEC_filing | 500 | 104,831.03 | 147.05% | -23.60% | 64 |
| MSFT | RSI30 | 500 | 77,061.36 | 47.11% | -18.61% | 9 |

**13 primary cases and 13 repeats pass with identical complete result hashes.** One additional queued persistence run also matches its earlier result exactly. The isolated source project retains 27 completed runs; no earlier run is replaced.

### RSI amendment conclusion

| Funding cohort | Ending SGD, v1→v2 | Return, v1→v2 | Drawdown, v1→v2 | Orders | Modeled total costs SGD |
| --- | --- | --- | --- | --- | --- |
| 0/month | 15,203.18 → 15,167.44 | 52.03% → 51.67% | -27.88% → -10.14% | 18 → 8 | 163.62 → 68.50 |
| 500/month | 66,282.59 → 70,879.38 | 50.60% → 51.01% | -27.85% → -10.21% | 18 → 8 | 371.11 → 162.79 |

**Mixed outcome:** the unfunded version loses SGD 35.74529879275 of ending equity despite materially lower drawdown/costs. The funded version gains SGD 4,596.78894315950 of ending equity and slightly improves flow-adjusted return. No automatic promotion, discarded worse result or future-performance claim follows. Ending balances across different contribution cohorts are not strategy-return comparisons.

| Year | No deposits v1 | No deposits v2 | SGD 500/month v1 | SGD 500/month v2 |
| --- | ---: | ---: | ---: | ---: |
| 2018 | 1.48% | 21.29% | 1.67% | 21.09% |
| 2019 | 22.25% | 8.07% | 21.23% | 7.72% |
| 2020 | 18.76% | 0.00% | 18.45% | 0.00% |
| 2021 | 9.36% | 0.00% | 9.22% | 0.00% |
| 2022 | -10.40% | 0.00% | -10.01% | 0.00% |
| 2023 | 12.11% | 0.00% | 11.78% | 0.00% |
| 2024 | 3.27% | 7.44% | 3.14% | 7.38% |
| 2025 | -9.04% | 7.70% | -8.97% | 7.82% |

Annual, quarterly and monthly exports retain the preceding equity/performance mark, positions, cash and receivables. Deposits are separated from P&L; funded returns/drawdowns use flow-linked time-weighted performance. Cash references receive matching deposits and assume zero interest. SPY is a tradable S&P500 proxy using the same profile/cost/funding assumptions, not a costless index series.

## Independent financial and causal verification

An independent **stdlib-only Decimal34 checker with no application imports** reconstructs:

- **52,286 strategy/benchmark daily marks**, **26,143 decisions**, **1,064 fills** (including independently reconstructed benchmark fills) and **1,570 primary strategy ledger entries**.
- Completed observations and FX available at each decision/fill; 14-day FX age; next-session execution; independently sized quantities and affordability/rejections; fees/slippage; splits, dividend entitlements/payment FX; contributions; pooled basis and remaining positions.
- All primary year/quarter/month reports (8/32/96 periods), carried capital, period returns/P&L, and 26,143 daily cash-only reference balances. No annual portfolio reset is substituted.
- All 96 deposits in each funded strategy and its matching benchmark; total SGD 48,000; opening pre/post-flow values and TWR. Actual/365 investor-return discounted-cash-flow residual is below SGD1e-7 (observed maximum `8.731149137020111e-11`). UTC elapsed times preserve DST correctly.
- SGD money tolerance 1e-18; float/return tolerance 1e-12. Exact replay hashes use complete saved results, not rounded table values.

Explicitly **SYNTHETIC adversarial copies** of real inputs perturb post-2022 prices, available FX, actions and SEC categories. Funded RSI30, MonthlyDCA and SEC strategies each retain identical pre-2023 equity/signals/ledger prefixes across 1,259 sessions. Mutated data/results were not imported or represented as real performance.

## Backup, restoration and persistence

A custom PostgreSQL backup is restored into a second fresh isolated database and accessed through a separate API. All 26 previously completed result payloads, dataset/source exports, strategy versions, profiles and all three intake reports/packages match the source snapshot. A job queued before backup remains queued after restore, then executes in a restored worker with exactly the expected result. The source job remains queued during that restore test, proving database separation.

Only the new source test project’s database/API/frontend are then restarted. Its named volume preserves the original snapshot, and restarting its worker completes the saved queued job with the same hash. A later frontend-only recreation preserves all 27 completed results and all published versions.

- Backup bytes: `9123164`.
- Backup SHA-256: `a9ae47c8d93c646efa0aedaa17039e3c8108f1f98efdf42c63cb6e9fb576408f`.
- Queued persistence run: `a119ec10-c5e4-4688-8e43-8a8ab6396712`.
- Temporary restore containers are removed; original test project and source volume remain.

## Browser finding, fix and tests

The initial full-history browser test exposed a genuine UI slowdown: thousands of independent Recharts ReferenceDot registrations made comparison controls time out after enabling decision markers. The fix renders point-only series grouped by strategy/event kind. All 2,011 decisions remain plotted and individually inspectable; duplicates for the same date/series/kind retain the previous consolidation behavior. No engine, signal, order or accounting behavior changes.

A second UI defect reset the zoom when brush/click handling rebuilt chart data. Memoized chart observations, separate brush interactions and a retained date-range selection now keep the viewport stable until the history changes.

Six new frontend tests cover all 2,011 markers, separate strategies/financial measures, absent/duplicate observations, distinct intraday timestamps and zoom retention/reset. Final real Chromium verification passes **17 research UI checks** (13 comparison/report checks plus 4 zoom/selection checks): v1/v2 comparison, deduplicated cash/SPY references, assumption mismatch warnings, retained decision reasons/indicator evidence, all decision markers, annual/quarter/month reports, deposit-neutral charts, mobile rendering, actual brush zoom, retained-session clicks and a zoom range that survives changing the chart measure. Three live company onboarding cases also pass. Screenshots were visually inspected; final browser runs report no runtime errors.

**Required checks:** 231 backend tests including PostgreSQL pass with no skips; 42 frontend tests pass; Ruff lint/format, Prettier, TypeScript/Vite build and Docker builds pass. Vite’s existing bundle-size advisory and third-party backend deprecations remain.

### Test-harness corrections

The first SPY browser expectation incorrectly assumed an existing reviewed SEC stream; the corrected test approved accounting only and retained its filing candidate unreviewed. The first restore attempt reached PostgreSQL’s temporary initialization Unix socket; the final procedure waits for the final TCP listener. The independent investor-return checker initially mixed wall-clock and elapsed-time arithmetic across DST; correcting it to UTC elapsed time resolves the residual. These were verification-harness issues, not engine changes. Final checks above include their corrected successful runs.

## Next actions

1. Review the [completed live user-prompt acceptance](llm-user-workflow-verification-2026-11-07.md), including the unnecessary refusal and source-readiness blocks. External disclosure approval was received and used for that bounded test.
2. Keep the research journal/conclusions with these runs; implement the journal product UI if desired, using existing versioning/simulation APIs.
3. Qualify full-period histories for additional user-selected companies. The earlier NVDA pilot remains bounded to 2024; this test does not extend it to 2018–2025.
4. Historical sectors, original-version news/ratings and Congress disclosures remain separately blocked source capabilities. They are not required by the accepted indicator/accounting cases.

See [research workflow](continuous-research.md), [onboarding contract](company-onboarding.md) and [known limitations](known-limitations.md).
