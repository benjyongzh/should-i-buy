# Historical strategy capabilities — engine 2.0.0

Strategies remain validated declarative JSON. The LLM proposes an interpretation,
assumptions, required inputs and a configuration. The user reviews that proposal,
accepts it into the mutable draft, then separately publishes the next immutable
version. Unsupported requests produce blocked proposals. Schema validation and
run-specific coverage checks apply independently of the model's explanation.
Natural-language flexibility is bounded by these explicit engine capabilities;
new execution models or financial instruments still require engineering/review.

## Decisions, timing and sizing

- Profiles choose daily or regular-session 1/5/15/30/60-minute execution bars.
  Strategies choose daily-close, completed-bar, or available-event/bar decisions.
  A market order waits for a **strictly later** eligible interval open. A bar's
  closing observation cannot be used to buy at that bar's earlier open.
- Entry/exit windows use minutes after the actual XNYS open and before its close,
  including DST and early closes. For “buy from one hour after opening”, set
  `entry_window.start_minutes_after_open: 60`; select an intraday profile and
  matching reviewed intervals. This does not guarantee a fill at precisely 10:30.
- Daily, weekly, monthly and once schedules, additions, partial exits, fixed
  budgets, equity/cash fractions and target allocations remain available.
  Ordered `sizing_rules` use the first matching condition, with ordinary sizing
  as fallback. Fees, affordability and portfolio constraints always apply.
- Calendar operands include exchange-relative minutes, weekday, month/year,
  calendar day and trading-session number within the month. Portfolio operands
  include cash, equity, quantity, weight and holding sessions. Arithmetic,
  corporate-action windows and explicit daily/intraday market wrappers can be
  combined with existing SMA/EMA/RSI/MACD/stochastic/volume and external series.
- A profile's monthly contribution remains an independent account-currency
  assumption. Funding does not automatically cause investment.

## Historical symbol selection

`universe` filters/ranks within the profile's permitted symbols (maximum 50).
It supports include/exclude symbols and sectors, preferred sectors, declarative
eligibility, numeric ranking, top N and optional exits when ineligible. Historical
states have a stable instrument identity, effective clock and availability clock.
Today's sector or index constituents cannot replace historical states. Rankings
use only completed available observations; ties are deterministic.

Held securities remain valued and protected even when removed from entry
selection. Identity recycling, delisting or missing terminal valuation fails
explicitly: merger consideration, terminal settlements and cash-in-lieu are not
implemented. This is a curated-universe engine, not an automatic all-market
historical security master or index-constituent discovery service.

## News, analyst reports, macro releases and Congress disclosures

Event expressions select a frozen stream, categories/tags, scope, lookback,
actors, measure and access policy. Counts, latest values or sums can affect
entry, exit, selection/ranking and sizing. `public_only` is default; historical
retail subscription information requires explicit `any_licensed`. This prevents
private records, including private amendment clocks, from changing public-only
strategies. Public access is source metadata requiring evidence.

Each original event retains publication, actual version availability, source URL,
content hash and derivation. News text versions and analyst reports cannot be
backdated. Optional scores require their own availability clock. Later amendments
supersede earlier records only after the amendment becomes available. An empty
result means zero only within reviewed complete coverage of the requested
symbols, interval, access policy and declared categories; unknown coverage fails.

- **Company/global news:** article IDs, versions, text and source tags; optional
  deterministic keyword tags retain their exact rules. No retrospective LLM
  sentiment or knowledge of later outcomes is inserted into earlier decisions.
  Global geopolitical/oil events use a global stream; they do not become
  complete market news merely because company-tagged stories were downloaded.
- **Analysts:** individual firm/analyst changes, rating labels and original
  nominal USD targets. Use categories such as `analyst.upgrade` for label-based
  rules and `analyst_target_after` for numeric targets. Current consensus and
  future-adjusted target histories cannot stand in for original reports.
- **Economic releases:** actuals and reference period/release clocks; a surprise
  requires a consensus value demonstrably available before that release.
- **Congress:** reporter/chamber/filing/owner, transaction date/type, original
  public disclosure clock, amendment lineage and disclosed amount bounds.
  Rules become eligible at disclosure, never the earlier transaction date.
  `congress_amount_min/max` retain the range; no exact amount is inferred.

“Information a person could have had” means the chosen public/licensed sources
with evidenced timing. No feed establishes “all information available to humans”.
Modern model knowledge, current classifications and revised articles are not
historical observations.

## Source workflow and audit

1. In **Strategy sources**, prepare a bounded Alpaca intraday/news or optional
   Benzinga rating partition, or import JSON/CSV with source metadata. Templates
   are visibly synthetic and never become real observations automatically.
2. Inspect original rows and historical cutoff. Attest publication/version/access
   assumptions and complete declared coverage with a review note. Approval
   creates a new revision retaining its raw parent; it does not edit the parent.
3. Select reviewed revisions in New backtest, including warm-up/lookback
   coverage, and check data readiness. Exact source IDs/content hashes, profile,
   strategy, engine and input manifest are retained. Worker replay verifies them.
4. Inspect completed decisions, evaluated values, selected symbols, sizing rules,
   linked source evidence, fills and capital events. The timeline compares saved
   strategy/version results with same-profile buy-and-hold and modeled cash.
   Intraday mode uses retained valuation clocks only; old runs gain no invented
   intraday marks. Daily marks remain the basis of annualized statistics.

Market fills assume full execution at subsequent raw interval opens with modeled
costs; there is no order book, latency calibration, volume participation, per-stock
halt model or actual intraday executable FX. Missing real inputs are errors.
The bounded independent financial review is recorded in
[Milestone 3 review](milestone-3-review.md). Data/access requirements are in the
[input checklist](historical-input-checklist.md).
