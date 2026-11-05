# Performance timeline and comparisons

## Retained intraday marks and source evidence

Engine 2.0 results can retain timestamped intraday marks. When every compared run
has these marks, choose Timeline resolution → Retained intraday valuation clocks,
then inspect a session/valuation clock. Markers attach to the first saved valuation
at or after their actual event time; these are account values, not fill prices.
Daily metrics remain daily. Old runs acquire no invented intraday observations.
Decision records can show evaluated expression values, selected status, sizing
rule and linked news/report/disclosure evidence with separate publication and
availability clocks. Source evidence displayed is evidence used by saved rules,
not an exhaustive news feed. Resolved rejected/cancelled orders retain clocks in
new runs; older runs may expose submission time only.

Completed backtest reports and the Compare page share an account-value timeline.
It uses saved results; opening the report does not rerun or modify a strategy.
The original timeline-only change retained engine 1.4.0 financial behavior; the 2.0 extension above adds separately reviewed execution capabilities.

## Use the views

1. Open a completed backtest. The chart shows the strategy, its saved
   buy-and-hold benchmark and a cash-only baseline. SPY is labeled as the S&P 500
   proxy when it is the profile's benchmark. Other benchmark symbols retain their
   own labels; missing market benchmark data is not invented.
2. Click a chart date or use **Inspect session** and the previous/next controls.
   The selected session shows recorded account value, available cash, exposure
   and drawdown, with executions, account events, decisions and order submissions.
3. Expand an event to see its stored reason and original audit fields. Conditions
   are translated into readable expressions without reevaluating historical
   indicators. New York session dates handle UTC rollover and daylight saving.
4. Buy/sell markers identify fills; other markers identify contributions and
   corporate actions. Enable all-decision markers to include hold decisions for
   the audited run. Markers sit at the session's closing account value, not at a
   fictional intraday account value or execution price.
5. Drag the chart's range handles to zoom. Funded runs can switch between actual
   account balance and time-weighted performance scaled to initial capital.
6. On **Compare**, select an experiment or up to six completed runs manually.
   Runs can be different published versions of one strategy or different
   strategies. Labels retain the version and short run ID. Choose the audited
   run to inspect its decisions while retaining the overlaid curves.

Shared-assumption benchmark curves are deduplicated by dataset, frozen profile
and engine. Different assumptions retain distinct reference curves and the
existing comparability warning; dataset/profile/engine/external-input equality
still governs strict comparisons. Unlike account currencies are not overlaid:
the chart follows the audited run until a common currency is selected. Missing
session valuations are reported, never interpolated into audit snapshots.

## Cash-only baseline

`GET /api/research/runs/{id}/cash-benchmark` is a read-only reporting endpoint for
completed runs. It computes Decimal account-currency cash from the run's frozen
initial capital plus **recorded external contributions available by each saved
valuation clock**. It ignores trading/dividend proceeds and does not infer new
deposits from an edited profile. Interest, FX conversions and trading costs are
zero. This is explicitly a modeled cash baseline, not historical bank, Treasury
bill or money-market performance. Investment P&L, TWR and drawdown are zero;
deposits increase account balance and contributed capital only.

No dataset, published version, engine result or profile snapshot is rewritten.
No market-data or LLM key is needed for these reporting views. The market
benchmark retains the original run's engine/cost/funding assumptions.

## Explanation limits

Explanations show saved rule outcomes, external-input audits and order/ledger
reasons. Older runs do not necessarily retain each indicator value or a precise
reason why no order was submitted. No retrospective LLM rationale is generated.
Order submission and execution dates are distinguished. Rejected/cancelled
orders lack their own outcome timestamp in current results, so they are listed
under submission with that limitation disclosed; no rejection-time marker is
invented. Full account/position reconstruction between daily marks is not
claimed. News/geopolitical annotations require a separate qualified event source
and are not added by this reporting change.

## Verification (2026-11-05)

Backend: 140 tests including PostgreSQL, Ruff lint/format pass. Frontend: 26 tests,
Prettier and production build pass. New cases verify cash-flow chronology and
Decimal precision, read-only API behavior, market-local session mapping,
chart-to-audit selection, stored execution/rejection reasons, version/strategy
overlays, benchmark deduplication, currency isolation and missing dates.
Percentage formatting now accepts valid Decimal JSON strings; this also fixes
previously blank exposure and period-return percentages.

Deployment/browser evidence is recorded in `verification.md`; private screenshots
and machine-readable checks are retained under `.local/ui-timeline-20261105/`.
The Vite bundle-size advisory and existing third-party deprecation warnings
remain; neither is hidden.

Deployed Chromium verification passed 12 checks on a real SPY report and a
three-strategy comparison, including chart clicks/zoom, normalized performance,
reference deduplication, real partial-sale audit and mobile rendering. The
audited-run selector accessibility issue found by this check was corrected and
retested. Ten retained result hashes and the reviewed dataset remain unchanged;
all 7,407 cash-baseline marks for those runs independently reconcile. The worker,
database and 22 unrelated containers retain their original identities.
