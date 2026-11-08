# Data providers and contracts

## Full 2018–2025 earnings experiment — 2026-11-08

The [executed full-history report](full-history-earnings-experiment-2026-11-08.md)
verifies 64 issuer/SEC quarterly pairs and independently reconciles 128 GAAP facts.
A 192-event immutable child is reviewed only under the explicit next-session-close
research availability proxy; exact public delivery remains unverified. All 96 month
news queries complete: 35,854 news events and 1,262 literal analyst announcements
are imported as 16 yearly **unreviewed/incomplete** sources. One blank-headline row
is quarantined and 68 older publications are explicitly excluded from update windows.

A streamed LLM proposes the exact predeclared earnings-entry gate. Explicit draft
acceptance/publication, version transcript, journal conclusion and exact candidate
repeat pass. The outcome is mixed: SGD 29,819.54 baseline versus 23,302.66 candidate,
with maximum drawdown 32.19% versus 19.49%. All 2018–2025 periods are retained.
Independent reconstruction checks 8,044 marks, 8,044 decisions, 150 fills and 308
ledger entries. **339 backend/PostgreSQL and 62 frontend tests pass**, Ruff/build
pass. Engine 2.0.0 is unchanged. [Visual report](earnings-experiment.html).

The full-history load exposed an automatic API restart and source-catalog UI
failure in the existing deployment. A metadata-only SQL fix passes 339 backend
checks and 12 browser assertions in a separate read-only API, with all 230 summaries
identical and response time 2.44–2.53s instead of 25.23s. It is **not deployed** over
existing containers. All 58 identities, 11 prior runs and 212 source exports remain;
57 runtimes are unchanged and the API records one automatic restart. Exact cause
is unconfirmed. See the report before treating the running source UI as verified.

[Executed qualification follow-up](retail-source-qualification-2026-11-08.md):
45 snapshot shards and all retained House inventory IDs check out; the bounded
Congress sample retains unknown public clocks. Ninety-eight literal analyst
announcements are imported unreviewed, and two issuer/SEC earnings pairs are
normalized as staging evidence. No new key or broad coverage approval is implied.

[Free Congress dataset assessment](congress-dataset-assessment-2026-11-08.md):
pinned upstream code and actual manifest are reviewed. It is relevant staging
material, but its availability clock is filing-day end, not measured retail
publication. Synthetic checks reproduce timing, ambiguous cross-document merging
and later-contributor provenance. No broad dataset is imported or qualified.
Earnings will use issuer investor-relations releases plus original SEC exhibits;
free analyst work can start from explicit announcements in existing news access.
Public ratings sites are corroboration candidates, not verified free bulk history.

The [retail information pilot](retail-information-pilot-2026-11-08.md) now verifies
AAPL/MSFT news and original insider/earnings samples using existing access.
A qualified retail provider can supply information without direct Senate access.
Samples are retained in the source UI as unreviewed/incomplete; full 2018–2025
coverage, individual analyst changes and historical versions remain separate gates.
Quiver API access is paid and optional; no new key was needed for this pilot.

Latest: [permanent conversation/version history](conversation-history-verification-2026-11-07.md)
now preserves full eligible context and publication-time read-only transcripts.
[Congress qualification](congress-qualification-2026-11-07.md) has begun under
confirmed personal non-commercial use: original indexes/reports, three matching
archive replays and two raw observations are retained. Coverage remains incomplete;
no Congress source was approved for financial backtests.

Latest source-review follow-up: [AAPL/MSFT accounting and deployed SEC/BLS imports](company-intake-verification-2026-11-06.md)
are complete under their recorded research availability policies. The combined
AAPL/MSFT/SPY revision has 7,542 daily bars, 2,494 reference-FX observations and
121 actions; reviewed event streams contain 190 BLS and 145 SEC observations.
These were prepared/reviewed externally and imported through existing HTTP
contracts. The [requested-company onboarding coordinator](company-onboarding.md) now orchestrates
daily accounting and SEC filing evidence, with explicit review and no fixed ticker
allowlist. It is verified in isolation and not deployed to port 18080. [Real strategy acceptance](real-equity-acceptance-2026-11-06.md)
now demonstrates 13 fixed equity/event cases and their exact repeats under the
documented source timing and FX policies.

## Additional historical strategy sources — engine 2.0.0

**Strategy sources** prepares Alpaca raw intraday and company-news partitions and
optional Benzinga individual analyst ratings, with immutable raw retention and
explicit separate review. JSON/CSV contracts also cover historical security
states, global/economic events and Congress disclosures. No Congress scraper or
comprehensive original-vintage news archive is configured. Existing Alpaca/FRED/LLM
keys remain server-side; optional `BENZINGA_API_KEY` is only needed for that direct
ratings adapter. Files need no additional key. Current vendor records may be
revised and do not prove complete original historical coverage. See the
[exact source/key checklist](historical-input-checklist.md).

Latest2026-11-05 result: a reviewed combined SPY revision now contains2,514 raw SIP bars,2,494 initial-release FX values and40 issuer dividends. Three strategies completed2018–2025 and supplemental2019–2022, with exact repeats and independent financial reconciliation. [Acceptance evidence](real-spy-acceptance-2026-11-05.md) explains the corrected FX availability, original pre-US-open USD notices, US-date authority and bounded reference-FX/vintage assumptions. QQQ/SMH/XLE still require action reviews. Earlier diagnostic paragraphs below preserve their then-unreviewed state and do not describe the new SPY revision.

Earlier source additions: separate raw SPY/QQQ/SMH/XLE SIP revisions cover2016–2025, and nine immutable context series cover VIX, Treasury yields, Fed funds, CPI, unemployment, oil and reference FX. Those viewing-only imports remain separate from accounting datasets; a later explicit review can create strategy-eligible external snapshots with known publication times. See [continuous research](continuous-research.md) and [strategy inputs](strategy-inputs.md).

Current 2026-11-05 integration evidence: the Linux project re-imported all 1,259 SPY SIP bars successfully with the same content hash reported below. Live LLM generation/modification also passes. See [current verification](verification-linux-2026-11-05.md) for current IDs, credential requirements and remaining FX/action blockers; earlier Windows `.local` artifacts referenced below are absent in this checkout.

## CSV

Upload UTF-8 CSV content, not filesystem paths. Paths cannot escape the repository/server. All records are validated before a transaction commits. Duplicate candles, malformed rows/headers, naive timestamps, invalid OHLC, nonpositive prices, negative volumes, non-session dates and premature daily availability are rejected. Coverage/gaps are recorded, never filled. Maxima: 100,000 candles, 30,000 FX observations, 10,000 actions, 25 MB request body (configurable server limits).

Daily columns: `symbol,session_date,open,high,low,close,volume,source_timestamp,available_at`. Optional exchange (XNYS/XNAS), currency (USD) and JSON-import quality flags. Session dates are ISO dates. Timestamps include `Z` or an explicit UTC offset.

FX: `observed_at,available_at,rate`; optional pair must be `USD/SGD`. Rate is SGD per USD, not the inverse.

Actions: `symbol,session_date,available_at,kind,value,payment_date`. For splits, value is new shares / old share; leave payment_date blank. For dividends, session_date is ex-date, value is USD/share, and payment_date is required. Actions must be known by effective opening; unreliable late events are rejected rather than retroactively inserted. Same-day split is processed before a dividend entitlement. Non-trading payment dates settle on the next available session.

JSON import uses the complete `DatasetInput` contract and supports quality arrays. Export an immutable revision at `GET /api/market-data/datasets/{id}/export`, amend externally, and import a new revision. Existing runs keep their original hash.

## Alpaca read-only historical adapter

Verified against official documentation on 2026-11-04:

- [Historical bars](https://docs.alpaca.markets/us/reference/stockbars): paginated `/v2/stocks/bars`, `1Day`, `adjustment=raw`, explicit `feed=sip` or `iex`, `asof=-`. The UI defaults to SIP; legacy API requests omitting feed retain IEX. Feed identity is persisted in the revision. Every page token is followed; 50-page and row limits fail explicitly. 350 ms spacing between pages stays below the documented Basic request ceiling when this adapter runs alone. HTTP errors, including entitlement/rate-limit errors, are surfaced; no alternate feed, scraping or synthetic fallback exists.
- [Market-data access](https://docs.alpaca.markets/us/docs/about-market-data-api): Basic includes US stocks/ETFs, historical coverage since 2016 and 200 historical calls/minute. IEX is a limited feed, not consolidated market volume. SPY 2018–2022 historical SIP access has now passed with the supplied credentials; other accounts/symbols still require verification.
- The [official FAQ](https://docs.alpaca.markets/us/docs/market-data-faq) distinguishes **historical SIP** from latest/realtime SIP: historical queries whose `end` is at least 15 minutes old can request SIP without a subscription. This historical request now succeeded here; no paid subscription was purchased or changed. SIP consolidates market venues, including Nasdaq trading; IEX captures one venue. Neither feed selection certifies historical symbol membership, official auction fills or original publication vintages.
- [Redistribution restrictions](https://alpaca.markets/support/redistribute-alpaca-api) and [current agreements](https://alpaca.markets/disclosures) apply to imported data. Keep this deployment personal/private and follow the account's applicable data agreement; repository fixtures contain no redistributed vendor prices.

Keys are supplied only through backend environment variables. The adapter calls only `data.alpaca.markets`, never a brokerage execution endpoint. It does not invent FX or corporate actions. Provide FX/action CSV alongside the API import or export/re-import a combined revision. Use raw prices; future-adjusted dividends/splits are deliberately not requested. Publication availability is an explicit 20:15 New York time assumption; current revised API bars are not historical vintages. These caveats are persisted and shown in results.

Credentialed verification on 2026-11-04: paper account `GET https://paper-api.alpaca.markets/v2/account` returned 200. Paper-account operations use that paper base; historical data uses `https://data.alpaca.markets/v2` for both paper and live-account credentials, per [Alpaca authentication](https://docs.alpaca.markets/us/docs/authentication). The application itself has no brokerage execution endpoint. A separate read-only credential probe does not add a trading feature.

The actual UI import API returned 201 for 1,259 real raw SPY SIP daily bars, 2018-01-02–2022-12-30, with no missing sessions. Dataset `f9d78623-c8c5-4941-9489-7a1370638476` has hash `5fd1c37ccd280c6f83e4904cb17853eb8c4a07dd6f8a6c8fe639c6f77ee3b739`. It remains unreviewed and has zero FX/actions. Scheduling correctly returned 422 and created no job. This verifies the API used by the form, not an interactive browser import. Raw responses, normalized data, export and the private verification report are retained under ignored `.local`; see the deployment runbook. Real backtest acceptance remains blocked by FX/action review.

Alpaca daily volume includes extended-hours trades while daily OHLC excludes those trade conditions, per the [official aggregation rules](https://docs.alpaca.markets/us/docs/market-data-faq). The adapter assumes publication after 20:00 ET plus 15 minutes and selects the 20:30 ET dataset decision clock. This avoids exposing final daily volume at 16:30 ET. OHLC is a first/last eligible feed print, not an official exchange auction price. The optional dataset decision_time policy is included in its hash when nondefault. CSV sources including extended-hours volume should select the same evening policy.

Real raw datasets require corporate_actions_reviewed=true before scheduling: the source owner must review split coverage and supply all effective events. Both import forms expose this attestation. It is stored in the immutable revision/hash, and is not an independent vendor-data audit. Unfinished API daily sessions are rejected rather than storing partial candles as completed history.

Both import forms also support `dividends_complete`; it remains false unless explicitly attested. Alpaca imports attach supplied FX/actions to the same immutable revision. No automatic FX or corporate-action retrieval has been added.

## Free-first source selection for US equities

SPY is the requested broad S&P 500 ETF acceptance instrument, not a Nasdaq-100 fund. US-listed Nasdaq stocks are in scope for these sources; adding QQQ or individual tickers is a later data import, not a reason to replace the engine. See the [issuer's SPY page](https://www.ssga.com/us/en/individual/etfs/state-street-spdr-sp-500-etf-trust-spy). Current symbols alone do not define a historically valid stock universe.

| Source | Role and access | Compromises / current integration |
| --- | --- | --- |
| Alpaca historical SIP | Verified raw SPY 2018–2022 bars with supplied paper credentials; key ID + secret | Existing adapter selects SIP/IEX. Current revised history, assumed evening availability; other symbols/qualified FX/actions still need review |
| [Tiingo EOD](https://www.tiingo.com/documentation/end-of-day) | Alternative daily US equities/ETFs with token; raw and adjusted fields, ex-date `divCash`, split factor | No adapter yet; normalize raw fields to existing CSV. Verify current plan/entitlement before purchase. EOD dividend field alone lacks the payment/declaration evidence required here. Tiingo notes evening corrections, so latest history is not automatically vintage-safe |
| [Massive, formerly Polygon](https://massive.com/knowledge-base/article/how-much-historical-stock-data-does-massive-have) | Broader alternative US market data API | Free Basic has a rolling two years, Starter five, Developer ten, Advanced all history. As of November 2026, 2018 is outside the free window and requires an adequate paid tier. No app adapter; CSV preparation would be needed. No paid plan is selected |
| [Norgate](https://norgatedata.com/index.php/pricing/) | Candidate for later US stock-universe research, including survivorship-bias-free datasets | Subscription/history tier and export workflow must be checked. Windows updater/export integration is separate from the deployed app. Not necessary for the initial single-SPY run and not selected |

Do not substitute adjusted-close downloads for raw OHLCV plus actions: that can encode later splits/dividends in earlier prices or double-count distributions. A different source requires explicit provenance and a new immutable revision. Only Alpaca SPY historical SIP has been live-tested in this phase; alternative providers remain unverified.

## Historical USD/SGD: publication timing matters

2026-11-05 update: live FRED v1 initial-release retrieval now succeeds. A standalone preparation script and private candidate CSV exist; no FX revision has been accepted/imported. Source reconciliation flags and measured freshness (seven days fails; 14 days passes for this candidate) are in [fx-data-review.md](fx-data-review.md). The key is read from the preparation process, not an app setting. The assessment/procedure below remains relevant, but statements that full extraction has not started are superseded by this audit.

The free candidate is Federal Reserve **[DEXSIUS](https://fred.stlouisfed.org/series/DEXSIUS)** via **ALFRED vintages**, not an ordinary latest-value FRED CSV. Units are SGD per USD, matching the ledger. The series is daily observations of noon New York buying rates; the [Fed publishes the previous week's daily observations with its weekly H.10 release](https://www.federalreserve.gov/feeds/h10.html), generally Monday at 16:15 ET. Observation date is therefore not availability date.

The [FRED observations API](https://fred.stlouisfed.org/docs/api/fred/series_observations.html) requires a free registered API key and supports initial-release-only output (`output_type=4`) and explicitly bounded real-time periods. Its default real-time period is today. The [real-time-period documentation](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html) explains why latest revised history differs from as-known history. Inspect actual 2018–2022 vintage coverage before calling this source accepted.

Preparation procedure:

1. Retrieve original/initial-release DEXSIUS values with explicit observation and real-time bounds, including enough observations/publications before 2018-01-01 for coverage. Retain API response and query parameters with the key redacted; follow any pagination and exclude missing-value markers rather than fill them.
2. Verify each vintage's first-publication date against archival release evidence. Retain the original value rather than today's revision. Translate the documented observation time with `America/New_York`, respecting DST.
3. Use evidenced publication timestamps for `available_at`. If the archive provides only an availability date, a deliberately later boundary (e.g. midnight New York **after** that date) can be used only as an explicitly documented conservative availability policy; it is not a measured publication time. Do not infer a same-day release from the observation date. Missing or ambiguous vintage evidence remains a blocking limitation.
4. Inspect FX age at every engine clock. Weekly publication can make the latest known observation older than the default seven-day limit. The existing profile supports up to 14 days; select it explicitly only after reviewing the actual gaps and acknowledging a lagged reference-rate model. No future backfill, daily interpolation or unlimited carry-forward is allowed.
5. Import the normalized `observed_at,available_at,rate` CSV with equity/actions in one revision and record the FX policy/source in combined provenance. This candidate is free and auditable, but stale reference rates are not historical executable conversion quotes. An API credential does not resolve that modeling compromise.

An additional keyless route was confirmed on 2026-11-05: [the Fed's January 7, 2019 archived release](https://www.federalreserve.gov/releases/h10/20190107/) includes the preceding week's daily Singapore rates, its release date and explicit missing-value markers. A FRED key is therefore needed for the FRED API workflow, not for every possible FX-source workflow. Full archive extraction, coverage and publication-time review remain pending; this single inspected release is not an accepted FX dataset.

The **[ECB reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)** are another keyless alternative for assessment: compute SGD/USD as `(SGD per EUR)/(USD per EUR)` using the same reference date. ECB publishes around 16:00 CET on working days and discourages transaction use. A latest historical download does not prove original vintages or exact availability. Do not substitute it into the acceptance dataset until archival/publication and revision assumptions are established. No FX candidate has yet been imported or certified against the engine's required timestamps.

## SPY corporate-action review

Indicator/external-input follow-up: MACD, stochastic, RSI, EMA and volume use existing OHLCV without a new key. Reviewed FRED snapshots or timestamped CSV sources can now drive signals through frozen revisions; they remain separate from accounting FX/actions. Fear & Greed has no qualified automatic feed configured. Its CSV path requires permitted US equity index history with defensible publication metadata; current VIX's unknown original timestamps prevent strategy approval. See [source workflow](strategy-inputs.md). No new provider subscription is required for the implemented capability.

Live Alpaca action testing is now recorded in [corporate-action-source-check.md](corporate-action-source-check.md): HTTP 200 with existing credentials. For 2018–2022, 19/20 issuer dividends were returned, seven payment dates were missing and one amount had a USD 0.0000001/share discrepancy. For 2022–2025, all 16 issuer dividends matched in amount/payment date. No declaration timestamps or split records were returned. This is corroboration, not complete point-in-time certification; no action data was imported as reviewed.

Use the US [State Street historical distributions and distribution schedule](https://www.ssga.com/us/en/intermediary/resources/documents/etf-dividend-distributions) as the primary issuer starting point, with original dated announcements for historical knowledge. The page provides historical XLSX and schedule PDF downloads; the workbook's 2018–2022 coverage was inspected as recorded below, while historical declaration timing remains unresolved. Do not use Australian SPY CDI distribution dates. Review all splits as well as dividends; a dividend file is not evidence of split completeness. Alpaca/Tiingo corporate-action products may help cross-check, but their historical coverage, entitlement and timing must be verified rather than assumed.

On 2026-11-05 the historical XLSX was downloaded and inspected: 20 SPY distribution records cover 2018–2022 with amounts and ex/record/payable dates, including the December 2022 payment in January 2023. The workbook contains no declaration timestamps or split-history fields. The current schedule PDF concerns 2026, so it cannot establish the historical declaration clock. Full source reconciliation and pre-open availability evidence remain outstanding.

Keep source files, declaration evidence, ex-date, record date (for reconciliation), payment date, amount, split ratio, transformation notes and a review log. A date-only same-day announcement is insufficient to assert knowledge before the effective open. Do not fabricate an earlier timestamp, missing payment date, zero dividend or no-split attestation. Price-only data cannot certify total-return acceptance. See [the deployment/integration runbook](deployment-verification.md) for UI steps, required credentials and the pending independent fill/accounting audit.

## November 7 streaming/source follow-up

The [strategy conversation](strategy-conversation.md) uses selected local frozen
evidence with explicit cutoff and source audits. It does not fetch news or vendor
records automatically. Existing LLM credentials suffice; estimates remain separate
research commentary.

Alpaca supplied 96 monthly AAPL/MSFT/SPY partitions for 2018–2025;92 complete
partitions have reviewed research children, while four with 27 missing intervals
remain blocked. Congress access/clock/use qualification is unresolved; no new
Congress key or subscription was configured. See the
[actual intraday/Congress source evidence](intraday-congress-verification-2026-11-07.md).

## Bounded House canonical-ledger intake

The [Congress source review](congress-source-workflow.md) page can acquire official
House annual indexes and specific PTR PDF/archive pairs without a new API key. It
retains exact responses/hashes and validates matching archived bytes/Memento
headers. Manual row/issuer/taxonomy review and explicit canonical amendment links
precede approval. The first qualified source is only the Pelosi March2022 AAPL/
MSFT filing cohort; it is not broad Congress coverage. Senate access, original
first-public clocks and automatic PDF interpretation remain pending. Cross-year
index support is now available in the bounded review workflow. [Actual checks](congress-ledger-verification-2026-11-08.md).

## Full available PTR inventory and Senate bridge

The [full-scope Congress collector](congress-full-coverage.md) now inventories
all House PTR filers across2018–2025 with boundary-support indexes, acquiring
exact PDFs and review-only text in resumable batches. Valid report IDs can be
seven or eight digits.403/429 stops source requests. Archive search targets do not
become publication times; returned captures must be verified. The full collection
is not yet strategy eligible. Senate normal browser/server access remains403 here;
a user-run same-origin exporter can retain current captures without session
credentials. No real Senate report or original posting clock was obtained in
this phase, and no extra API key resolves the access denial.
