# Real SPY source review and backtest acceptance — 2026-11-05

Status: **real combined revision imported; six backtests and six identical repeats completed; independent financial reconciliation passed**. These are measured results from real source data under the disclosed model, not synthetic demonstrations or out-of-sample evidence. Engine 1.3.0 and its accounting behavior were unchanged in this pass.

## Frozen dataset and source review

New dataset: `051e4285-e374-4b44-b82c-a54ffc8a6a6e`.

- Content hash: `de0dac7e7817309877fe9ef4697b3b047fde1f880e65b7c3de1bf292e47a4ce8`.
- Review-manifest SHA-256: `50815c44fcd336f0211e8fcc51c9735e06deaaf65da7f31b2b1cc0578b645d6f`.
- 2,514 real raw SPY SIP bars, 2016–2025, with no required-session gaps. Existing price-only revision and its bars remain unchanged. The 2016–2017 observations warm the indicators; trading begins at the profile start.
- 2,494 numeric ALFRED initial-release USD/SGD observations; 115 initial missing rows remain omitted. All 6,033 opening/closing/decision clocks for 2018–2025 pass the explicit 14-day age policy. Maximum age is 12.3541667 days. Seven days fails at 2,142 clocks after the conservative correction below.
- 40 US SPY dividends, 2016–2025. US issuer ex-dates, full-precision amounts and payment dates are retained. All 40 amounts match original dated issuer USD announcements published before the effective US open. No split events were identified after the documented coverage review.

FRED was fetched again in three bounded first-release windows: all retained numeric dates/values match. The original audit's flags received explicit dispositions. Missing initial values stay omitted, including the 2021-02-24 missing value; no later numeric value replaces them. The 2021-03-12 numeric flag matches the appropriate March15 weekly table, although its FRED vintage was later. Failed constructed URLs and conflicting current archive labels are retained as limitations; they are not treated as original publication clocks. ALFRED first-vintage metadata remains the timing authority, with an additional following-week floor and next-midnight New York boundary. See [FRED's initial-release contract](https://fred.stlouisfed.org/docs/api/fred/series_observations.html) and [the Fed's weekly-release policy](https://www.federalreserve.gov/releases/h10/default.htm).

One actual timing anomaly required a conservative change: the 2018-07-23 observation had a same-day FRED vintage. Its value, 1.3653 SGD/USD, matches the appropriate [weekly table labeled July31](https://www.federalreserve.gov/releases/h10/20180730/). Availability is delayed to **2018-08-01 00:00 New York**, after that evidenced release; the numeric value is unchanged. No availability is advanced.

Corporate-action reconciliation uses the [US issuer historical distribution workbook](https://www.ssga.com/library-content/products/fund-data/etfs/us/spdr-etf-historical-distributions.xlsx) for US dates/amounts. Original issuer announcements were retained from the [ASX annual announcement archive](https://www.asx.com.au/asx/v2/statistics/announcements.do?by=asxCode&asxCode=SPY&timeframe=Y&year=2020). Only matching USD amounts and exchange publication times are taken from those notices. **Australian CDI ex-dates, payment dates and AUD conversions are not imported.** Archive minute timestamps use Australia/Sydney with DST and are rounded forward one minute. Both originals and amendments are retained; the latest matching notice before the US open is selected conservatively. The archive's two misspelled titles and a later FX notice mislabeled as a rate notice are explicitly handled in the evidence log.

This supplies the dividend missing from Alpaca (2018-06-15) and the seven missing payment dates from the US issuer record. The issuer amount 1.366242 is retained for 2020-06-19, with Alpaca's 0.0000001 difference recorded. A December2025 Australian notice incorrectly labels the US payment January31 (Saturday); the US workbook and Alpaca agree January30 (Friday), which is retained. The reviewed split evidence combines zero Alpaca action records, identical raw versus split-adjusted OHLCV on all 2,514 bars, and [an independent split-history publisher reporting zero splits](https://www.splithistory.com/spy/). Source completeness is not guaranteed by any one of these checks.

Private evidence is retained under `.local/combined-spy-20261105-v2/`, including the manifest, 113 hashed source files, original/extracted issuer notices, FX/action review ledgers, normalized CSVs, combined payload and preflight results. Original source files remain private and uncommitted. The source-review transformation module has twelve regression cases; full backend/PostgreSQL checks pass **121 tests**, with Ruff lint/format passing. Frontend code is unchanged; its latest verification remains 17 passing tests and a successful production build.

Final source refinement: 39 US payment dates also match the original pre-open ASX notices. For December 2025, the issuer's [SGX announcement](https://links.sgx.com/1.0.0/corporate-announcements/16ETHGOSVMS2TAW4/68fec87094fb02499708a6cac8bba8714c9434bc6a26ca1bb81f8b49b0c24cea) corroborates US payment on January 30, 2026. Complete action availability is therefore **2025-12-18T23:57:43Z**, one second after that later broadcast, rather than the earlier amount notice. No SGX ex-date is used. The original combined revision `98ced3fa-4ab5-4ea4-ba23-04409ed2bd8e`, its manifest and all first-stage runs remain retained. The final revision changes only that later availability and source provenance; all six sets of financial records match the first stage exactly (policy-warning text differs). The final six runs and their six repeats were executed again; the final revision is the accepted baseline. Source-delta proof and SGX addenda are retained beside the final evidence.

## Shared assumptions and definitions

- Starting capital SGD 10,000; fixed fee SGD 2.50 per executed order; adverse slippage 0.0005 (0.05%); zero additional spread/percentage commission/FX markup.
- SGD account; published reference FX, maximum observation age14 days. Whole shares, long-only, unlevered; no protective stops or take-profit orders.
- All three strategies size new entries at **95% of current equity**, bounded by available cash and costs. This is an explicit acceptance convention, not a fully invested SPY total-return series. The independent benchmark targets100% with the same execution/accounting rules.
- Buy and hold: enter when flat; no ordinary exit. SMA20/50: enter on a20-over50 crossing, exit on the opposite crossing. RSI14 uses Wilder smoothing; enter below30 and exit above65.
- Signals use completed permissible bars at 20:30 New York and quantities determined at that decision, then execute at the next eligible US open. Positions and cash carry across years. No fictitious final liquidation is added.
- Research period 2018–2025 is the user's full iterative-development interval (`in_sample`). Supplemental2019–2022 runs also satisfy the original acceptance interval. The two intervals start independent portfolios; annual subreports within a run do not reset them.

## Actual results

### Full continuous 2018–2025 — 2,011 sessions

| Strategy | Ending equity SGD | Net return | Maximum drawdown | Executed orders |
| --- | ---: | ---: | ---: | ---: |
| Buy and hold | 25,146.74 | +151.47% | −30.06% | 1 |
| SMA20/50 crossover | 18,835.59 | +88.36% | −26.97% | 33 |
| RSI14 mean reversion | 12,369.83 | +23.70% | −26.20% | 16 |

The100%-target benchmark ends at SGD25,729.40. The differing initial allocation explains why it is not identical to the 95%-target hold strategy.

### Yearly net returns from those same continuous portfolios

| Year | Buy and hold | SMA20/50 | RSI14 |
| --- | ---: | ---: | ---: |
| 2018 | −2.42% | +6.94% | −1.67% |
| 2019 | +26.46% | +10.50% | +13.38% |
| 2020 | +14.99% | +19.35% | +0.21% |
| 2021 | +28.36% | +21.25% | +0.00% |
| 2022 | −17.20% | −23.82% | −1.28% |
| 2023 | +21.00% | +10.86% | +10.82% |
| 2024 | +25.09% | +20.08% | +0.00% |
| 2025 | +10.16% | +8.62% | +1.21% |

Period returns compound to the saved ending equity; period order/fee totals reconcile to the full run. Zero returns can represent an inactive cash portfolio; cash interest is not modeled.

### Supplemental 2019–2022 — 1,008 sessions

| Strategy | Ending equity SGD | Net return | Maximum drawdown | Executed orders |
| --- | ---: | ---: | ---: | ---: |
| Buy and hold | 15,633.57 | +56.34% | −30.12% | 1 |
| SMA20/50 crossover | 12,243.73 | +22.44% | −25.60% | 17 |
| RSI14 mean reversion | 10,539.61 | +5.40% | −26.25% | 7 |

## Independent arithmetic and reproducibility

A standalone stdlib-only program imports no application engine, ledger, indicator or FX helper. It independently reconstructs every strategy/benchmark daily cash and equity mark, dividend entitlement/payment and final receivable, full share position, entry quantity, executed price, historical FX, commission, SMA crossing and incremental Wilder RSI signal. It also reconciles net return, drawdown, volatility and Sharpe. All **9,057 strategy signals/marks plus 9,057 benchmark marks**, **75 strategy fills** and **262 strategy ledger entries** pass. Money tolerance is1e−20 SGD; floating reporting metrics use1e−12. The complete check/output are `.local/reconcile-real-spy.py` and `independent-reconciliation.json`.

One independently checked fill: the hold signal at 2018-01-02 20:30 New York sizes26 shares using close268.77 and signal-available FX1.3441. The later published rate1.3363 becomes available at midnight before the January3 open; it is used for the fill, not the earlier sizing decision. Raw open268.96 becomes USD269.094480 after slippage. Cash debit is `26 ×269.094480 ×1.3363 +2.50 = SGD9,351.8647942240`, leaving SGD648.1352057760.

At the 2025 final mark, the hold strategy has26 shares, cash SGD2,311.4203740662 and an unpaid USD51.827568 December dividend due2026-01-30. With close681.92 and permissible FX1.2842, independently recomputed equity is SGD25,146.7406008918. That dividend is valued as a receivable and has not been spent or booked as early payment.

All six primary results match their six repeat results exactly. Frozen dataset/profile/configuration/engine provenance and all saved result hashes revalidate; annual linked returns, orders and fees reconcile. The original raw SPY revision and earlier synthetic baseline result remain unchanged. The adverse future-history diagnostic is recorded separately in `causal-prefix-check.json`; it uses visibly synthetic in-memory perturbations, never a replacement historical dataset.

| Interval / strategy | Primary run | Identical repeat |
| --- | --- | --- |
| 2018–2025 hold | `287fed4c-d350-4da9-9882-bdeece14159f` | `ca85887e-d1a4-48ce-b50e-f754209072cc` |
| 2018–2025 SMA | `9e7572a6-fc10-49aa-b4d4-bdf8cc713b54` | `49a8f01e-36bc-437f-adea-9147d33509f5` |
| 2018–2025 RSI | `07321c46-d8ec-499f-959b-154a95ba94ec` | `781d81a2-ea45-4c6d-8fe6-7fdd21d8bd70` |
| 2019–2022 hold | `614ab680-7ed0-4e45-94ee-27eaa6df5a76` | `305fc1a7-595b-4074-96e2-c2f4e76ca838` |
| 2019–2022 SMA | `e1fcae44-4ab3-4eae-a817-4ccc6d08ae39` | `55ecdeec-d2d5-49dd-afd8-cb5ddc1687e4` |
| 2019–2022 RSI | `7c998261-78e5-4526-92c9-1f0b128acf01` | `50e2ebd5-2876-4116-b2a2-57256508d383` |

## Limits and remaining work

The future-mutation check passed for all three full-period strategies: replacing2022–2025 price/volume/FX/dividend inputs in a clearly labeled synthetic in-memory diagnostic leaves all 1,008 earlier sessions' signals, order sizing, fills/ledger and equity unchanged. No altered history was imported. Results and prefix hashes are retained in `causal-prefix-check.json`.

These results use real historical observations under a reviewed **reference-FX research policy**. They are not executable broker FX or proof of original price-vendor vintages: raw SIP history is revised data with the pre-existing assumed20:15 New York availability. ALFRED first releases are retained without replaying later revisions. Publisher archive conflicts are dispositioned using the stated authority; original intraday FX publication was not certified for every row. Source coverage review is bounded by the available records.

The financial model has full opening fills and fixed daily costs, no liquidity/impact model, no tax/withholding, cash interest, automatic dividend reinvestment or forced final sale. Improvements made after examining2018–2025 remain development results. QQQ/SMH/XLE still require their own action reviews and combined revisions. Real Fear & Greed/news/event integration and stricter vendor-vintage certification remain unverified. This pass did not rebuild/restart application containers or change engine behavior, and does not establish a new backup/recovery test.
