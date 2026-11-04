# Chronological execution and financial accounting

## Per-session ordering

1. Check cancellation/ownership; advance to the official XNYS open.
2. Apply known effective splits to positions, per-share entry prices and pending quantities. Cost basis remains unchanged. Accrue dividend entitlements for pre-open holders on ex-date; settle receivables on the first trading session on/after their declared payment date.
3. Fill previously submitted market orders at this session's raw open, only when submitted strictly before this opening. Symbols/orders are processed in stable order. Reject zero-quantity, no-volume, duplicate-position, position-count, allocation, exposure, cash and minimum-notional violations. Rejections cost nothing.
4. Process active protective orders against daily OHLC. Stops take precedence if both levels are touched. Stop gaps fill at the worse opening price; otherwise stop threshold. Take profits fill at threshold without favorable gap improvement. Apply adverse slippage/spread. Stops override minimum holding periods. Frequency limits still apply to every executed order.
5. Advance to the dataset decision clock: official close + 30 minutes for regular-session CSV data, or 20:30 America/New_York for Alpaca full-day volume. Materialize only completed candles whose availability timestamps have passed. Strategy indicator history is split-adjusted using only actions effective and known at this clock. Late candles are not used early, and stale observations do not generate fresh signals.
6. Mark positions and unpaid receivables using latest permissible prices/FX. Evaluate exit/entry rules against the restricted data view. Generate future market orders with quantity determined from this clock's prices, FX and equity. Prevent duplicate pending orders and repeated buys into an existing position. Regular exits respect minimum holding sessions.
7. Record equity, cash, exposure, P&L, signals, orders and ledgers; advance. Pre-period data warms indicators but cannot generate pre-period trades.
8. Retain open positions and pending orders at the final mark. No automatic liquidation or invented commissions.

The simulator may inspect a daily range only to fill already-active protective orders. It never passes a future daily high/low to signal generation. Because OHLC cannot determine an intraday touch time, non-gap protective fills are booked at close with close-available FX. This deterministic convention is disclosed rather than assigning a fictional intraday path. Gap stops use opening FX. Daily bars are a simplified full-fill execution model, not a liquidity/order-book simulation.

## Cash ledger

Decimal precision is 34 within each simulation. Monetary JSON uses decimal strings; no intermediate cash ledger rounding is performed. Charts convert strings to floats only for display. USD/SGD is **SGD per USD**. USD-account profiles use 1 and no FX markup.

- Buy: `cash -= quantity * execution_USD * historical_FX + fixed_fee + notional * commission_pct + notional * fx_markup`.
- Sell: `cash += quantity * execution_USD * historical_FX - fixed_fee - notional * commission_pct - notional * fx_markup`.
- Buy execution: open × (1 + slippage + spread/2); sell: open × (1 − slippage − spread/2).
- Cost basis includes entry commission and FX markup; realized trade P&L is net proceeds minus entry basis. Each exit closes the whole position; no pyramiding or partial fills.
- Equity = cash + marked securities + marked USD dividend receivables. Cash never borrows. Dividend entitlements survive selling before payment; unpaid entitlements remain in final results. Cash interest, leverage, shorting, taxes and top-ups are absent.
- Whole-share restrictions apply to new buy orders; split-created fractional holdings can be sold. Cash-in-lieu is not modeled. External action completeness is the source owner's responsibility.

## Statistics

Net return = end/start − 1. Gross return is a full zero-fee/slippage/spread/FX-markup replay: quantity and even trades can differ because affordability changes. `cost_addback_return` instead adds cumulative ledger costs to net ending equity; it is attribution, not that counterfactual replay.

Daily returns include starting cash as the initial value, then consecutive marked daily equity values. Volatility uses sample daily standard deviation × sqrt(252); Sharpe is `(mean_daily_return − annual_risk_free/252) / sample_stddev × sqrt(252)`. The default risk-free rate is zero. Zero volatility produces null Sharpe. CAGR uses `(end/start)^(252/session_count)-1` only with at least 252 sessions. Drawdown is equity/running_peak − 1, including starting capital as the first peak; duration is consecutive underwater sessions.

Trade win statistics use completed round trips and entry/exit costs; dividends are portfolio income, not attributed to round-trip win/loss statistics. Profit factor is summed positive realized P&L / absolute negative P&L, null with no losses. No-trade win rate/average holding periods are null. Exposure is the mean daily marked securities/equity; turnover is total executed account-currency notional / starting capital. Benchmark uses the same next-open, costs, dates, FX and dataset with a 100%-target buy-and-hold configuration and an independent portfolio.
