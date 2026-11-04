# Point-in-time data boundary

The interpreter accepts only a materialized `DataView.history(symbol)` at the current simulation timestamp. The view filters availability timestamps on construction, and explicitly rejects requests through a future timestamp. The declarative interpreter has no reference to the dataset, provider, database, network or clock advancement mechanism.

Market data contracts distinguish exchange session date, source timestamp, historical availability timestamp and ingestion time. Completed bars earlier than the official close are invalid. FX has a separate observation timestamp and publication timestamp. Selection requires both <= the execution/valuation clock; observations older than the profile limit (default seven days) fail. There is no current-FX substitution, backward fill or synthetic fallback.

Imported gaps are enumerated against the XNYS calendar. Any missing trading session in the run's required universe/benchmark rejects scheduling and worker execution. Weekends and holidays are not gaps. Insufficient indicator warm-up delays eligibility; no shortened SMA/RSI is invented. Delayed observations remain hidden until their availability, then use the latest permissible mark.

Raw prices are immutable. Splits change quantities and reference prices at effective open. Historical indicator bars are adjusted only by split events effective by the current clock; future splits cannot rewrite earlier decisions. Dividends require trustworthy ex/payment dates. Complete dividends must be explicitly attested; otherwise the results are price-only with a visible warning.

An API source's current revised history is not a vintage database. Alpaca imports explicitly disclose assumed 20:15 New York time publication and revised histories. Temporal gating cannot prove the vendor never revised earlier prices. Strict historical research requires source-provided vintage timestamps/data, corporate-action coverage and historical constituents. See provider/limitations documents.

Tests cover future observation rejection, future-price/volume/FX mutation invariance, next-open fills, SMA warm-up, missing-session rejection, FX publication gating, unmatured ML labels, splits and reproducible replay. The 2019–2022 synthetic acceptance report independently verifies invariant signals, eligible fills and equity before 2020-06-30 after mutating all later data.

Future trainers must accept explicit label maturity timestamps and enforce <= training cutoff before preprocessing, feature selection or training. The included maturity guard is a boundary test, not an implemented ML training system. No modern LLM pretrained knowledge is used as a 2020 trading agent.
