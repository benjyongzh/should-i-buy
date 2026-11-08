# Retail information boundary: AAPL/MSFT source pilot

The target is a retail investor using declared news/data feeds, with information
arriving over time. Direct Senate access is not a prerequisite: a qualified retail
provider can supply Congress information. Publisher/provider identity, delivery
clocks, revisions and coverage matter; a web-archive capture is not mandatory for
every trustworthy provider record.

**Actual result, 8 November 2026:** existing Alpaca access supplies historical and
recent AAPL/MSFT news. The pilot retained 92 successful response bodies, checked
1,282 news records and 58 original SEC filings, and imported 11 **unreviewed,
incomplete** source revisions into the existing application. It did not qualify
continuous 2018–2025 news/insider coverage, acquire a structured analyst feed or
run a new information-driven backtest. Earlier reviewed SEC streams remain valid
within their earlier scope.

## What was collected

News requests selected AAPL/MSFT, exhausted pagination, requested content when
available and retained the exact decoded response bodies and SHA-256 hashes.
The historical windows deliberately sample each year rather than pretending to
cover the intervening periods. The recent window tests access today, not the
historical speed of delivery or an ongoing real-time polling service.

| Publication sample | News records | Updated versions | Without full body |
| --- | ---: | ---: | ---: |
| 2018-07-25–31 | 62 | 22 | 37 |
| 2019-07-25–31 | 85 | 48 | 36 |
| 2020-07-25–31 | 85 | 34 | 36 |
| 2021-07-25–31 | 158 | 82 | 64 |
| 2022-07-25–31 | 182 | 95 | 57 |
| 2023-07-25–31 | 160 | 118 | 38 |
| 2024-07-25–31 | 160 | 99 | 32 |
| 2025-07-25–31 | 181 | 129 | 53 |
| 2026-11-02–06 | 209 | 20 | 66 |
| **Total** | **1,282** | **647** | **419** |

Missing full content can still leave a provider summary or headline. No body,
sentiment, EPS, rating change or trade amount is invented. Deterministic keyword
rules found 508 earnings mentions, 292 analyst mentions, 33 insider mentions and
17 Congress/politician mentions. These overlap and are **text matches**, not
validated structured earnings, ratings or transactions.

The SEC sample contains **36 original Form 4s, four Form 4 amendments and 18
8-Ks selected by earnings item 2.02**, across 2018–2026: 28 Apple and 30 Microsoft
filings. All 18 retained earnings submissions contain EX-99 exhibits with
financial-results/earnings language. Earnings numerical fields and pre-release
consensus are not normalized. Selected ownership XML supplies **39 nominal
non-derivative transaction rows**. Derivative rows are counted but not normalized.
Missing prices remain null; grants, exercises and amendments are not relabeled
as new open-market purchases. Historical holdings, investment intent, complete
insider coverage and amendment lineage are not inferred.

## Timing and the practical qualification boundary

1. **Declared feed access.** Alpaca/Benzinga records are labeled subscription
   access. This models a licensed retail news feed; it does not certify that every
   article was freely accessible or that Alpaca's API existed throughout the
   historical period. A website's public headline and permission for automated
   historical ingestion are separate questions.
2. **Current article versions.** Each candidate uses `max(created_at, updated_at)`
   for availability. Publication and update clocks must exist and have explicit
   timezones; a missing update clock no longer falls back silently to creation.
   Current text is not backdated to an earlier article version.
3. **Query limitations.** Alpaca documents sorting by update date. A real 2022
   response included article `17808018`, originally published in October 2020 and
   updated during July 2022. Its raw row is retained and its exclusion from the
   publication-cohort candidate is counted explicitly. Exhausted query pagination
   does **not** prove a complete archive of what originally appeared in that week:
   later edits can change which records a historical query returns.
4. **SEC delivery assumption.** Original submission accession, ownership issuer,
   primary XML and header acceptance are checked against inventory. Form 4
   candidates use a declared **next-session-close delivery assumption** after
   acceptance. This is deliberately coarse daily research timing, not a measured
   publication instant or a certified intraday reaction clock. The SEC can be a
   chosen retail information source, but this is not a reconstruction of Webull's
   own notification history.
5. **Coverage is feed-specific.** A sample is a sample. No events between sample
   windows, missing original versions, unparsed derivatives and unreviewed
   amendments become fabricated zeros. No candidate receives complete/reviewed
   status merely because a request succeeded.

Sources: [Alpaca news endpoint and update-date sorting](https://docs.alpaca.markets/us/reference/news-3),
[SEC public APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces),
[SEC acceptance/publication guidance](https://www.sec.gov/about/webmaster-frequently-asked-questions).

## What is available in the UI

Open the local app at `http://127.0.0.1:18094/sources`. Nine bounded news revisions
and two visibly labeled **SAMPLE** insider-filing revisions are retained. Select
one to inspect its clocks, source URL, content identity, policy and records. News
is hidden by **Public records only**; deselect it to inspect the licensed feed.
Set **Historical cutoff (UTC)** to inspect only then-available versions. This does
not approve a source. Do not attest continuous coverage for these samples.

Imports use the existing immutable source-import endpoint. Every exported payload
matches its candidate exactly. All 11 pre-existing backtests in that project
remain unchanged. A read-only container audit confirms **all 57 pre-existing
containers unchanged**. The separate House collection has acquired all 6,234
indexed PDFs and is now blocked on archive access; it is not historically
qualified, and this pilot did not restart or alter that worker. No strategy version or engine behavior changed.

A live browser check exposed a source-viewer bug: the full exported payload has
an empty `bars` array even for events/universe sources, and that array hid their
actual records. Kind-based selection fixes it. Regression tests reproduce the
event/universe failures before the fix and pass afterwards. A **new frontend on
loopback 18094** serves the fix and uses the existing 18092 project API; it does
not replace the older frontend.

The source adapter fixes and pilot run against the checked-out code in disposable
processes. **No existing API/frontend/worker container was rebuilt or restarted.**
The existing deployed provider-fetch endpoint still uses its previous image;
these new candidates were prepared separately and imported through the existing
compatible file-import path. Deploy the checked-out adapter in a future isolated
release before relying on its new validations through the provider-fetch UI.

## Quiver pricing and remaining inputs

The [official Quiver API pricing](https://api.quiverquant.com/pricing/) checked on
8 November 2026 lists **Hobbyist US$30/month**, or **US$300 billed annually**,
including Congress trading. **Trader is US$75/month**, or US$750 billed annually,
and adds insider/other datasets. These are personal, non-commercial plans. There
is no free API tier shown. Free-to-view information is not free API access.
Quiver's [API overview](https://api.quiverquant.com/) advertises Congress history
from 2014, but insider history from 2021; that alone would not fill 2018–2020
insider coverage. Historical clocks, revisions and entitlements still need sample
verification. No Quiver purchase, key configuration or API data acquisition was
performed.

**No new key was needed for the completed pilot.** Existing Alpaca credentials and
`DATA_SOURCE_CONTACT_EMAIL` worked. The next inputs are:

- For Congress through Quiver: optionally obtain the Hobbyist API access/key,
  after confirming historical data/export and personal-use entitlements. The
  Quiver adapter is not implemented; do not expect a new environment variable to
  enable it yet. Senate's 403 does not block other source work.
- For structured analyst changes: a provider/export with individual firm, action,
  nominal targets and version/publication clocks. The existing Benzinga ratings
  adapter has no configured key. News mentions are already inspectable, but cannot
  substitute for a structured rating history. Do not purchase a second subscription
  until its sample/history is checked.
- For a continuous historical retail replay: expand the selected feed coverage
  across 2018–2025, establish the original-version/archival policy, finish insider
  coverage and amendment review, and explicitly review new immutable revisions.
  Current-version snapshots can support clearly labeled research, but they must
  not be described as a complete replay of original retail news delivery.
- For future freshness: a separately bounded capture schedule can begin retaining
  first-seen versions now. The pilot is not an operating scheduled collector and
  does not demonstrate a delivery-latency SLA.

## Verification evidence

**304 backend tests including fresh PostgreSQL migration/immutability checks and
62 frontend tests pass; Ruff and frontend build pass.** New adversarial tests
cover missing/naive update clocks, unrequested tickers, updated text, incomplete
pagination, changed retained bytes, missing prices, wrong issuer/accession/clocks,
non-finite financial values, amendment/award/exercise classification, original
XML rendering paths and double HTTP decompression.

Six actual browser checks pass on the new frontend: licensed-access filtering,
all 182 records in the inspected 2022 sample, an actual article-version cutoff,
explicit review controls, 390px layout and no runtime errors. Three documentation
browser checks pass for the diagram and mobile layout.

An independent standard-library audit, without importing the new normalizer,
checks all **92 response hashes, 1,282 news clocks/identities, 58 original filing
identities, 39 nominal transaction rows and 18 earnings exhibits**. It recomputes
the report hash. The failed initial attempts remain retained; the final attempt
reused 36 exact checked responses and fetched 56 missing originals rather than
silently changing earlier evidence. This is source verification, not financial
performance or a new engine correctness review.

Private credentials, source bodies, candidates, receipts and test reports remain
under ignored `.local/retail-information-20261108/`. No raw licensed news content
or runtime database is committed. See the [visual workflow](data-workflow.html#retail-boundary).
