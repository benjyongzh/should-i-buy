# Chronological execution and financial accounting

## Per-session ordering

1. Check cancellation/ownership; advance to the official XNYS open.
2. Apply known effective splits to positions, per-share entry prices and pending quantities. Cost basis remains unchanged. Accrue dividend entitlements for pre-open holders on ex-date; settle receivables on the first trading session on/after their declared payment date.
3. Process opening gaps on carried positions using only opening quotes, in symbol order: a stop already crossed fills at the worse open; an already-crossed take-profit fills at its threshold without favorable gap improvement. A successful protective exit cancels a redundant queued exit without another commission. Then process eligible previously submitted market orders at this session's raw open in submission order, followed by any immediately active opening protection on new positions. Reject invalid quantities/sides, duplicate positions, position-count, allocation, exposure, cash and minimum-notional violations. Allocation/exposure use marked securities and post-cost equity. Rejections cost nothing. Final daily volume is not known at the open and cannot gate opening fills.
4. Only after all opening events may the execution simulator inspect daily OHLC for remaining active protection. Book these unknown intraday touches at close in symbol order. Stops take precedence when both levels are touched and their sequence is genuinely unknown; a known opening take-profit cannot be overridden by a later low. Apply adverse slippage/spread. Stops override minimum holding periods. Frequency limits apply chronologically to every executed order.
5. Advance to the dataset decision clock: official close + 30 minutes for regular-session CSV data, or 20:30 America/New_York for Alpaca full-day volume. Materialize only completed candles whose availability timestamps have passed. Strategy indicator history is split-adjusted using only actions effective and known at this clock. Late candles are not used early, and stale observations do not generate fresh signals.
6. Mark positions and unpaid receivables using latest permissible prices/FX. Evaluate exit/entry rules against the restricted data view. Generate future market orders with quantity determined from this clock's prices, FX and equity. Prevent duplicate pending orders and repeated buys into an existing position. Regular exits respect minimum holding sessions.
7. Record equity, cash, exposure, P&L, signals, orders and ledgers; advance. Pre-period data warms indicators but cannot generate pre-period trades.
8. Retain open positions and pending orders at the final mark. No automatic liquidation or invented commissions.

The simulator may inspect a daily range only to fill already-active protective orders. It never passes a future daily high/low to signal generation. Because OHLC cannot determine an intraday touch time, non-gap protective fills are booked at close with close-available FX. This deterministic convention is disclosed rather than assigning a fictional intraday path. Opening protective fills use opening FX. Supplied opening prices are treated as executable quotes under the full-fill assumption; there is no volume-based liquidity model or inference of opening tradability from the day's eventual volume.

## Cash ledger

Decimal precision is 34 within each simulation. Monetary JSON uses decimal strings; no intermediate cash ledger rounding is performed. Charts convert strings to floats only for display. USD/SGD is **SGD per USD**. USD-account profiles use 1 and no FX markup.

- Buy: `cash -= quantity * execution_USD * historical_FX + fixed_fee + notional * commission_pct + notional * fx_markup`.
- Sell: `cash += quantity * execution_USD * historical_FX - fixed_fee - notional * commission_pct - notional * fx_markup`.
- Buy execution: open × (1 + slippage + spread/2); sell: open × (1 − slippage − spread/2).
- A pure execution quote supplies the same fees, FX markup, slippage and cash delta to risk checks and the ledger. For buys, post-trade equity is pre-trade marked equity plus the quoted cash delta plus the new position marked at the raw quote. Allocation/exposure constraints use this post-cost denominator, not the pre-trade balance.
- Cost basis includes entry commission and FX markup; realized trade P&L is net proceeds minus entry basis. Each exit closes the whole position; no pyramiding or partial fills.
- Equity = cash + marked securities + marked USD dividend receivables. Cash never borrows. Dividend entitlements survive selling before payment; unpaid entitlements remain in final results. Cash interest, leverage, shorting, taxes and top-ups are absent.
- Whole-share restrictions apply to new buy orders; split-created fractional holdings can be sold. Cash-in-lieu is not modeled. External action completeness is the source owner's responsibility.

## Statistics

Net return = end/start − 1. Gross return is a full zero-fee/slippage/spread/FX-markup replay: quantity and even trades can differ because affordability changes. `cost_addback_return` instead adds cumulative ledger costs to net ending equity; it is attribution, not that counterfactual replay.

Daily returns include starting cash as the initial value, then consecutive marked daily equity values. Volatility uses sample daily standard deviation × sqrt(252); Sharpe is `(mean_daily_return − annual_risk_free/252) / sample_stddev × sqrt(252)`. The default risk-free rate is zero. Zero volatility produces null Sharpe. CAGR uses `(end/start)^(252/session_count)-1` only with at least 252 sessions. Drawdown is equity/running_peak − 1, including starting capital as the first peak; duration is consecutive underwater sessions.

The first transition to zero equity is a −100% daily return. With no capital injection, subsequent flat zero-equity sessions have a documented 0% daily return convention, rather than dividing by zero; the portfolio remains worth zero and cumulative return stays −100%. Negative equity or recovery from zero without a modeled capital flow is rejected. A total-loss CAGR is −100% when the annualization horizon is eligible. Daily return ratios are calculated with Decimal before conversion for statistics.

Trade win statistics use completed round trips and entry/exit costs; dividends are portfolio income, not attributed to round-trip win/loss statistics. Profit factor is summed positive realized P&L / absolute negative P&L, null with no losses. No-trade win rate/average holding periods are null. Exposure is the mean daily marked securities/equity; turnover is total executed account-currency notional / starting capital. Benchmark uses the same next-open, costs, dates, FX and dataset with a 100%-target buy-and-hold configuration and an independent portfolio.
