# Funding, timing and position sizing (engine 1.4.0)

Strategies control conditions, decision schedules, sizing and exits. Profiles
control account funding, costs and portfolio constraints. Published versions,
dataset revisions and run snapshots remain immutable; create new versions/runs
to compare changes. This extension requires no provider keys or schema migration.

## Monthly salary contributions

`ProfileConfig.monthly_contribution` is a nonnegative fixed amount in account
currency, default zero. It is credited at the **first XNYS session open of each
calendar month**, including the starting month if that session is in the run.
A run starting midmonth receives no retroactive deposit. There is no warm-up
funding or deposit on weekends/holidays. No withdrawals or variable income
schedules are modeled.

The opening sequence is splits, dividend entitlement and payment, pre-flow
valuation, contribution, then protective and queued orders. Pre-flow equity
includes receivables and uses opening prices and only FX available at the open.
An existing order keeps the quantity calculated at the previous decision clock;
the engine never sizes it against tomorrow's salary or prices. A contribution
does not force an investment: the strategy still decides what to do with cash.

## Strategy controls

Existing strategies with no `trading` object retain one entry while flat and
full rule exits. Explicit new policy:

```json
"trading": {
  "entry_schedule": "monthly",
  "exit_schedule": "daily",
  "allow_additions": true,
  "exit_fraction": "1"
}
```

- Schedules filter **close decisions**, after the completed daily candle is
  available. Daily, first session of the calendar week/month, and once are entry
  choices. A monthly decision therefore fills at the following eligible open,
  normally the second trading session. Starting midmonth does not invent a
  first-of-month signal. Weekly/monthly eligibility is not deferred if a rule is
  false or a candle is unavailable.
- `once` retries daily until the first successful buy for that symbol; after
  that fill it never re-enters, even after an exit. An unfilled last-day order
  remains pending. This is distinct from recurring DCA.
- `allow_additions` permits buys into an existing position. It does not bypass
  cash, aggregate same-symbol allocation, exposure or position limits.
- `exit_fraction` sells that fraction of the current position when the scheduled
  exit rule is true. Exit rules take priority over entry/rebalance rules. Values
  below one can leave a residual too small for a whole-share partial exit; full
  exits can liquidate split-created fractional residuals. Minimum notional and
  affordability still apply, including sell fees. Protective exits remain full.
- Minimum holding sessions constrain ordinary sells, measured conservatively
  from the latest addition. They do not prevent additions or protective exits.

Sizing modes:

| Mode | Meaning at the decision clock |
| --- | --- |
| `equity_percent` | Fraction of current total equity as an order budget |
| `fixed_notional` | Fixed order budget in account currency, including costs |
| `cash_percent` | Fraction of currently available cash as order budget |
| `target_allocation` | Move toward a fraction of equity held in this symbol; buy a positive gap or trim a negative gap |

The last two require an explicit trading policy. Percentages are fractions in
[0,1]; zero is permitted only for target allocation. Target trims may execute
without enabling additions. A target is a decision-time objective, not an exact
execution-time guarantee: next-open gaps, rounding, fees and risk rejections can
prevent reaching it. The engine does not repeatedly resize orders at execution.
Multiple symbols consume shared cash in deterministic symbol order and may
compete for affordability; this is not a portfolio optimizer.

Examples with entry always true and exit always false:

- Lump sum: cash fraction 1, entry once, additions disabled.
- Monthly DCA: fixed notional 500, entry monthly, additions enabled.
- Deploy salary/residual cash: cash fraction 1, entry daily, additions enabled.
- Maintain an allocation: target allocation 0.60, entry daily, additions enabled.

These examples are configurations, not investment recommendations. The profile
contribution can be zero or any explicitly chosen amount, independently of the
strategy order budget.

## Accounting and performance

Additions pool quantity and account-currency cost basis; protective prices use
quantity-weighted execution price in USD. Partial exits allocate cost basis pro
rata, and the final exit consumes the exact remaining basis. Trade statistics
count completed **exit tranches**, not independent tax lots or necessarily whole
roundtrips. Holding duration starts at the original pooled entry. Split and
dividend accounting continues to use chronological holdings and historical FX.

For funded profiles, overall and period returns, volatility, Sharpe and drawdown
use linked time-weighted performance. For preceding close A, pre-deposit opening
equity B, post-deposit equity C and current close D, daily growth is
`(B/A) * (D/C)`. Without a deposit it is `D/A`. Thus the overnight market/FX
return remains counted and deposited principal is excluded. The curve stores
actual equity, flow/pre-flow/post-flow amounts and `performance_equity`, a
cash-flow-neutral curve starting at initial capital. A total loss remains a
100% cumulative time-weighted loss after recapitalization.

Reports separately show initial capital, contributions, ending account equity
and investment P&L = ending equity − initial capital − contributions. Period
reports subtract that period's deposits and use the preceding session's mark.
Turnover for funded runs uses total contributed capital as denominator. The
simple cost-add-back return is unavailable for funded runs; gross return is a
separate chronological zero-cost replay with the same contribution schedule.

Investor money-weighted return is an annualized actual/365 cash-flow IRR for
positive deposits and the final portfolio value. It is unavailable for runs
shorter than 365 elapsed days or a root outside the bounded numerical search.
It does not assume liquidation costs at the terminal mark. Same-day opening
initial capital and salary are separate external contributions.

The funded benchmark uses the same initial capital and deposits and targets
100% in the benchmark with daily additions, subject to the same next-open,
rounding, cost and risk rules. Prior zero-contribution benchmarks retain their
historical behavior. Compare only runs with matching profile, data, engine and
external-input hashes; repeated historical optimization remains in-sample work.

TWR methodology reference: [GIPS Standards Handbook](https://www.gipsstandards.org/standards/gips-standards-for-firms/gips-standards-handbook-for-firms/).
