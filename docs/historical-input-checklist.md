# What to supply for historical strategies

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

Current follow-up: one permanent strategy conversation has complete eligible recall
and [read-only per-version transcripts](conversation-history-verification-2026-11-07.md).
Personal non-commercial use is confirmed for Congress research; original reports
and conservative public-observation proofs are retained. The two imported raw
observations remain incomplete/unreviewed; no new key is needed, and complete
Congress company/filer coverage still requires qualification. See
[current Congress evidence](congress-qualification-2026-11-07.md).

For a visual overview of sources, review gates and the simulation clock, open the
[historical data workflow](data-workflow.html).

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
| Daily accounting: SPY, AAPL and MSFT | Reviewed combined raw daily/FX/action revision, 2016–2025; [real acceptance](real-equity-acceptance-2026-11-06.md) | No new key. Fixed hold/SMA/RSI acceptance and bounded AAPL/MSFT BLS/SEC checks pass. Additional tickers need their own action/price review. |
| SEC company filing events | Reviewed AAPL/MSFT 8-K/8-K/A stream, 2018–2025, with literal item tags and separate amendments | No new key. Uses the explicit next-session-close research availability proxy; precise first-public delivery remains unverified. |
| Intraday timing and indicators | Alpaca raw minute bars aggregated into complete regular-session intervals; JSON/CSV import | Existing Alpaca key may suffice. Verify SIP access for requested dates/symbols, review completeness and disclosed completion-delay/revision policy. Start with a short SPY slice. |
| Historical sectors/security universe | Immutable state-transition JSON/CSV import | Historical classifications/membership and stable security identities, with effective and availability clocks, including starting state and changes. Supply MSFT/AAPL/CVS histories if comparing them. Current metadata is insufficient. |
| Company news | Alpaca/Benzinga news preparation; archival JSON/CSV import | Check existing Alpaca news entitlement. Original article versions, titles/text, symbols, publication/availability/update clocks and coverage/access evidence. No promise of all news. |
| Analyst changes | Benzinga individual ratings preparation or archival JSON/CSV | Optional **`BENZINGA_API_KEY`**, historical entitlement covering 2018–2025, and verified source timezone. Alternatively supply timestamped reports/exports. Require firm/analyst, original rating/nominal USD target and actual version clock. |
| Congress trades | Typed historical JSON/CSV import and disclosure-gated rules | Original public House/Senate disclosures, identities/ticker mapping, amendment lineage, amount bounds and evidenced public-posting/first-seen times. Transaction/filing dates alone are insufficient. No Congress API key is required for file imports. |
| Geopolitics/oil/sector events | Global/sector event streams and retained keyword rules | Timestamped source archives with declared coverage and historical access evidence; source tags or documented deterministic rules. No automatically comprehensive geopolitical feed is configured. |
| Macro indicators | Reviewed FRED/external-series path; reviewed BLS payroll/unemployment release stream | Existing FRED key suffices for supported series preparation; BLS needs no new key and uses the documented five-minute research delivery lag. Historical forecasts/consensus are additional inputs for surprise rules. Latest revised macro values are insufficient. |
| Fear & Greed | Existing reviewed external-series CSV path | A lawful archive with observation, original availability, source/version evidence and coverage. No qualified automatic original-vintage history has been supplied. |
| LLM authoring | Server structured-output strategy planning | Existing `LLM_API_KEY`, `LLM_MODEL`, optional `LLM_BASE_URL`. No brokerage key. Proposals still require review, draft acceptance and explicit publication. |

Latest follow-up: [streaming strategy conversations](strategy-conversation.md)
add clarification, source previews/audits and conditional research estimates with
the existing key. [Intraday qualification](intraday-congress-verification-2026-11-07.md)
now supplies 92 reviewed monthly AAPL/MSFT/SPY15-minute partitions. Four months with
27 gaps block a complete 2018–2025 replay; a January 2019 window test passes.
Congress needs a permitted-use basis and original public-availability archive,
not merely a new API key. No qualified Congress revision has been supplied.

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

## Company onboarding configuration

The new `/companies` workflow uses the existing server-side Alpaca credentials
and `DATA_SOURCE_CONTACT_EMAIL` in both API and worker. No additional vendor key
was needed for the real NVDA acceptance. It reuses reviewed historical FX for
SGD; a FRED key alone does not mark a new FX revision reviewed. Initial automatic
collection covers daily accounting and SEC filing presence only. Other requested
capabilities stay blocked pending their source evidence. Deploy migration 005 and
updated API/worker/frontend before using the page in a project environment;
existing Docker services on 18080 have not been changed by this implementation.
See [workflow and limits](company-onboarding.md) and [actual test evidence](company-onboarding-verification-2026-11-06.md).

## Congress qualification update

No extra key is needed for the tested House index/PDF/archive sources. The
[canonical-ledger workflow](congress-source-workflow.md) now qualifies one narrow
March2022 Pelosi filing cohort. Broader strategy requirements still need reviewed
filer/company/date inventories, exact public-observation evidence, historical
issuer identity and resolved original/amendment/instrument categories. Cross-year
supporting indexes are now supported; Senate access remains outstanding. A sparse positive sample
must not be relabeled full2018–2025 or all-Congress coverage.

## Full Congress coverage input status

House index access needs no new key. The all-filer PTR acquisition is running
with explicit gaps and no automatic approval. Senate currently needs a normally
accessible public browser session or permitted report exports; see the
[normal-session instructions](congress-full-coverage.md). Do not provide session
cookies or API credentials for this bridge. Current captures still need separate
historical posting evidence, issuer/filer identity and amendment review before
full2018–2025 Congress replay is available.
