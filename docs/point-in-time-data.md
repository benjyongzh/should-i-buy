# Point-in-time data boundary

## News, ratings, disclosures and intraday prefixes

Engine 2.0 revalidates isolated source models at the protected simulation boundary.
Intraday history requires interval completion, source timestamp and availability
at/before the clock. Historical states require both effective and availability
clocks. Event text/report revisions use their own availability, scores use an
additional score clock, and Congress trades use public disclosure time. Private
records cannot alter public-only clocks or amendment folding. Coverage/catalog
checks distinguish unknown history from a verified absence of events. Original
vendor vintages remain a source requirement, not a property an API key supplies.
See [capabilities](strategy-capabilities.md) and [input checklist](historical-input-checklist.md).

Engine 1.4 monthly contributions become spendable only at their scheduled open,
after splits/dividend accounting and before order execution. Orders retain their
prior decision-clock quantity. Funding-neutral performance uses actual opening
prices and opening-available FX before/after each flow, preserving overnight
returns without counting principal as profit. Strategy schedules filter completed
close decisions and never expose tomorrow's deposit or execution quote. See
[funding semantics](funding-and-trade-controls.md).

The interpreter accepts only a materialized `DataView.history(symbol)` at the current simulation timestamp. The view filters availability, source timestamps and the actual exchange-session completion time, including for historical `through` requests. Misdated availability cannot expose a future completed candle. Requests through a future timestamp are rejected. The simulator also revalidates dataset chronology at its entry boundary. The declarative interpreter has no reference to the dataset, provider, database, network or clock advancement mechanism.

Market data contracts distinguish exchange session date, source timestamp, historical availability timestamp and ingestion time. Completed bars earlier than the official close are invalid. FX has a separate observation timestamp and publication timestamp. Selection requires both <= the execution/valuation clock; observations older than the profile limit (default seven days) fail. There is no current-FX substitution, backward fill or synthetic fallback.

Engine 1.3.0 external signal inputs additionally require a retained, explicitly reviewed snapshot with known timezone-aware publication times. Only the latest eligible observation reaches a current/prior scalar `FeatureView`; the interpreter cannot inspect future source rows. Crossovers use the previous trading-session decision clock, including its separately effective/known split adjustments for price history. A late older release cannot overwrite a newer known observation. Missing/stale coverage rejects the run. Revision IDs, hashes and a manifest hash are frozen and worker-checked. Context approval cannot waive unknown publication times or supply accounting FX/actions. See `strategy-inputs.md` and the independent 1.3.0 review.

Imported gaps are enumerated against the XNYS calendar. Any missing trading session in the run's required universe/benchmark rejects scheduling and worker execution. Weekends and holidays are not gaps. Insufficient indicator warm-up delays eligibility; no shortened SMA/RSI is invented. Delayed observations remain hidden until their availability, then use the latest permissible mark.

Raw prices are immutable. Splits change quantities and reference prices at effective open. Historical indicator bars are adjusted only by split events effective by the current clock; future splits cannot rewrite earlier decisions. Dividends require trustworthy ex/payment dates. Complete dividends must be explicitly attested; otherwise the results are price-only with a visible warning.

An API source's current revised history is not a vintage database. Alpaca imports explicitly disclose assumed 20:15 New York time publication and revised histories. Temporal gating cannot prove the vendor never revised earlier prices. Strict historical research requires source-provided vintage timestamps/data, corporate-action coverage and historical constituents. See provider/limitations documents.

Tests cover future observation rejection, future-price/volume/FX mutation invariance, next-open fills, SMA warm-up, missing-session rejection, FX publication gating, unmatured ML labels, splits and reproducible replay. The 2019–2022 synthetic acceptance report independently verifies invariant signals, eligible fills and equity before 2020-06-30 after mutating all later data.

The mandatory Milestone 3 review adds finer intraday invariance: modifying a session's final volume cannot change that morning's fill; modifying one asset's later low cannot change another asset's earlier opening gap exit, including under a one-order daily limit. Opening events precede every range-based close event. See `milestone-3-review.md` for the failed baseline and independently verified corrections.

Future trainers must accept explicit label maturity timestamps and enforce <= training cutoff before preprocessing, feature selection or training. The included maturity guard is a boundary test, not an implemented ML training system. No modern LLM pretrained knowledge is used as a 2020 trading agent.
