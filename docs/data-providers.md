# Data providers and contracts

## CSV

Upload UTF-8 CSV content, not filesystem paths. Paths cannot escape the repository/server. All records are validated before a transaction commits. Duplicate candles, malformed rows/headers, naive timestamps, invalid OHLC, nonpositive prices, negative volumes, non-session dates and premature daily availability are rejected. Coverage/gaps are recorded, never filled. Maxima: 100,000 candles, 30,000 FX observations, 10,000 actions, 25 MB request body (configurable server limits).

Daily columns: `symbol,session_date,open,high,low,close,volume,source_timestamp,available_at`. Optional exchange (XNYS/XNAS), currency (USD) and JSON-import quality flags. Session dates are ISO dates. Timestamps include `Z` or an explicit UTC offset.

FX: `observed_at,available_at,rate`; optional pair must be `USD/SGD`. Rate is SGD per USD, not the inverse.

Actions: `symbol,session_date,available_at,kind,value,payment_date`. For splits, value is new shares / old share; leave payment_date blank. For dividends, session_date is ex-date, value is USD/share, and payment_date is required. Actions must be known by effective opening; unreliable late events are rejected rather than retroactively inserted. Same-day split is processed before a dividend entitlement. Non-trading payment dates settle on the next available session.

JSON import uses the complete `DatasetInput` contract and supports quality arrays. Export an immutable revision at `GET /api/market-data/datasets/{id}/export`, amend externally, and import a new revision. Existing runs keep their original hash.

## Alpaca read-only historical adapter

Verified against official documentation on 2026-11-04:

- [Historical bars](https://docs.alpaca.markets/us/reference/stockbars): paginated `/v2/stocks/bars`, `1Day`, `adjustment=raw`, `feed=iex`, `asof=-`. Every page token is followed; 50-page and row limits fail explicitly. 350 ms spacing between pages stays below the documented Basic request ceiling when this adapter runs alone. HTTP errors, including entitlement/rate-limit errors, are surfaced; no scraping or synthetic fallback exists.
- [Market-data access](https://docs.alpaca.markets/us/docs/about-market-data-api): Basic includes US stocks/ETFs, historical coverage since 2016 and 200 historical calls/minute. IEX is a limited feed, not consolidated market volume. This app does not require a paid subscription; account/data entitlement and actual per-symbol coverage still require a live credentialed check.
- [Redistribution restrictions](https://alpaca.markets/support/redistribute-alpaca-api) and [current agreements](https://alpaca.markets/disclosures) apply to imported data. Keep this deployment personal/private and follow the account's applicable data agreement; repository fixtures contain no redistributed vendor prices.

Keys are supplied only through backend environment variables. The adapter calls only `data.alpaca.markets`, never a brokerage execution endpoint. It does not invent FX or corporate actions. Provide FX/action CSV alongside the API import or export/re-import a combined revision. Use raw prices; future-adjusted dividends/splits are deliberately not requested. Publication availability is an explicit 20:15 New York time assumption; current revised API bars are not historical vintages. These caveats are persisted and shown in results.

No live credentials were available here. Provider pagination/error handling is tested with controlled HTTP responses; real entitlements and 2019–2022 coverage remain unverified.

Alpaca daily volume includes extended-hours trades while daily OHLC excludes those trade conditions, per the [official aggregation rules](https://docs.alpaca.markets/us/docs/market-data-faq). The adapter assumes publication after 20:00 ET plus 15 minutes and selects the 20:30 ET dataset decision clock. This avoids exposing final daily volume at 16:30 ET. OHLC is a first/last eligible feed print, not an official exchange auction price. The optional dataset decision_time policy is included in its hash when nondefault. CSV sources including extended-hours volume should select the same evening policy.
