# Synthetic acceptance demonstration

Verified with engine 1.1.0 on native PostgreSQL 16; the scenario also passed on SQLite.

This is deterministic SYNTHETIC data, not actual SPY or FX performance. The real-data scenario remains unverified because no provider credentials or real FX source files were supplied.

Profile: SGD 10,000; SGD 2.50 per executed order; 0.05% slippage; 2019–2022; long-only, 1x leverage. 2018 observations provide warm-up.

| Strategy | Final SGD | Net return | Max drawdown | Sharpe | Orders | Fees SGD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Buy and hold SPY | 9888.76 | -1.11% | -22.31% | 0.034 | 1 | 2.50 |
| MA crossover 20/50 | 17656.00 | 76.56% | -12.28% | 1.855 | 16 | 40.00 |
| RSI mean reversion | 3740.80 | -62.59% | -62.59% | -2.986 | 17 | 42.50 |
| MA crossover 10/30 (v2) | 34360.43 | 243.60% | -9.01% | 3.992 | 16 | 40.00 |

Verified through the API and worker: create/import/publish/schedule/persist/retrieve; original results unchanged after publishing revised periods and editing profile fees; all earlier signals, eligible fills, and equity unchanged after replacing later prices, volume, and FX after 2020-06-30.

Dataset content hash: `35a0e4211fa7dad44e340dba64997da8e812215e9ac7352b2c0d3a82f957541b`.

Use `python -m app.demo` from backend to reproduce. View equity curves, individual orders, signal rules, fees and open positions in the web UI. This script creates explicitly labeled demo resources in the configured database.
