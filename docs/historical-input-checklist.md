# What to supply for historical strategies

Target research period: **2018–2025, replayed sequentially**, plus indicator
warm-up and event lookback before the first decision. Every rerun is retained;
repeated tuning against the same history is labeled in-sample. Period reports
help compare regimes but do not establish future performance.

Existing server Alpaca, FRED and LLM credentials are already configured. Do not
paste keys into strategy JSON, browser forms, source files or chat. Put optional
keys only in the server `.env`, then recreate this project's affected services.
Configuration flags do not establish account entitlements or historical coverage.

| Capability | Source/path implemented | What is still needed |
|---|---|---|
| Daily SPY accounting | Existing reviewed combined daily/FX/dividend revision, 2016–2025 | No new key. Existing real daily acceptance remains preserved; new features need their own acceptance. |
| Intraday timing and indicators | Alpaca raw minute bars aggregated into complete regular-session intervals; JSON/CSV import | Existing Alpaca key may suffice. Verify SIP access for requested dates/symbols, review completeness and disclosed completion-delay/revision policy. Start with a short SPY slice. |
| Historical sectors/security universe | Immutable state-transition JSON/CSV import | Historical classifications/membership and stable security identities, with effective and availability clocks, including starting state and changes. Supply MSFT/AAPL/CVS histories if comparing them. Current metadata is insufficient. |
| Company news | Alpaca/Benzinga news preparation; archival JSON/CSV import | Check existing Alpaca news entitlement. Original article versions, titles/text, symbols, publication/availability/update clocks and coverage/access evidence. No promise of all news. |
| Analyst changes | Benzinga individual ratings preparation or archival JSON/CSV | Optional **`BENZINGA_API_KEY`**, historical entitlement covering 2018–2025, and verified source timezone. Alternatively supply timestamped reports/exports. Require firm/analyst, original rating/nominal USD target and actual version clock. |
| Congress trades | Typed historical JSON/CSV import and disclosure-gated rules | Original public House/Senate disclosures, identities/ticker mapping, amendment lineage, amount bounds and evidenced public-posting/first-seen times. Transaction/filing dates alone are insufficient. No Congress API key is required for file imports. |
| Geopolitics/oil/sector events | Global/sector event streams and retained keyword rules | Timestamped source archives with declared coverage and historical access evidence; source tags or documented deterministic rules. No automatically comprehensive geopolitical feed is configured. |
| Macro indicators | Existing reviewed FRED/external-series path; typed release import | Existing FRED key suffices for supported series preparation. Historical forecasts/consensus and release clocks are additional inputs for surprise rules. Latest revised macro values are insufficient. |
| Fear & Greed | Existing reviewed external-series CSV path | A lawful archive with observation, original availability, source/version evidence and coverage. No qualified automatic original-vintage history has been supplied. |
| LLM authoring | Server structured-output strategy planning | Existing `LLM_API_KEY`, `LLM_MODEL`, optional `LLM_BASE_URL`. No brokerage key. Proposals still require review, draft acceptance and explicit publication. |

For each additional equity, supply raw daily bars/warm-up, historical USD/SGD as
required, and separately reviewed splits/dividends. Intraday bars cannot replace
corporate actions or accounting FX. Existing lagged FRED FX uses the expressly
reviewed 14-day research limit; it is not an intraday conversion quote. A strategy
requiring actual executable FX needs a separately qualified timestamped source
and execution policy. Delisting/merger settlement also requires future engine
work; providing a terminal record alone does not implement settlement.

## Recommended order

1. Reuse Alpaca first for short historical SPY intraday and news checks. Its
   [historical news documentation](https://docs.alpaca.markets/us/v1.1/docs/historical-news-data)
   describes Benzinga coverage back to 2015. Account access and original article
   version retention must be tested separately. Avoid buying a second price feed
   before checking the current account.
2. Add a small curated equity universe with historical states and fully reviewed
   accounting inputs. Then extend complete partitions toward 2018–2025. Source
   coverage and processing limits are checked before queue admission.
3. Add individual analyst changes once archival coverage and nominal target
   semantics are confirmed. The
   [official Benzinga client](https://github.com/Benzinga/benzinga-python-client)
   documents ratings and update clocks. Do not assume a current subscription
   includes all eight historical years or original versions.
4. Normalize Congress disclosures next. Use original
   [House disclosure records](https://disclosures-clerk.house.gov/) and
   [Senate electronic disclosures](https://efdsearch.senate.gov/search/) as
   authorities, with corroborating archives when first-public timing is absent.
   [House guidance](https://ethics.house.gov/financial-disclosure/) distinguishes
   filings and amendments. Collection/normalization and exact historical public
   times remain outstanding; no unattended Congress scraper is implemented.

Prefer documented APIs or licensed/public exports. Scraping a current page cannot
recover missing past versions or first-public times. Source access conditions and
redistribution rights must be checked for any chosen archive; an unknown clock
cannot be replaced by a convenient guessed time. A date-only source can be used
only with an explicit conservative availability policy supported by evidence.

## File contracts and practical limits

Use **Strategy sources → Load labeled synthetic schema example** to inspect each
family without importing it. Replace all synthetic observations and metadata
with actual sourced records before calling it historical. Full JSON and CSV
rows plus JSON metadata are supported; array cells use `|`, typed `details` uses
JSON, timestamps carry explicit timezones, optional blank CSV cells use defaults.
`GET /api/strategy-inputs/schema` exposes the exact contract.

Provider preparation is limited to 32-calendar-day partitions and five symbols
per request. Runs allow up to 100 selected source partitions, one million total
source rows, 200,000 execution intervals and 500,000 decision records. A single
SPY 5-minute full-period series can approach/exceed a bound depending on warm-up;
one-minute eight-year replay exceeds current limits. Choose a coarser supported
interval or explicitly bounded experiments. Raising limits/full-market scaling
requires measured capacity work; do not silently reduce dates or omit data.

News preparation retains bounded plain-text prefixes (30,000 characters) and
source-response/content hashes. Keep licensed original documents separately for
source review; a hash or a truncated article cannot recover a missing version.

Source review is an explicit attestation, not automated certification of vendor
completeness. Current revised records are retained at their actual version clock;
if originals are absent, early historical coverage remains unknown and cannot be
honestly approved as complete for strategies depending on those originals.
