# Project Specification: Trading Lab

## 0. Your Role and Operating Instructions

You are the lead software architect and full-stack engineer responsible for designing and implementing **Trading Lab**, a self-hosted quantitative trading research platform.

The application will allow a user to create, configure, version, backtest, evaluate, and compare algorithmic trading strategies for US equities and ETFs.

The application must eventually support LLM-powered trading agents, machine learning, and live paper trading. However, the first release will focus on **historical backtesting**, with strict point-in-time information isolation.

This is a real software project, not a demonstration application.

### Development principles

1. Produce clean, maintainable, modular, production-quality code.
2. Prefer simple, reliable solutions over unnecessary architectural complexity.
3. Build the application as a functional end-to-end system, not disconnected prototypes.
4. Implement features incrementally with automated tests.
5. Document important architectural decisions.
6. Avoid introducing features outside the MVP unless they are essential dependencies.
7. Never silently substitute fabricated financial data for real market data.
8. Never allow historical strategies to access information from the future.
9. Ensure backtests are deterministic and reproducible.
10. Do not implement actual brokerage execution or real-money trading in the MVP.

You have permission to create and modify files within this project repository.

Do not delete unrelated user files, modify external projects, or execute destructive commands without authorization.

### Expected workflow

First, inspect the repository and available development environment.

Then:

1. Create the architecture and implementation plan.
2. Create an `AGENTS.md` documenting project conventions and invariants.
3. Establish the repository structure.
4. Implement the application milestone by milestone.
5. Run appropriate tests after each milestone.
6. Fix discovered issues before proceeding.
7. Keep documentation synchronized with implementation.
8. Report completed work, test results, architectural decisions, and remaining limitations.

Do not stop permanently after producing a plan or scaffold. Progress through the implementation milestones where feasible, without attempting one enormous unreviewable change.

Use appropriate, maintained library versions and pin dependencies using lockfiles or equivalent reproducible dependency specifications.

---

# 1. Product Vision

Trading Lab is a personal web application for researching and experimenting with algorithmic trading strategies.

The goal is to determine which trading strategies perform well under realistic historical market conditions and to compare them objectively.

The platform should enable users to:

- Create and manage trading strategies.
- Configure strategies through the UI without modifying source code.
- Use an LLM to generate or modify strategy configurations from natural-language instructions.
- Maintain immutable published versions of strategies.
- Backtest strategies over historical market periods.
- Run multiple strategies against identical market conditions.
- Compare performance, profitability, risk, and transaction costs.
- Inspect individual simulated trades and the reasons behind them.
- Optimize or combine strategies through structured experiments.
- Eventually integrate machine-learning models and live paper trading.

The application should ultimately serve as an experimental laboratory rather than a single trading bot.

### Primary user

A technically proficient individual running the application on personal infrastructure.

The MVP is single-user.

Do not implement enterprise multi-tenancy, organizations, billing, subscriptions, or role-based access control.

---

# 2. MVP Scope

## 2.1 Required features

The initial release must support:

1. Historical US equities and ETF market data.
2. Daily OHLCV historical candles.
3. Historical market-data ingestion and local persistence.
4. Strategy creation, reading, editing, cloning, archiving, and versioning.
5. A declarative strategy configuration format.
6. A UI-based strategy editor.
7. Reusable backtest profiles with common financial assumptions.
8. Sequential, chronological backtesting.
9. Simulated portfolio and order execution.
10. Transaction fees, slippage, and configurable execution assumptions.
11. Historical currency conversion for SGD-denominated portfolios.
12. Backtest job execution and persistent results.
13. Strategy comparison and performance dashboards.
14. LLM-assisted strategy creation and editing.
15. Automated tests covering financial calculations and look-ahead prevention.
16. Docker Compose deployment.

The MVP should support creating and evaluating strategies without requiring code changes.

## 2.2 Explicitly excluded from MVP

Do not implement:

- Live stock trading.
- Real-money brokerage integration.
- Automated brokerage order submission.
- Cryptocurrency or forex trading strategies.
- High-frequency trading.
- Options, derivatives, margin trading, or short selling.
- Full machine-learning model training workflows.
- Reinforcement learning.
- Autonomous LLM trading based on historical news.
- Intraday or tick-level backtesting.
- Multi-user authentication or account management.
- Distributed infrastructure or Kubernetes.
- Commercial subscriptions or payment systems.

Some of these features will be implemented later, so the architecture should permit extensions without major rewrites.

---

# 3. Technology Stack

Use the following stack unless there is a significant technical reason not to.

## Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- TanStack Query for API communication and caching
- React Router
- Recharts or another suitable React charting library
- React Hook Form with Zod validation where appropriate

Build a responsive dashboard-style interface.

Prioritize usability, information clarity, and functionality over decorative design.

## Backend

- Python 3.12 or newer compatible stable version
- FastAPI
- Pydantic
- SQLAlchemy 2.x
- Alembic for database migrations
- PostgreSQL
- pytest
- Ruff for linting and formatting

Use type annotations throughout the backend.

## Background processing

Implement a separate Python worker process for executing backtests.

For the MVP, prefer a PostgreSQL-backed job system with transactional job claiming, or another simple reliable mechanism.

Avoid requiring Redis, RabbitMQ, Celery, or additional infrastructure unless there is a demonstrated need.

Requirements:

- Backtests must not block HTTP requests.
- Jobs must expose status and progress.
- Failed jobs must retain error information.
- Job execution must be idempotent where applicable.
- Avoid duplicate execution when multiple workers exist.
- Support cancellation at safe checkpoints.
- Handle stale or interrupted jobs safely.

## Backtesting

Implement a small, deterministic, event-driven backtesting core with clearly defined market-data, strategy, portfolio, and execution interfaces.

You may use existing financial libraries for indicators or analytics, but the core simulation semantics must be explicit and thoroughly testable.

Do not blindly depend on a third-party backtesting framework if it makes look-ahead prevention, fee accounting, or strategy JSON interpretation difficult.

## LLM integration

Use an OpenAI-compatible LLM API, with the provider abstracted behind a dedicated service interface.

The selected API and model should be configurable through environment variables or application settings.

Use structured responses and Pydantic validation.

Never expose LLM API credentials to the frontend.

## Deployment

Use Docker Compose.

The final application should be deployable to an existing Ubuntu Linux virtual machine running Docker.

The project should run independently of any existing homelab services, while allowing connection to an external PostgreSQL instance through configuration.

---

# 4. Proposed Repository Structure

Use a modular monorepo with a structure similar to:

```text
trading-lab/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── types/
│   ├── package.json
│   └── ...
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── strategies/
│   │   ├── market_data/
│   │   ├── backtesting/
│   │   ├── portfolio/
│   │   ├── analytics/
│   │   └── llm/
│   ├── migrations/
│   ├── tests/
│   └── pyproject.toml
├── workers/
├── docs/
│   ├── architecture.md
│   ├── data-model.md
│   ├── strategy-schema.md
│   ├── backtesting-engine.md
│   ├── point-in-time-data.md
│   └── roadmap.md
├── docker-compose.yml
├── .env.example
├── AGENTS.md
└── README.md
```

The precise structure may be refined, but maintain clear boundaries between API, business logic, simulation, data, and presentation.

---

# 5. Core Domain Model

The platform has five primary concepts.

## 5.1 Strategy

A logical trading strategy, such as:

- Momentum
- Mean reversion
- Moving-average crossover
- Breakout
- RSI reversal
- Buy and hold

A strategy is the parent entity under which multiple versions exist.

## 5.2 Strategy Version

An immutable published definition of a strategy.

Contains:

- Strategy configuration
- Version identifier
- Creation timestamp
- Parent version reference, if applicable
- Optional change summary
- Schema version
- Configuration hash

Published versions must never be modified in place.

## 5.3 Backtest Profile

A reusable collection of financial and simulation assumptions.

Examples:

- Starting capital
- Account currency
- Historical date range
- Tradable universe
- Transaction fees
- Slippage
- Order execution rules
- Position and exposure limits
- Benchmark

Profiles are independent of strategy definitions.

## 5.4 Backtest Run

One execution of a specific strategy version against a specific market dataset and backtest profile.

The run stores all information required to reproduce its results.

## 5.5 Experiment Group

A logical collection of backtest runs intended for comparison.

For example:

"Momentum Strategy Variations — 2019 to 2022"

An experiment group should allow multiple strategy versions to run against the same profile and dataset.

---

# 6. Strategy CRUD and Versioning

## 6.1 Functional requirements

The application must allow users to:

- Create strategies.
- List and search strategies.
- View strategy details.
- Edit a working draft.
- Validate a draft.
- Publish a draft as a new version.
- Clone an existing strategy.
- Create a new version from an existing version.
- View version history.
- Compare two strategy versions.
- Archive a strategy.
- Restore an archived strategy.

Use soft deletion or archiving rather than deleting historical strategy definitions referenced by backtests.

## 6.2 Draft and published states

Strategies should support editable drafts and immutable published versions.

Suggested workflow:

1. User creates a strategy.
2. User configures it in the UI.
3. Changes are saved to a draft.
4. Backend validates the configuration.
5. User publishes the configuration.
6. A new immutable version is created.
7. The version becomes available for backtesting.

A subsequent edit must create a new draft derived from the published version.

Editing must never change the strategy configuration of a previously completed backtest.

## 6.3 Strategy configuration language

Use a restricted, declarative JSON-based domain-specific language (DSL).

Do not allow arbitrary Python code execution from strategy definitions.

Support typed expressions and composable conditions.

Initial indicator support:

- Simple moving average (SMA)
- Exponential moving average (EMA)
- Relative strength index (RSI)
- Price momentum / rate of change
- Rolling average volume
- Rolling price high and low

Initial condition support:

- Greater than
- Less than
- Greater than or equal
- Less than or equal
- Equal
- Crosses above
- Crosses below
- Logical AND
- Logical OR
- Logical NOT

Initial strategy actions:

- Buy
- Sell
- Hold

Initial risk and position rules:

- Fixed percentage of available portfolio equity
- Fixed target notional
- Maximum allocation per asset
- Stop-loss percentage
- Take-profit percentage
- Maximum concurrent positions

All indicator periods, signal thresholds, exits, and sizing rules must be editable through the application.

## 6.4 Example strategy

A strategy named "Momentum Breakout" might define:

- Market universe: inherited from backtest profile
- Indicator: 20-day SMA
- Entry: price crosses above SMA
- Additional condition: current volume exceeds 1.5 times the trailing 20-day average
- Exit: price crosses below SMA
- Stop loss: 3%
- Take profit: 6%
- Position size: 10% of account equity
- Maximum concurrent positions: 5

Codex should define a formal Pydantic strategy schema rather than depending on informal text descriptions.

The interpreter should recursively evaluate validated expression trees.

Every supported operator and indicator requires automated tests.

## 6.5 Strategy editor UI

Provide both:

**Visual editor**

Users can create and modify common strategy rules through forms, selectors, and configurable parameters.

**Advanced JSON editor**

Users can inspect and edit the structured strategy definition directly.

Both must use the same backend validation.

Changes made through either editor should produce equivalent strategy definitions.

Show validation errors near the affected rule when possible.

Unknown operators or malformed expressions must be rejected explicitly.

---

# 7. Shared Backtest Profiles

This is a critical requirement.

Strategies must operate under common, independently configurable financial conditions.

## 7.1 Initial default profile

Name: `US Equities Standard`

Settings:

- Starting capital: SGD 10,000
- Account currency: SGD
- Market: US equities and ETFs
- Start date: January 1, 2019
- End date: December 31, 2022
- Candle timeframe: Daily
- Fixed transaction fee: SGD 2.50 per executed order
- Percentage commission: 0% initially
- Slippage: 0.05% per execution
- Additional bid-ask spread assumption: 0% initially
- FX conversion markup: 0% initially
- Fractional share trading: Disabled
- Short selling: Disabled
- Leverage: 1.0x
- Cash interest: 0%
- Benchmark: SPY buy-and-hold
- No automatic cash top-ups

These are default assumptions, not claims about actual broker pricing.

## 7.2 Editable parameters

The UI must support editing:

### Capital and currencies

- Starting capital
- Base account currency
- Historical FX conversion policy

### Simulation period

- Start date
- End date
- Market calendar
- Candle timeframe

### Execution costs

- Fixed commission per executed order
- Percentage commission
- Slippage
- Optional spread assumption
- FX conversion markup

### Trading constraints

- Allow or disallow fractional shares
- Maximum number of orders per simulated trading day
- Maximum portfolio exposure
- Minimum order notional
- Optional minimum holding period
- Maximum concurrent positions

### Benchmark

- Benchmark instrument
- Benchmark comparison settings

## 7.3 Fee semantics

For the default fee:

- One completed buy order costs SGD 2.50.
- One completed sell order costs SGD 2.50.
- A buy followed by a sell costs SGD 5.00 in fixed commissions.
- Fees are deducted from simulated cash.
- Unfilled or rejected orders do not incur execution commissions.
- The initial MVP may use full fills only, provided this assumption is clearly documented.

Ensure the simulation does not allow orders that exceed available cash after accounting for fees and execution costs.

Fees should not be the only protection against excessive trading.

Also implement configurable order-frequency limits and duplicate-order prevention.

## 7.4 Shared comparison settings

When comparing multiple strategies:

- Every strategy starts with the same capital.
- Every strategy uses the same account currency.
- Every strategy uses the same date range.
- Every strategy uses the same market dataset snapshot.
- Every strategy uses the same execution-cost assumptions.
- Every strategy uses the same permitted trading universe.
- Every strategy uses the same benchmark methodology.

Each strategy has an independent virtual portfolio.

Do not allow strategies to share simulated cash or positions unless a future portfolio-combination feature explicitly requires it.

## 7.5 Profile versioning

Backtest profiles can be edited, but every run must retain an immutable snapshot of the actual settings used.

Changing the default transaction fee from SGD 2.50 to SGD 5.00 must never change an existing backtest result.

---

# 8. Historical Market Data

## 8.1 Requirements

Support historical daily US equities and ETF data.

Required OHLCV fields:

- Symbol
- Session date
- Open
- High
- Low
- Close
- Volume

Also store:

- Data provider
- Dataset version
- Exchange
- Currency
- Source timestamp
- Historical availability timestamp
- Ingestion timestamp
- Data adjustment policy
- Data-quality indicators

All timestamps should be timezone-aware.

Store absolute timestamps in UTC where appropriate and use the US exchange's timezone/calendar for market-session calculations.

## 8.2 Data providers

Implement a provider interface.

Potential implementations include:

- Alpaca historical market data
- CSV historical data import
- Other supported providers added later

For MVP:

1. Implement a robust CSV import mechanism.
2. Implement at least one usable API-based historical market-data integration where available.
3. Use deterministic synthetic fixture data for automated tests and a clearly marked demo dataset.
4. Never silently use demo data in a real historical backtest.

Verify the actual capabilities, terms, rate limits, historical coverage, and price-adjustment conventions of the chosen API before implementing its adapter.

Do not rely on brittle website scraping when an official data API is available.

Do not require paid subscriptions for the initial application.

If historical data is unavailable, the application should show a clear error rather than silently fabricating it.

## 8.3 Data storage

Use PostgreSQL for:

- Dataset metadata
- Supported symbols
- Historical daily candles
- FX rates
- Corporate actions
- Dataset revisions

Use appropriate indexes and uniqueness constraints.

For daily data and a limited asset universe, PostgreSQL is sufficient.

Keep the data-access layer abstract enough to support Parquet/DuckDB later for much larger datasets.

Avoid introducing time-series infrastructure prematurely.

## 8.4 Data quality

Validate imported data for:

- Duplicate candles
- Invalid timestamps
- Negative prices
- Nonpositive prices where inappropriate
- High lower than low
- Prices outside high/low bounds
- Invalid volume
- Missing sessions
- Unexpected gaps
- Duplicate symbols within one session

Trading holidays and weekends must not be treated as missing market data.

Do not automatically forward-fill missing tradeable market prices without a clearly defined policy.

## 8.5 Corporate actions

Stock splits and dividends must be handled explicitly.

The engine must not interpret stock-split price discontinuities as real investment losses.

Document whether returns are:

- Price-only returns
- Total returns including dividends

Use raw historical prices with point-in-time corporate-action handling, or another demonstrably look-ahead-safe method.

Do not apply future corporate-action knowledge to decisions made before the relevant event.

At minimum:

- Support split adjustments to existing portfolio positions.
- Preserve the correctness of position quantities and cost basis.
- Handle dividends when trustworthy historical corporate-action data is available.
- Show an explicit warning when total-return accounting is unavailable.

Do not claim dividend-adjusted total returns when only raw price data is present.

Stock universes should eventually support historical constituents and delisted securities to avoid survivorship bias. For MVP, clearly disclose limitations when testing a manually selected list of current symbols.

---

# 9. Historical FX and SGD Portfolio Accounting

The simulated account starts with SGD, while US equity prices are quoted in USD.

Do not use today's currency exchange rate for historical trades.

## 9.1 FX data

Support historical USD/SGD rates.

Each rate must carry a timestamp at which it was available.

Use only rates available at or before the simulated transaction time.

Do not backfill from future exchange rates.

When the selected FX series lacks sufficient historical coverage, reject the run or explicitly flag it as incomplete.

The data layer should distinguish the date represented by a published FX rate from the time at which the rate was actually available.

## 9.2 Initial accounting model

For the MVP, use:

- SGD cash balance
- USD-denominated securities
- Implicit SGD/USD conversion at simulated execution time
- Configurable FX conversion cost, defaulting to zero
- Historical FX-based portfolio valuation

Define and document the exact conversion direction.

When purchasing US shares:

1. Determine the simulated USD execution price.
2. Convert the total notional to SGD using the historically available FX rate.
3. Add transaction fees and FX costs.
4. Deduct the total SGD amount from cash.
5. Add the acquired securities to the portfolio.

When selling:

1. Calculate USD proceeds.
2. Convert proceeds to SGD using historically available FX.
3. Deduct fees.
4. Add net proceeds to SGD cash.
5. Update the position and realized P&L.

Portfolio equity:

`SGD cash + SGD value of open securities + accrued receivables, if applicable`

Use the latest permissible market and FX data at each valuation timestamp.

Use Decimal or another deliberate precision strategy for monetary calculations. Do not rely on unrestricted floating-point arithmetic for cash ledger correctness.

## 9.3 Constraints

- Cash must never become negative when borrowing is disabled.
- No automatic capital injection.
- Position sizes must respect available funds.
- Fractional-share trading must follow the selected profile setting.
- Commission and FX costs must be included before affordability checks.

---

# 10. Sequential, Point-in-Time Backtesting

This is the most important requirement in the entire project.

## 10.1 Fundamental invariant

At any simulated time T:

**A strategy may use only information that was available at or before T.**

All historical data access must respect this invariant.

The enforcement must be architectural, not merely a convention followed by individual strategies.

## 10.2 Example

Suppose the backtest period is January 2019 through December 2022.

When the simulated clock reaches June 15, 2020:

- The strategy may access historical prices available through June 15.
- It may calculate indicators using preceding observations.
- It may inspect its own prior trades and portfolio state.
- It cannot read June 16 prices.
- It cannot read December 2022 prices.
- It cannot use later earnings announcements.
- It cannot access future model training labels.
- It cannot know whether its current trade will eventually be profitable.

This restriction applies throughout the simulation.

## 10.3 Backtesting loop

Implement an event-driven simulation.

Conceptual sequence:

1. Initialize the virtual portfolio.
2. Load required historical data through a controlled data-access interface.
3. Set the simulation clock to the first valid session.
4. Process previously submitted orders that are eligible for execution.
5. Process market events and applicable corporate actions.
6. Update relevant portfolio state.
7. Make newly available completed market observations accessible.
8. Evaluate strategy conditions.
9. Generate orders for future execution.
10. Record signals, decisions, orders, fills, and portfolio valuations.
11. Advance the simulation clock.
12. Repeat until the specified end date.
13. Calculate final performance metrics.

The precise intraday ordering of execution, corporate actions, and valuation events must be formally documented and tested.

## 10.4 Execution timing

For daily-candle MVP:

- A completed daily candle becomes available only after that trading session closes.
- Strategy evaluation occurs after that candle becomes available.
- A market order generated from that candle cannot fill at the same day's opening price.
- The default execution point is the next eligible market session's opening.
- A buy executes at opening price plus the configured adverse execution costs.
- A sell executes at opening price minus the configured adverse execution costs.

Do not use the future candle's high or low to decide whether to place an order.

Protective orders such as stop losses and take profits require separately documented execution rules.

If daily OHLC data indicates that both a stop loss and take profit might have executed within the same candle, the engine must use a conservative, deterministic rule rather than inventing the unknown sequence of intraday prices.

Gaps through stop levels must be handled realistically.

No strategy should access a completed session's high/low until those observations would historically have become available, except that the execution simulator may use that information to determine fills of orders already active during that session.

## 10.5 Historical warm-up

Indicators may require observations preceding the requested test period.

For example, a 200-day moving average requires historical observations before the first date on which it can be evaluated.

Support a warm-up period.

Warm-up data must not be used to generate trades before the configured backtest start.

If there is insufficient warm-up data, the system must either:

- Delay eligible strategy trading until sufficient history exists, or
- Reject the configuration with an informative message.

Do not silently calculate an incorrect indicator using insufficient data.

## 10.6 Protected data access

Strategies must not receive unrestricted access to the entire historical dataset.

Implement a controlled strategy data view such as:

- Current simulation timestamp
- Permitted historical candle window
- Permitted indicator values
- Current portfolio state
- Relevant historical execution records

Future observations must not be accessible through this interface.

Indicator calculations must be causally correct.

Avoid centered rolling windows, unshifted future targets, and other look-ahead mechanisms.

## 10.7 Market calendar

Use an appropriate US exchange calendar.

Handle:

- Weekends
- Trading holidays
- Early market closes
- Daylight saving time
- Missing trading sessions
- Delisted or suspended securities where data supports them

Do not simulate executions on non-trading days.

## 10.8 Historical methodology limitations

Even with chronological simulation, a strategy designed today may incorporate knowledge of historical market events.

Therefore, distinguish:

- In-sample strategy research
- Out-of-sample validation
- Walk-forward testing
- Future live paper testing

The MVP should make it easy to designate a historical holdout period.

Do not describe repeatedly optimized historical performance as unbiased out-of-sample evidence.

---

# 11. Simulated Order and Portfolio Engine

The simulation engine should be separate from the strategy engine.

A strategy generates proposed actions.

The execution engine determines whether and how those actions can be executed.

## 11.1 Order model

Support:

- Buy
- Sell
- Market order
- Protective stop-loss and take-profit rules

Keep the design extensible for future limit orders.

An order should record:

- Unique identifier
- Backtest run identifier
- Strategy version
- Symbol
- Side
- Quantity
- Submission time
- Earliest eligible execution time
- Execution status
- Requested order type
- Execution price
- Executed quantity
- Fees
- Rejection reason where applicable

## 11.2 Portfolio model

Maintain:

- Cash
- Positions
- Position quantities
- Cost basis
- Realized P&L
- Unrealized P&L
- Total equity
- Fees paid
- FX-related costs
- Exposure
- Order history
- Trade history

Use explicit ledger/accounting events to make portfolio changes auditable.

## 11.3 Safety constraints

Reject orders that violate:

- Available cash
- Position-sizing limits
- Maximum allocation
- Maximum concurrent positions
- Maximum order-frequency limits
- Market availability
- Allowed asset universe

Avoid accidental duplicate orders.

The simulation must not repeatedly buy the same intended position simply because a signal remains true across multiple candles.

Crossover rules must distinguish an actual crossing event from a condition remaining true.

## 11.4 End-of-backtest behavior

At the end of a simulation:

- Mark open positions to market.
- Include unrealized P&L in ending portfolio equity.
- Do not automatically liquidate all positions unless that behavior is explicitly configured.
- Preserve open positions and pending order state in the results.
- Do not invent liquidation commissions for trades that never occurred.

---

# 12. Strategy Backtesting and Experiment Management

## 12.1 Backtest creation

The UI must let users select:

- Strategy
- Published strategy version
- Backtest profile
- Date range
- Market dataset
- Benchmark
- Optional experiment group

The application should validate requirements before scheduling the job.

## 12.2 Multiple strategies

Support running multiple published strategy versions under one common backtest profile.

Each run has an independent simulated portfolio.

All runs must use the same financial assumptions for fair comparisons.

## 12.3 Run lifecycle

Use statuses such as:

- Queued
- Running
- Completed
- Failed
- Cancelled

Show progress based on processed market sessions or events.

Persist execution duration, error details, and completion timestamp.

## 12.4 Reproducibility

Every backtest must retain:

- Strategy version ID and configuration hash
- Backtest profile snapshot
- Dataset identifier and revision/hash
- Historical data coverage
- Date range
- Execution model version
- Backtesting engine version
- Indicator implementation version where relevant
- Random seed if any stochastic components exist
- Model artifact version if ML is added later
- Final results

A completed run must not silently change when source data is subsequently refreshed.

Dataset snapshots should be immutable or otherwise content-addressed so that the historical input can be reconstructed.

---

# 13. Performance Metrics

Calculate at least:

## Returns

- Starting equity
- Ending equity
- Absolute profit or loss
- Total percentage return
- Annualized return, where meaningful
- Daily portfolio returns
- Gross return before fees
- Net return after fees and costs

## Risk

- Maximum drawdown
- Drawdown duration
- Annualized volatility
- Sharpe ratio
- Market exposure

## Trading

- Number of executed orders
- Number of completed trades
- Winning trades
- Losing trades
- Win rate
- Average win
- Average loss
- Profit factor
- Average holding period
- Turnover
- Total commissions
- Total slippage impact
- Total FX costs

## Benchmark comparison

- Benchmark total return
- Strategy return minus benchmark return
- Relative equity performance

Use explicit, consistent formulas and document assumptions.

For example, the Sharpe ratio should use a documented daily-return and annualization convention, with a configurable risk-free rate or a clearly stated zero default.

Handle zero-volatility and no-trade cases without producing misleading metrics.

## Important distinction

Compare both:

1. Net ending portfolio value in SGD.
2. Risk-adjusted performance and drawdowns.

Do not automatically rank strategies based solely on total percentage return.

---

# 14. Frontend Application

Create a functional dashboard with the following pages.

## 14.1 Overview dashboard

Display:

- Number of strategies
- Published strategy versions
- Completed backtests
- Recent experiments
- Top-performing strategies
- Recently failed jobs

Provide shortcuts to create a strategy and run a backtest.

Do not display fabricated investment returns.

Use empty states until real simulations exist.

## 14.2 Strategy list

Display:

- Strategy name
- Description
- Latest published version
- Draft state
- Creation date
- Archive status

Actions:

- Create
- View
- Edit
- Clone
- Archive
- Backtest

## 14.3 Strategy editor

Create an interactive editor for supported strategy rules.

Include:

- Name and description
- Indicator selection
- Indicator parameters
- Entry conditions
- Exit conditions
- Position sizing
- Risk rules
- Configuration validation
- JSON preview
- Save draft
- Publish new version

Support viewing differences between versions.

## 14.4 Backtest profiles

Provide UI to:

- Create a profile
- Edit a profile
- Clone a profile
- Select starting capital
- Select transaction fee assumptions
- Configure execution and currency settings
- Select historical dates
- Select tradable symbols
- Select benchmark

Show the estimated cost configuration clearly.

## 14.5 Create backtest

Allow selection of one or more strategy versions.

Allow selection of an existing shared profile.

Show the historical coverage of the selected dataset.

Validate whether sufficient historical and FX data is available.

On submission, schedule background execution.

## 14.6 Backtest results

Display:

- Total return
- Ending equity
- Maximum drawdown
- Sharpe ratio
- Win rate
- Total trades
- Total transaction costs
- Equity curve
- Drawdown chart
- Portfolio exposure
- Trade history

Provide a filterable order and trade table.

Allow inspection of individual signals and the rule conditions that triggered them.

## 14.7 Strategy comparison

Allow users to select multiple completed backtest runs.

Display their cumulative equity curves on the same chart.

Show a sortable comparison table.

Clearly indicate when runs use different profiles, date ranges, or datasets.

Incompatible runs should not be presented as strictly comparable without warning.

## 14.8 LLM strategy assistant

Provide a natural-language interface for creating or modifying strategy drafts.

Show generated configuration changes for user review.

Never automatically publish an LLM-generated strategy.

---

# 15. LLM Integration

The MVP must support LLM-assisted strategy authoring.

## 15.1 Primary capabilities

The user should be able to ask:

"Create a momentum strategy using a 20-day moving average."

Or:

"Modify this strategy so it only enters positions when RSI is below 65."

Or:

"Create a new version with a stricter stop loss and a volume filter."

The application should:

1. Send the user's request and supported strategy schema to the LLM.
2. Receive structured strategy configuration output.
3. Validate the configuration.
4. Display a preview of proposed changes.
5. Allow the user to accept or reject them.
6. Save accepted changes into an editable draft.
7. Require explicit publication before the version becomes immutable and backtestable.

## 15.2 Provider abstraction

Implement an LLM client interface so different compatible providers and models can be substituted later.

Keep credentials server-side.

Document configuration through `.env.example`.

Provide friendly errors when no API key is configured.

The remainder of the app must work without an LLM API key.

## 15.3 Safety and consistency

- Never execute arbitrary generated Python code.
- Reject unknown strategy operators.
- Reject unsupported indicators.
- Reject malformed parameter combinations.
- Validate generated configuration against strict backend schemas.
- Apply output-token and request-size limits.
- Record model and prompt versions for accepted generated changes.
- Prevent sensitive API keys from appearing in logs.
- Provide understandable validation errors.

## 15.4 Scope limitation

For MVP, the LLM acts as a **strategy authoring assistant**, not a historical trading oracle.

Do not use a modern LLM's unrestricted pretrained knowledge to simulate what a trading agent would have known in 2020.

Historical LLM news-trading experiments require additional point-in-time data and evaluation controls and belong to a later milestone.

---

# 16. Machine Learning: Future Architecture

Machine learning is a planned extension, not an MVP requirement.

However, avoid designing the system in a way that would require rewriting the simulation engine to support ML models.

## 16.1 Future ML strategies

Eventually support:

- Logistic regression
- Random forest
- Gradient-boosted trees
- Other compatible predictive models

Initial features might include:

- Historical returns
- Momentum
- Moving averages
- RSI
- Volatility
- Volume changes
- Relative performance against benchmarks

Predictions might represent:

- Probability of positive return over a specified horizon
- Expected return
- Predicted volatility
- Market-regime classification

## 16.2 Sequential training

ML models must respect the simulated clock.

For example, during a backtest in June 2020:

- Training data may include observations available before the simulated training cutoff.
- Training targets must already have matured.
- The model cannot use later realized prices or returns.
- Feature selection and preprocessing must use only permissible training data.
- Model retraining must occur on explicitly defined schedules.

Support expanding and rolling training windows in the future.

Training, validation, and testing periods must be separated appropriately.

## 16.3 Extension interfaces

Design future interfaces around:

- Feature provider
- Model trainer
- Model registry
- Prediction provider
- Retraining scheduler
- Model artifact references
- Prediction-driven strategy condition

Do not implement expensive ML infrastructure now.

Document the proposed interfaces and defer actual training workflows.

---

# 17. Proposed Database Entities

Use PostgreSQL and Alembic migrations.

Suggested tables:

## Strategy management

`strategies`

- ID
- Name
- Description
- Created at
- Updated at
- Archived at

`strategy_drafts`

- ID
- Strategy ID
- Draft configuration JSON
- Draft revision
- Updated at

`strategy_versions`

- ID
- Strategy ID
- Version identifier
- Parent version ID
- Configuration JSON
- Schema version
- Configuration hash
- Change summary
- Created at

## Simulation configuration

`backtest_profiles`

- ID
- Name
- Description
- Current configuration
- Created at
- Updated at

`backtest_runs`

- ID
- Strategy version ID
- Backtest profile snapshot
- Dataset snapshot reference
- Run configuration
- Start and end dates
- Status
- Progress
- Timestamps
- Engine version
- Error details

`experiment_groups`

- ID
- Name
- Description
- Created at

`experiment_group_runs`

- Experiment group ID
- Backtest run ID

## Market data

`market_datasets`

- ID
- Provider
- Dataset name
- Revision
- Content hash
- Coverage
- Adjustment policy
- Creation timestamp

`market_symbols`

- ID
- Symbol
- Exchange
- Currency
- Security metadata

`market_bars`

- Dataset ID
- Symbol reference
- Session date
- OHLCV
- Source timestamp
- Available-at timestamp

`fx_rates`

- Dataset ID
- Currency pair
- Rate
- Source timestamp
- Available-at timestamp

`corporate_actions`

- Dataset ID
- Symbol
- Action type
- Effective date
- Relevant financial values
- Available-at timestamp

## Execution and results

`backtest_orders`

`backtest_fills`

`backtest_positions`

`portfolio_snapshots`

`backtest_metrics`

`backtest_signal_logs`

`backtest_jobs`

Use appropriate primary keys, foreign keys, indexes, uniqueness constraints, and JSONB fields where useful.

Avoid duplicating large immutable payloads unnecessarily, but ensure reproducibility.

Create an entity relationship diagram in the documentation.

---

# 18. Backend API Design

Create REST endpoints with typed request and response schemas.

Suggested resources:

## Strategies

- `GET /api/strategies`
- `POST /api/strategies`
- `GET /api/strategies/{id}`
- `PATCH /api/strategies/{id}`
- `POST /api/strategies/{id}/archive`
- `POST /api/strategies/{id}/restore`

## Versions

- `GET /api/strategies/{id}/versions`
- `GET /api/strategy-versions/{id}`
- `POST /api/strategies/{id}/publish`
- `POST /api/strategy-versions/{id}/clone`
- `POST /api/strategy-definitions/validate`

## Backtest profiles

- `GET /api/backtest-profiles`
- `POST /api/backtest-profiles`
- `GET /api/backtest-profiles/{id}`
- `PATCH /api/backtest-profiles/{id}`

## Backtests

- `POST /api/backtests`
- `GET /api/backtests`
- `GET /api/backtests/{id}`
- `GET /api/backtests/{id}/results`
- `GET /api/backtests/{id}/trades`
- `GET /api/backtests/{id}/equity`
- `POST /api/backtests/{id}/cancel`

## Experiments

- `POST /api/experiments`
- `GET /api/experiments`
- `GET /api/experiments/{id}`
- `GET /api/experiments/{id}/comparison`

## Market data

- `GET /api/market-data/datasets`
- `GET /api/market-data/symbols`
- `GET /api/market-data/coverage`
- `POST /api/market-data/import`

## LLM

- `POST /api/llm/generate-strategy`
- `POST /api/llm/modify-strategy`
- `POST /api/llm/explain-strategy`

These are suggestions; refine route naming where beneficial.

Use FastAPI's generated OpenAPI schema.

Ensure that API errors are structured and frontend-friendly.

---

# 19. Automated Testing

Testing is especially important because financial simulations can appear correct while producing invalid results.

## 19.1 Unit tests

Test:

- Strategy schema validation
- Indicator calculations
- Entry conditions
- Exit conditions
- Crossovers
- Position sizing
- Commission calculations
- Slippage calculations
- FX conversions
- Cash accounting
- Position valuation
- Realized P&L
- Unrealized P&L
- Drawdown calculations
- Performance metrics

## 19.2 Look-ahead prevention tests

Create explicit tests proving that strategies cannot access future information.

Examples:

### Test A: Future observation blocking

At a simulated timestamp in June 2020, request a price from July 2020.

The data-access layer must reject the request or exclude the observation.

### Test B: Future mutation invariance

Run a strategy through June 2020.

Then modify all market data after June 2020 and rerun.

Every strategy signal and eligible execution before the cutoff must remain identical.

### Test C: Next-open execution

A strategy generates a buy signal after Monday's close.

It must not purchase at Monday's opening price.

The first possible fill should occur at the next eligible session's opening.

### Test D: Indicator warm-up

A 20-day SMA must not be evaluated as a valid 20-day SMA using only five observations.

### Test E: Missing data

Missing market data must not be replaced with future observations.

### Test F: FX availability

An exchange rate published after an execution time must not be used for that execution.

### Test G: Unmatured ML targets

The future ML training interface must reject labels whose return horizons extend past the simulated training cutoff.

## 19.3 Financial accounting tests

Verify:

- Buying reduces available cash.
- Selling increases available cash.
- Fees are deducted correctly.
- A complete buy/sell round trip incurs two order commissions.
- Insufficient funds result in order rejection.
- Share quantities and cost basis remain consistent.
- Portfolio equity equals cash plus permissible marked position values.
- Historical FX changes affect SGD valuations correctly.
- Stock splits do not artificially generate profits or losses.
- A strategy with no trades produces valid metrics and a flat cash equity curve.

## 19.4 Reproducibility tests

Running the same strategy version against the same dataset snapshot and profile with the same engine version must produce identical results.

Changing a published strategy must not be possible through the API.

Changing a profile must not alter historical completed runs.

## 19.5 Integration tests

Test:

- Create strategy
- Save draft
- Publish version
- Create backtest profile
- Import historical data
- Start backtest
- Process job
- Persist results
- Retrieve results through API
- Compare strategy performance

Include at least one automated end-to-end test using deterministic synthetic market data.

## 19.6 Frontend tests

Test important UI workflows such as:

- Creating strategies
- Editing rules
- Validation failures
- Publishing versions
- Creating backtest profiles
- Running simulations
- Displaying results

Use appropriate frontend testing tools.

---

# 20. Security and Operational Requirements

Although this is a personal application, maintain sensible security boundaries.

## Credentials

- Keep API keys server-side.
- Use environment variables or protected configuration.
- Never commit `.env` files.
- Never log API keys.

## API security

- Validate all inputs.
- Apply appropriate request and resource-size limits.
- Restrict CORS to configured frontend origins.
- Avoid arbitrary code execution.
- Prevent path traversal in file imports.
- Sanitize or encode user-supplied display content.
- Do not expose PostgreSQL publicly by default.

The MVP may operate without a login system on localhost or behind a trusted access layer such as Tailscale.

If deployed beyond localhost, document how to restrict access and require suitable authentication at the network or reverse-proxy layer.

## Background workers

- Limit concurrent backtests.
- Set configurable resource limits.
- Allow cancelling excessive workloads.
- Prevent uncontrolled job spawning.
- Report unexpected failures.
- Do not leave database transactions open unnecessarily.

## Logging

Use structured logging where practical.

Log:

- Job starts and completions
- Job failures
- Data ingestion results
- Strategy validation failures
- Backtest execution summaries

Avoid overly verbose per-candle logs unless specifically enabled.

Detailed strategy signal records should be available for debugging without overwhelming operational logs.

---

# 21. Development and Deployment Experience

The project should be straightforward to run locally.

## Development

Provide instructions for:

1. Cloning the repository.
2. Creating `.env` from `.env.example`.
3. Starting required services.
4. Running database migrations.
5. Starting frontend and backend.
6. Importing historical data.
7. Creating an example strategy.
8. Running a backtest.
9. Viewing results.
10. Running automated tests.

## Docker

Provide a working Docker Compose configuration containing:

- PostgreSQL
- FastAPI backend
- Background worker
- React frontend

Use persistent volumes where required.

Include health checks and reasonable service dependencies.

Do not hardcode passwords or credentials.

Support overriding the database connection so the app can eventually use an existing homelab PostgreSQL instance.

## README

The README should provide a concise project overview, setup commands, architecture summary, development workflow, and feature status.

## AGENTS.md

Create repository instructions for future Codex sessions.

Include these non-negotiable requirements:

- Maintain point-in-time correctness.
- Never access future market information.
- Preserve immutable strategy versions.
- Keep strategies declarative.
- Keep backtest profiles independent from strategies.
- Maintain realistic accounting.
- Write tests for changes to simulation behavior.
- Never silently fabricate historical financial results.
- Keep live brokerage execution outside MVP.
- Maintain reproducible backtests.
- Avoid unnecessary infrastructure.

---

# 22. Development Milestones

Implement the project in the following sequence.

## Milestone 1 — Foundation and Architecture

Deliver:

- Repository structure
- Docker Compose
- FastAPI skeleton
- React frontend skeleton
- PostgreSQL connection
- Alembic setup
- Configuration management
- Initial database migrations
- Architecture documentation
- AGENTS.md
- README

Acceptance criteria:

- Frontend starts.
- Backend starts.
- Database connection works.
- Health check succeeds.
- Migrations run successfully.
- Basic tests pass.

## Milestone 2 — Market Data and Simulation Clock

Deliver:

- Historical market-data schema
- CSV importer
- Real historical-data provider adapter
- Historical FX-data support
- Dataset metadata and revision handling
- Historical data validation
- Market calendar integration
- Point-in-time data-access interface
- Deterministic simulation clock

Acceptance criteria:

- Historical data can be imported and queried.
- Coverage can be inspected.
- Historical FX data can be stored.
- Future market observations cannot be accessed from an earlier simulation time.
- Automated point-in-time tests pass.

## Milestone 3 — Core Backtesting Engine

Deliver:

- Basic buy-and-hold strategy
- Basic moving-average crossover strategy
- Portfolio simulation
- Order execution
- Commission accounting
- Slippage model
- SGD portfolio valuation
- Trade history
- Daily equity history
- Core performance metrics

Acceptance criteria:

- A complete historical backtest can execute.
- Results are deterministic.
- Fees are correctly deducted.
- Insufficient-cash orders are rejected.
- No future prices influence earlier decisions.
- At least one complete integration test passes.

Initially, the strategies may be built-in fixtures to establish engine correctness.

## Milestone 4 — Strategy CRUD and Versioning

Deliver:

- Declarative strategy schema
- Strategy interpreter
- CRUD API
- Drafts
- Immutable published versions
- Strategy cloning
- Strategy list UI
- Strategy editor UI
- Version history

Acceptance criteria:

- User can create a strategy from the app.
- User can change its rules without code edits.
- User can publish a new version.
- Older versions remain unchanged.
- Different versions can be backtested independently.

## Milestone 5 — Backtest Profiles and Experiment Management

Deliver:

- Reusable backtest profiles
- Starting capital configuration
- Transaction fees
- Execution-cost parameters
- Trading constraints
- Multiple strategy backtests
- Experiment groups
- Background job execution
- Progress and failure handling

Acceptance criteria:

- User can create a profile with SGD 10,000 and SGD 2.50 fees.
- User can run multiple strategies with that shared profile.
- Each has an independent portfolio.
- Results remain reproducible if the profile is edited later.
- Completed and failed jobs are persisted correctly.

## Milestone 6 — Dashboard and Performance Comparison

Deliver:

- Overview dashboard
- Backtest creation form
- Backtest details page
- Equity curve charts
- Drawdown charts
- Performance metrics
- Trade history
- Strategy comparison
- Buy-and-hold benchmark

Acceptance criteria:

- User can run a backtest from the UI.
- Results persist after page refresh.
- User can compare strategies visually.
- Gross and net performance are distinguishable.
- Different dataset/profile assumptions are clearly disclosed.

## Milestone 7 — LLM-Assisted Strategy Editor

Deliver:

- Configurable LLM API integration
- Natural-language strategy generation
- Natural-language modification of drafts
- Structured configuration validation
- Proposed-change preview
- Human approval workflow
- Prompt and model metadata

Acceptance criteria:

- User can describe a strategy in natural language.
- LLM output is validated against the supported schema.
- User can review and save the result.
- User can publish and backtest the new strategy version.
- The app remains functional without an LLM API key.
- LLM output cannot execute arbitrary code.

## Milestone 8 — Hardening and MVP Completion

Deliver:

- Additional integration tests
- Data-quality checks
- Reproducibility checks
- Financial accounting edge-case tests
- Error handling improvements
- Documentation updates
- Docker deployment verification
- UI cleanup
- Known limitations document

Acceptance criteria:

- The application starts from a clean checkout.
- Database migrations succeed.
- Automated tests pass.
- User can import historical data.
- User can create and publish strategies.
- User can configure financial assumptions.
- User can run sequential backtests.
- User can compare multiple strategies.
- User can inspect trades, fees, returns, and drawdowns.
- No real brokerage connection is required.

---

# 23. Required Demonstration Scenario

Before declaring the MVP complete, demonstrate the following workflow.

### Step 1

Create a backtest profile:

- Name: Standard SGD Portfolio
- Starting capital: SGD 10,000
- Transaction fee: SGD 2.50 per executed order
- Slippage: 0.05%
- Market: US equities
- Backtest period: 2019–2022
- No leverage
- Long-only

### Step 2

Load suitable historical US equity and ETF price data, plus USD/SGD exchange-rate data with sufficient coverage.

If real data credentials or coverage are unavailable, demonstrate using a visibly labeled synthetic dataset, and explicitly state that the real-data scenario remains unverified.

### Step 3

Create three strategies:

1. Buy and hold SPY.
2. 20-day / 50-day moving-average crossover.
3. RSI-based mean reversion.

### Step 4

Run each strategy over the same period with identical financial assumptions.

### Step 5

Display:

- Final portfolio value
- Total returns
- Maximum drawdown
- Sharpe ratio
- Number of trades
- Total fees
- Equity curves
- Individual executed orders

### Step 6

Create a new version of the moving-average strategy with different indicator periods.

Run a new backtest.

### Step 7

Compare the original and modified versions.

Confirm that the original results remain unchanged.

### Step 8

Demonstrate that changing later historical prices cannot alter earlier simulated trading decisions.

This final validation is mandatory.

---

# 24. Future Roadmap — Do Not Implement Yet

Document future expansion possibilities.

## Phase 2 — Machine Learning

- Feature engineering
- Model training
- Model registry
- Model versioning
- Walk-forward retraining
- Model-based trading signals
- Out-of-sample evaluation
- Hyperparameter experiments
- Controlled model comparisons

## Phase 3 — Intraday Backtesting

- 5-minute candles
- 1-minute candles
- Intraday order events
- Higher-volume time-series storage
- More sophisticated execution modelling

## Phase 4 — Live Paper Trading

- Live US market-data ingestion
- Scheduled strategy execution
- Independent paper portfolios
- Alpaca or another paper broker adapter
- Trade decisions during real market hours
- Morning performance reports in Singapore time
- Alerts and monitoring

## Phase 5 — Strategy Ensembles

- Multiple strategy signal aggregation
- Portfolio allocation across strategies
- Correlation analysis
- Market-regime detection
- Ensemble optimization
- Walk-forward allocation evaluation

## Phase 6 — Real Brokerage Integration

Potential integrations:

- Interactive Brokers
- Alpaca, subject to account eligibility

This phase must be explicitly authorized separately.

No live trading implementation is permitted as part of the current MVP.

---

# 25. Quality Standards and Definition of Done

A feature is complete only when:

1. The implementation exists.
2. Its API is validated.
3. Its database changes are migrated.
4. Its business logic is tested.
5. Its UI workflow works where applicable.
6. Errors are handled sensibly.
7. Relevant documentation is updated.
8. Existing functionality remains operational.

The application must never knowingly present misleading historical returns or pretend that missing financial data was successfully processed.

Financial correctness, reproducibility, and point-in-time integrity take priority over performance optimization and UI polish.

---

# 26. Instructions for Starting Work

Begin by:

1. Inspecting the current repository and development environment.
2. Identifying any genuinely blocking unknowns.
3. Creating the proposed architecture and implementation roadmap under `docs/`.
4. Defining the data contracts for strategy configurations, backtest profiles, historical market data, and simulated orders.
5. Documenting the chronological simulation event ordering.
6. Creating `AGENTS.md`.
7. Scaffolding the application.
8. Implementing Milestone 1.
9. Continuing through subsequent milestones in small, testable increments.

Before making a major architectural deviation, document why it is necessary and what tradeoff it introduces.

When possible, make logical Git commits after completing tested milestones, without overwriting unrelated work.

Do not merely generate pseudocode or placeholder APIs and describe the project as complete.

Do not build fake dashboards containing hardcoded profitability numbers.

Use a clearly labeled demonstration dataset when testing with synthetic prices.

At the end of each milestone, provide:

- What was implemented
- Important files created or changed
- Tests executed and their results
- Outstanding limitations
- Architectural decisions made
- Next implementation milestone

**Final objective:** Deliver a self-hosted web application in which I can create trading strategies through the UI, version them, configure shared financial assumptions, backtest them chronologically without access to future information, and objectively compare their historical performance before eventually introducing machine learning and live paper trading.