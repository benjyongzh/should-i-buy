# Free congressional-disclosures dataset assessment

[Executed qualification follow-up](retail-source-qualification-2026-11-08.md):
45 snapshot shards and all retained House inventory IDs check out; the bounded
Congress sample retains unknown public clocks. Ninety-eight literal analyst
announcements are imported unreviewed, and two issuer/SEC earnings pairs are
normalized as staging evidence. No new key or broad coverage approval is implied.

**Decision:** relevant and useful as a free, provenance-bearing staging source and
cross-check for House/Senate information. **Not approved as a drop-in historical
retail-availability feed.** This review read the documentation and implementation,
retrieved the public manifest/methodology, and ran three explicitly synthetic
reproductions against selected pinned upstream functions. No bulk dataset was
imported, application code changed, backtest executed or container operated on.

Repository commit reviewed: `2965e8796bd4cb9423a83b964a1f9dbd076a0ad6`.
Hugging Face dataset commit observed: `bb5e1c4d5dd052ffe4e14def1ac6b1f25f7bc2bb`.
These identify separate code/data publications; the public snapshot does not by
itself prove which application build produced every historical shard.

## Relevance and actual metadata

The hosted [dataset](https://huggingface.co/datasets/austin-starks/congressional-stock-trades)
is downloadable without a data-provider API key. Its manifest, generated
**2026-11-07 14:04:40 UTC**, declares:

| Item | Producer manifest |
| --- | ---: |
| Filing documents | 10,883 |
| Printed transaction rows | 187,288 |
| Consolidated event-version rows | 182,595 |
| Failed filings | 1 |
| Members represented | 468 |

All three tables advertise partitions for every requested year, **2018–2025**.
That is a partition-presence check, not an independent count of complete records
for every member, chamber or ticker. The whole published Parquet snapshot is only
9,085,655 bytes by its manifest; hosted download avoids our direct Senate denial.
No npm installer or upstream OCR/model service was run during this assessment.

The latest filing dates in the inspected metadata are House **2026-11-05** and
Senate **2026-11-04**. The stated refresh target is **20 hours after successful
upstream integrity publication**, not a real-time SLA. A pass flag coexists with
one failed filing; do not turn that failed extraction into a no-trade history.
Checksums and freshness are useful acquisition controls, not historical market
availability evidence. See the [snapshot](https://huggingface.co/datasets/austin-starks/congressional-stock-trades/blob/bb5e1c4d5dd052ffe4e14def1ac6b1f25f7bc2bb/snapshot.json).

## What its implementation gets right for our purpose

- Separate filings, printed rows and reconciled event versions; original source
  URLs/document hashes and parser/extraction status are retained.
- Owner, disclosed amount range, partial sales and instrument descriptions are
  preserved. A range is not a known purchase quantity or precise cash amount.
- Reconciled events expose availability and supersession fields. Past reads need
  both the then-available version and its validity window; selecting only today's
  unsuperseded rows would lose earlier historical states.
- Senate electronic tables are parsed structurally. Scans/text extraction have
  validation/reconciliation and explicit failures. The download code checks sizes
  and SHA-256 hashes. Existing model/OCR output can be consumed without paying to
  rerun that extraction.
- Member identities link to a pinned congress-legislators source. Unknown and
  non-member filers remain distinguishable from resolved members.

These observations come from the [pinned source tree](https://github.com/austin-starks/congressional-disclosures/tree/2965e8796bd4cb9423a83b964a1f9dbd076a0ad6/packages/congressional-disclosures/src),
including normalization, event consolidation, download validation and identity
code. Upstream test files contain amendment/option and same-clock correction
cases; this review did not run their complete test suite.

## Material qualifications

**1. The availability clock is an assumption.** Both normalizers call
`endOfDayNewYork(filingDate)`. In
[dates.ts](https://github.com/austin-starks/congressional-disclosures/blob/2965e8796bd4cb9423a83b964a1f9dbd076a0ad6/packages/congressional-disclosures/src/lake/dates.ts),
the function constructs 23:59:59.999 New York time. Source labels explicitly say
House index filing date / Senate filed date. A synthetic reproduction confirms
2022-03-04 becomes **2022-03-05T04:59:59.999Z**. The manifest's latest availability
values also have that day-end shape.

This is not measured public posting, provider ingestion or retail notification.
Filing-day end is not necessarily a safe upper bound if posting occurred later.
It can support a separately labeled daily research assumption, but must not be
silently reclassified as verified public availability or used for exact intraday
reactions. We can accept reliable provider publication evidence without requiring
Wayback for every record; this dataset currently supplies filing-date proxies.

**2. Consolidation involves matching heuristics.** The
[event builder](https://github.com/austin-starks/congressional-disclosures/blob/2965e8796bd4cb9423a83b964a1f9dbd076a0ad6/packages/congressional-disclosures/src/lake/events.ts)
can merge cross-document observations with matching ticker/date/owner/action/
amount/instrument fields even when no unique source transaction ID or explicit
amendment relation exists. A synthetic two-report example produces one event.
That can represent a real repeated disclosure, but identical disclosed fields
also cannot distinguish two separate transactions. This demonstrates an
ambiguity, not a measured count of errors in the actual dataset.

A second reproduction finds a later repeated filing's contributor ID added to an
earlier version's provenance. That does not change that example's financial
fields, but our historical LLM/evidence view must not expose later contributors
at earlier cutoffs. Same-clock correction replacement also needs to be understood
under the coarse filing-day timing assumption.

**3. Extraction quality still needs source comparison.** The
[methodology](https://huggingface.co/datasets/austin-starks/congressional-stock-trades/blob/main/METHODOLOGY.md)
records manual corrections and ambiguous scans. It describes date corrections
in 2020 and notification-date corrections in 2022 where a digit is ambiguous.
Keep these flags and raw evidence; do not treat every corrected day as a directly
observed original fact. Independent model agreement alone does not prove a row.

**4. Printed symbols are not a historical security master.** The normalizer
separates printed symbols from unresolved/resolved identity. We must distinguish
stock, option exercise, grant, bond, fund and exchange; preserve household owner
and amendment lineage. A ticker alone cannot turn an option transaction into an
ordinary equity purchase. The earlier reviewed Pelosi cohort should be a useful
cross-check, not overwritten by a new aggregate's interpretation.

**5. Fresh publication now is not historical delivery then.** Producer metadata
shows a recently generated snapshot and its target refresh rate. It does not
establish 2018–2025 delivery latency or guarantee future operation. Record actual
snapshot versions/first-seen times going forward. The code's MIT license and the
underlying disclosure-data use notice are separate; the user's existing personal,
non-commercial authorization remains the applicable project scope.

## Recommended adoption sequence

1. Download a commit-pinned snapshot and verify declared hashes, sizes and counts.
2. Compare the filing inventory by chamber/year with retained House inventories;
   quantify failed/missing reports and check AAPL/MSFT/SPY slices. Preserve all
   three source tables; do not blindly sum printed rows and consolidated events.
3. Reconcile the already reviewed March2022 Pelosi original/amendment cohort and
   representative Senate HTML/paper reports. Retain unresolved differences.
4. Map only reviewed issuer/instrument/action categories, version links and amount
   bounds into new immutable revisions. Filter metadata as well as signal fields
   at the strategy clock. Keep the earlier qualified cohort unchanged.
5. For strict retail replay, obtain evidenced posting/provider clocks where
   available. Any filing-date-plus-delay approximation belongs to a conspicuous
   research policy and remains distinct from certified original availability.

This assessment recommends proceeding to a **bounded import/qualification pilot**,
not declaring the entire dataset strategy eligible. No new key is required for
that pilot. Private metadata receipts, pinned source snippets and synthetic
reproductions are in ignored `.local/congress-dataset-review-20261108/`.

## Earnings source decision

Per the user's instruction, use **issuer investor-relations earnings releases and
SEC original filings/exhibits**. Keep quarterly EPS/revenue, guidance and
GAAP/non-GAAP definitions separate; do not use the fiscal quarter-end as the
information clock. Reuse the 18 earnings-related submissions retained in the
[retail pilot](retail-information-pilot-2026-11-08.md). Source access and exhibits
are verified; continuous quarterly metric extraction/review remains pending.

Two original source pairs were inspected in this assessment:

- [Apple FY2025 Q1 release](https://www.apple.com/newsroom/2025/01/apple-reports-first-quarter-results/),
  dated 2025-01-30, pairs with retained accession `0000320193-25-000007`.
  The original SEC header accepts it at **16:30:23 Eastern**. That is an acceptance
  clock, not automatically an exact investor notification time.
- [Microsoft FY2025 Q2 release](https://www.microsoft.com/en-us/Investor/earnings/FY-2025-Q2/press-release-webcast),
  dated 2025-01-29, pairs with retained accession `0000950170-25-010484`.
  Its original SEC header acceptance is **16:08:56 Eastern**.

The announcement, SEC acceptance/dissemination and conference-call time must stay
separate. A date-only issuer page does not certify its exact intraday publication
instant. For missing exact clocks, retain the uncertainty or apply an explicit
conservative daily policy. Earnings-surprise rules still need independently dated
pre-announcement consensus; do not derive that from later analyst snapshots.

## Free analyst-action sources

| Source | Free information observed | Suitability and remaining limits |
| --- | --- | --- |
| Existing Alpaca/Benzinga news access | Our pilot already retained articles mentioning upgrades/downgrades/targets | Best immediate no-additional-subscription path: extract only explicitly reported firm/action/rating/nominal target facts, retain article ID and version clock, and leave unreported fields null. This is a news-derived subset, not all analyst actions. |
| [Finviz company page](https://finviz.com/quote.ashx?t=AAPL&p=d) | Public dated individual firm/rating/target rows | Useful human review/corroboration. No complete free 2018–2025 bulk archive or original intraday clocks verified; free viewing is not an automated-export entitlement. |
| [Benzinga public ratings](https://www.benzinga.com/analyst-stock-ratings) | Public individual analyst/rating/target rows | Useful corroboration/discovery. Free web viewing does not include its separately licensed API/history. |
| [MarketBeat ratings](https://www.marketbeat.com/ratings/) | Public recent brokerage actions/ratings/targets | Useful human review and source discovery; no free historical bulk entitlement verified. |
| [Finnhub](https://finnhub.io/docs/api/recommendation-trends) | Free-account candidate for recommendation trends | Trends are aggregate buy/hold/sell counts, not a sequence of individual actions. Its published OpenAPI distinguishes those endpoints. Current free-key entitlement/history has not been tested; no key supplied and no free individual-actions archive is claimed. |

A comprehensive, verified, free 2018–2025 individual-actions archive was **not**
established by this review. That need not block a retail strategy based on the
specific analyst announcements in its selected news feed. The sensible free-first
path is existing news + explicitly extracted facts + source corroboration,
retaining the original article version and access policy. No paid subscription,
API key request or scraping of restricted pages is necessary for this assessment.
