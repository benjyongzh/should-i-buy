# Real equity and event-source acceptance — 2026-11-06

Status: **13 primary backtests and 13 exact repeats completed on real reviewed
inputs; independent financial, signal and causal-prefix checks passed**.
See the [interactive results and annual comparisons](real-equity-results-2026-11-06.html).
These are in-sample development results for selected surviving equities, not
out-of-sample validation or evidence of a generally improved strategy.

## Frozen inputs and shared profile

Dataset `526cf606-bbff-4d89-8b43-00eeaa5fc16f`, content hash
`bc123cb86fd083ab04555343158ec4608a527d72cb9077ef9f9bf19f116f5db7`.
The [accounting source review](company-intake-verification-2026-11-06.md) supplies
raw AAPL/MSFT/SPY bars, historical reference FX and reviewed issuer actions.
Source rules bind BLS revision `6f765c92-71a7-45b3-a5c3-1641c08d8a3a` or SEC
revision `59bbf500-1a59-4835-a69f-ab7d4a8a4a34` as appropriate.

- Continuous 2018–2025 replay: 2,011 sessions, with 2016–2017 indicator warm-up.
- SGD 10,000 initial capital, SGD 2.50 per executed order, 0.05% adverse slippage.
- Zero monthly contributions, extra spread, percentage commission and FX markup.
- Whole shares, long-only, no leverage; each case permits one selected asset.
- Entries size 95% of current equity, bounded by cash and costs. The SPY
  benchmark targets 100%; cash-only models zero interest and zero costs.
- Daily decisions at 20:30 New York; orders fill at the next strictly later
  eligible exchange open. No forced final liquidation, tax or liquidity model.
- Published strategy, profile, engine, dataset and selected source hashes are
  frozen in each run. Every repeat uses its primary's exact published version.

## Rules selected before examining results

Buy and hold enters when flat and has no ordinary exit. SMA20/50 enters on an
upward crossover and exits on the opposite crossing. RSI14 uses Wilder
smoothing, enters below 30 and exits above 65.

The two event rules are integration diagnostics: BLS enters after a positive
original payroll-change release in the preceding 24 hours; SEC enters after an
available symbol-specific Item2.02 filing in the preceding 24 hours. Both exit
after 20 held exchange sessions. They do not infer sentiment or use consensus.
No threshold was tuned after seeing these results.

## Full-period measured results

| Asset | Rule | Ending SGD | Net return | Max drawdown | Orders |
| --- | --- | ---: | ---: | ---: | ---: |
| AAPL | Buy and hold | 58,146.14 | +481.46% | -35.91% | 1 |
| AAPL | SMA 20/50 | 34,425.15 | +244.25% | -25.10% | 45 |
| AAPL | RSI 14 | 15,203.18 | +52.03% | -27.88% | 18 |
| AAPL | BLS payroll check | 21,026.35 | +110.26% | -30.94% | 112 |
| AAPL | SEC filing check | 24,340.21 | +143.40% | -23.98% | 64 |
| MSFT | Buy and hold | 53,673.71 | +436.74% | -34.52% | 1 |
| MSFT | SMA 20/50 | 22,315.40 | +123.15% | -38.35% | 40 |
| MSFT | RSI 14 | 14,796.19 | +47.96% | -18.56% | 9 |
| MSFT | BLS payroll check | 40,822.88 | +308.23% | -21.84% | 112 |
| MSFT | SEC filing check | 17,631.45 | +76.31% | -18.87% | 64 |
| SPY | Buy and hold | 25,146.74 | +151.47% | -30.06% | 1 |
| SPY | SMA 20/50 | 18,835.59 | +88.36% | -26.97% | 33 |
| SPY | RSI 14 | 12,369.83 | +23.70% | -26.20% | 16 |

The common SPY reference ends at **SGD 25,729.40**;
cash-only ends at SGD 10,000. The 95%-entry SPY strategy differs from the
100%-target reference because of initial allocation and retained cash.

## Annual returns from the continuous portfolios

Each year begins at the preceding saved account value. Positions, dividend
receivables and cash carry across years; accounts are not reset annually.

### AAPL

| Rule | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Buy and hold | -4.05% | +76.86% | +74.10% | +35.62% | -25.82% | +43.48% | +32.45% | +2.95% |
| SMA 20/50 | +9.77% | +51.90% | +59.56% | +7.91% | -20.39% | +18.50% | +23.98% | +2.52% |
| RSI 14 | +1.48% | +22.25% | +18.76% | +9.36% | -10.40% | +12.11% | +3.27% | -9.04% |
| BLS payroll check | -15.80% | +31.13% | +28.23% | +11.45% | -3.22% | +7.94% | +34.71% | -5.31% |
| SEC filing check | +16.32% | +3.82% | +32.71% | +5.18% | -14.68% | +20.22% | +15.16% | +22.24% |
| SPY reference | -2.51% | +27.50% | +15.45% | +29.12% | -17.56% | +21.53% | +25.61% | +10.33% |
| Cash only | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |

### MSFT

| Rule | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Buy and hold | +21.92% | +51.31% | +38.18% | +52.74% | -27.34% | +51.56% | +15.04% | +8.83% |
| SMA 20/50 | +14.62% | +43.44% | +6.62% | +27.38% | -28.55% | +22.89% | +1.79% | +11.80% |
| RSI 14 | +6.14% | +8.18% | +0.00% | +0.00% | -8.32% | +4.76% | +12.44% | +19.31% |
| BLS payroll check | +8.71% | +29.33% | +35.23% | +23.05% | -3.42% | +38.89% | +22.69% | +6.02% |
| SEC filing check | +8.09% | +18.24% | +17.92% | +6.94% | -0.67% | +19.89% | +9.49% | -16.10% |
| SPY reference | -2.51% | +27.50% | +15.45% | +29.12% | -17.56% | +21.53% | +25.61% | +10.33% |
| Cash only | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |

### SPY

| Rule | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Buy and hold | -2.42% | +26.46% | +14.99% | +28.36% | -17.20% | +21.00% | +25.09% | +10.16% |
| SMA 20/50 | +6.94% | +10.50% | +19.35% | +21.25% | -23.82% | +10.86% | +20.08% | +8.62% |
| RSI 14 | -1.67% | +13.38% | +0.21% | +0.00% | -1.28% | +10.82% | +0.00% | +1.21% |
| SPY reference | -2.51% | +27.50% | +15.45% | +29.12% | -17.56% | +21.53% | +25.61% | +10.33% |
| Cash only | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |


## Independent accounting and chronology

A separate stdlib-only program imports no engine, ledger, indicator or FX
helpers. It reconstructs **52,286 daily strategy/benchmark marks**, **26,143
strategy decisions**, **516 strategy fills** and **1,080 strategy ledger
entries**. It checks order sizing, incremental Wilder RSI, split-adjusted SMA
crossings, opening FX, slippage/fees, cash affordability, dividend entitlement/
payment, split quantities/basis, ending positions/receivables and net reporting
metrics. Monetary tolerance is 1e−18 SGD; floating metric tolerance is 1e−12.
The saved source-decision traces also match independently filtered, available
event IDs and original numeric values. All checks pass.

One independently checked BLS/AAPL entry: the January5,2018 payroll release
reports +148 thousand jobs and is modeled available at13:35UTC. The decision
occurs January5 at20:30NewYork; its40-share buy fills January8 at09:30NewYork.
Raw open USD174.35 becomes USD174.437175 after slippage. Available FX1.3363,
observed December29 and available January3, gives
`40 × 174.437175 × 1.3363 + 2.50 = SGD9,326.5158781000`, leaving
SGD673.4841219000. No later FX or same-day earlier price is used.

AAPL buy-and-hold starts with40 shares. The2020-08-31 split changes these to160
shares with unchanged SGD9,229.1845967800 cost basis. Dividends become
receivables on ex-dates and become spendable only at payment using then
available FX. No adjusted price series is substituted into execution.

Separate, visibly synthetic in-memory diagnostics alter only later prices,
volume, FX/actions, add a future split and remove future event records. The
2018–2021 prefixes remain exactly unchanged for AAPL SMA, AAPL BLS and MSFT SEC:
1,008 daily marks per case, plus their signals and ledgers. No altered history
was imported and no synthetic investment results are reported.

## Compatibility, repeats and preservation

All13 repeat results are exactly equal to their primaries, with matching frozen
provenance. Annual report values and cash references reconcile independently.
Two new AAPL compatibility-path controls match the corresponding daily event
financial records. All three SPY strategies match the earlier accepted SPY
daily equity and fills despite the additional equities in the combined dataset.
All38 pre-existing completed result hashes and original dataset/source rows
remain unchanged.

The compatibility daily path was slow on the combined history. Its completed
AAPL hold/SMA diagnostics are retained as controls. Seven queued compatibility
diagnostics were explicitly cancelled and retained; the complete primary matrix
uses the existing daily event path. Baseline configurations were explicitly
published with that policy as version2; source primary/repeat cases retain the
same version1/default daily-event policy. No engine behavior or prior version
was rewritten.

The backend suite passes **182 tests, one skipped**. The skipped test requires
`TEST_POSTGRES_URL`, which is unset; this phase did not re-run isolated
PostgreSQL integration. Ruff passes. Native HTTP tests succeeded when run with
permitted socket access, resolving the earlier restricted-environment harness
block. No application code, container or service restart was needed.

The standalone HTML report passed **10 Chromium checks**, including asset/rule
selection, measured totals, source-fill details, annual rows, mobile overflow,
no JavaScript errors and no external requests. A desktop chart screenshot was
visually inspected. This verifies the documentation report, not a new browser
test of the application's Backtests/Compare screens.

## Runs retained in the application

| Case | Primary | Exact repeat |
| --- | --- | --- |
| AAPL · Buy and hold | `fd519d80-e832-47b7-bbec-a9b4aad1c256` | `f42e0fa0-303d-44ec-a668-d78b83f1c899` |
| AAPL · SMA 20/50 | `34e95195-a743-48bc-93d2-484ae90c9127` | `3fba4696-3ec3-4602-b33d-6c740a831d88` |
| AAPL · RSI 14 | `78cbc7f5-612c-48e2-8337-40ee9938e0df` | `f8981a23-64d0-41c4-b677-6af6b339d3da` |
| AAPL · BLS payroll check | `97be90f9-0aa1-468d-a90d-c7f05da64752` | `e0f6fcfb-b534-41dd-98fa-ad44db6850c2` |
| AAPL · SEC filing check | `90f6082f-5293-47c3-871a-161f6584afab` | `ecd3bb25-7bf3-4353-8452-c1690f29bd87` |
| MSFT · Buy and hold | `2f74cf19-d583-469f-8a3a-e071eba6b365` | `10f3dec5-b772-4987-a2af-25d134203ebb` |
| MSFT · SMA 20/50 | `9ad38088-d052-4dd7-b0ae-c2dd39182590` | `636191a3-8018-4212-ae22-ae52275cddd4` |
| MSFT · RSI 14 | `a072969e-9eb9-4361-bd8f-9c68e1381a2c` | `2a9dd977-0768-40d8-a91a-3ed79937dee4` |
| MSFT · BLS payroll check | `c192c626-6ba4-45e7-abfb-7421ad2d47bd` | `7c29af22-628c-426e-a268-c32da053eee3` |
| MSFT · SEC filing check | `f2e669a0-ef7b-4257-bf47-fcc18d86e7ef` | `c9170a4b-97b3-41c4-9559-6c96c662238a` |
| SPY · Buy and hold | `95434e66-baf0-45e6-82ef-f41bb3ab1aa9` | `5cc58190-d96f-492f-a951-90933fd1b348` |
| SPY · SMA 20/50 | `3e2cae37-eea6-4edf-b5a2-bd122467b695` | `631fd203-11e9-4d05-950a-4b64a3ebfec6` |
| SPY · RSI 14 | `f641d63d-b2d4-4ceb-8fcf-3edb81232b79` | `3d700aff-1d9d-45f9-ba1a-33ac9976c163` |

The app's Backtests and Compare views can select these saved runs; their daily
account timelines, decisions/reasons and benchmarks are retained. Private full
results, yearly reports, cash references, receipts, independent reconciliation,
prefix diagnostics and hashes are under ignored
`.local/real-equity-acceptance-20261106/`.

## Limits

The accepted policies remain research approximations: current revised SIP bars
with evening completion, lagged reference FX, BLS five-minute delivery, SEC
next-session-close and conservative issuer announcement clocks. Exact historical
delivery vintages, executable intraday FX, liquidity, taxes and full company
news coverage are not certified. The two selected stocks have survivorship
bias; these results do not qualify an entire US stock universe. No intraday,
sector, analyst-rating, Congress or general automated ticker-onboarding
acceptance is established by this phase. Repeated changes against2018–2025
remain in-sample research, and every change should create another version/run.
