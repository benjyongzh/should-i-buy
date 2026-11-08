# First primary-source pilot: SEC, BLS and issuer actions

**Current follow-up:** [accounting and deployed source review completed](company-intake-verification-2026-11-06.md)
for AAPL/MSFT and the selected SEC/BLS streams under recorded research policies.
The initial pilot notes below describe the earlier unreviewed state.

Status: **source pilot in progress; no new imported revision**. This document does not attest that a new
2018–2025 event history or a new equity accounting dataset has been imported.
The earlier reviewed SPY combined revision remains the only completed issuer
action baseline discussed here.

**Follow-up:** [BLS extraction and SEC document review are completed](primary-source-verification-2026-11-06.md)
for the selected fields and filings. The report supersedes the initial access
status below: candidate exports have 190 BLS and 145 SEC events, validated but
unreviewed, with explicit research availability assumptions. Application source
approval and real strategy acceptance remain pending.

## Scope and order

| Stream | Initial instrument or release | Intended use | Current status |
| --- | --- | --- | --- |
| SEC EDGAR | AAPL and MSFT 8-K filings | Company filing events and evidence for announced actions | Full 2018–2025 filing metadata inventory retained; filing contents, first-public times and semantic tags not reviewed |
| BLS | Monthly Employment Situation, 2018–2025 | Global economic release events | 96 archived release pages retained, including one pre-period release; values/vintages not reviewed |
| Issuers | Existing SPY first; then AAPL and MSFT | Cash dividends and splits for portfolio accounting | SPY reviewed in existing combined revision; AAPL and MSFT issuer files retained but not reviewed or imported |

### Initial pilot access and evidence check (2026-11-06)

| Check | Observed result | Consequence |
| --- | --- | --- |
| SEC submissions with contact User-Agent | The AAPL current submissions file and MSFT current plus older-history file were downloaded. A 2018–2025 inventory has **145 distinct 8-K/8-K/A accessions: AAPL 68, MSFT 77**, with every year represented. The [2020-07-30 AAPL 8-K](https://www.sec.gov/Archives/edgar/data/320193/000032019320000060/0000320193-20-000060-index.htm) shows acceptance 18:55:04 Eastern and links the split exhibit. | Exact source bytes and SHA-256 hashes are retained under `.local/primary-source-pilot/`. The inventory is filing metadata, not a reviewed event feed. All 145 first-public times and document semantics remain unresolved. |
| BLS archive with contact User-Agent | The archive index and **95 published 2018–2025 reference-month HTML releases** were retained, plus the December 2017 release issued in January 2018. All 96 headers state 08:30 Eastern. The [2018-02-02 release](https://www.bls.gov/news.release/archives/empsit_02022018.htm) reports January payroll increase of 200,000 and unemployment of 4.1%. | Exact archived bytes/hashes and release-clock candidates are retained locally. Nine archive pages explicitly say they were reissued or carry correction notices. Source values, affected fields and original vintages still need review. |
| BLS coverage edge cases | The archive explicitly says **October 2025 Employment Situation was not published**. The December 2025 release was issued **2026-01-09**, beyond a backtest ending 2025-12-31. | Neither can be used as a 2025 release event. The January 2018 release of December 2017 data is included as pre-period context. |
| Direct-access behavior | Initial BLS and Apple requests without a contact-identified User-Agent returned HTTP 403. Bounded retries with a contact-identified User-Agent returned HTTP 200 for both; all 95 BLS release requests succeeded at one request per 1.5 seconds. | The BLS denial cited bot controls; the successful retry does not prove which condition triggered the earlier block. No Playwright or access-control bypass was used. |
| AAPL/MSFT issuer files | Apple's [dividend/split history](https://investor.apple.com/dividend-history/) and Microsoft's [investor history](https://www.microsoft.com/en-us/investor/dividends-and-stock-history) plus its linked dividend workbook were retained with local SHA-256 hashes. | Files provide candidate action rows. Original announcement clocks, AAPL ex-date corroboration and split completeness remain pending. No new accounting revision was created. |
| AAPL/MSFT Alpaca comparison | One read-only action request returned 32 cash dividends for each stock and one AAPL 4-for-1 forward split effective 2020-08-31. The issuer histories each have 32 cash rows for 2018–2025. MSFT issuer and Alpaca ex-dates match in sequence; AAPL issuer history does not list ex-dates. | Alpaca omits record and payment dates on nine early rows per stock. Four MSFT workbook numeric cells contain `0.56000000000000005`, while Alpaca gives `0.56`; review the workbook's displayed precision and original announcements before choosing the stored Decimal amount. The pairs and exact raw response are retained locally. |
| Existing SPY issuer evidence | Local review artifact has 40 distinct ex-dated rows from 2016-03-18 through 2025-12-19; each has amount, payment date and availability. The retained issuer workbook SHA-256 is `4add18439e505ba6c114bea5d352ac68b1ea5420bc99abdf2e21500dd6f1faa2`. | Existing reviewed SPY revision can be reused. This local consistency check does not add a new issuer or guarantee source completeness. |

The SEC requests an identified User-Agent with a contact email for scripted
downloads; the supplied contact was used only in request headers and is not
stored in these documents. The BLS archive pages are not guaranteed to be
untouched first versions: nine explicitly describe reissues/corrections. A
current BLS API series would also expose later revised values. Do not create
`original_content_hash` events or approve coverage until the selected metric
in each release has been compared with its contemporaneous version and any
reissue notice. An HTTP 403 is an access barrier, not evidence that the source
does not exist. No app database, running container, or existing dataset was
changed by this pilot.

The pilot has produced raw SEC metadata and BLS archive files, with source URLs
and hashes, under ignored `.local/primary-source-pilot/`. Next compare
each normalized row to the original page/document and test the exact app import
contract. Expand to every release/filing/action in 2018–2025 only after sample
qualification. A source's absence of an event must be established from declared
coverage rather than represented by an invented zero row.

## 1. SEC EDGAR filing events

The [SEC submissions API](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
is public and keyless. A company's current submissions JSON includes recent
filings and links to older filing-history files. A filing accession identifies
the original 8-K and its exhibits. For example, this
[AAPL 2020 8-K filing-detail page](https://www.sec.gov/Archives/edgar/data/320193/0000320193-20-000008-index.html)
lists acceptance at **2020-01-28 16:30:40 Eastern**, identifies the 8-K and
exhibit, and distinguishes the report date from acceptance. That single example
is a format check, not coverage evidence. The
[SEC's timestamp guidance](https://www.sec.gov/about/webmaster-frequently-asked-questions)
says filing content often appears one to three minutes after acceptance and
does not provide an exact first-public timestamp. A daily research rule can
use a documented next-session availability policy; any intraday rule needs
stronger first-seen evidence or a sufficiently conservative delay.

Proposed row mapping: stable `event_id` from accession plus document/version;
`symbols=["AAPL"]`; category `sec_8k`; title and a short, source-grounded tag;
source URL and content hash. Keep the original filing and each later amendment
separate. Use the earliest **evidenced public availability** for `published_at`
and a conservative `available_at` at or after it. Acceptance time is useful
evidence but should not automatically be treated as the instant the document
was retrievable. A 10-K's fiscal-period end is never its availability clock.
Human review is needed for any semantic tag such as earnings, acquisition or
product-related event; an 8-K form alone does not establish sentiment.

For automated collection, identify the client in the User-Agent and follow the
[SEC's fair-access guidance](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data),
including its current 10-requests-per-second maximum. Do not scrape at an
unbounded rate or send SEC data directly to the browser.

## 2. BLS Employment Situation releases

The [BLS archive](https://www.bls.gov/bls/news-release/empsit.htm) provides
original monthly PDF releases across 2018–2025. For example, the
[January 2018 release](https://www.bls.gov/news.release/archives/empsit_02022018.htm)
states an embargo until **2018-02-02 08:30 Eastern** and reports the then
published nonfarm payroll change and unemployment rate. The release clock is
different from the January reference period. The archive itself warns that
later releases can revise data. The [historical schedules](https://www.bls.gov/bls/archived_sched.htm)
are a cross-check on planned release dates; the dated original document is the
source for the release and its values.

Use one event per original public release. Map the release clock to
`published_at`, `available_at` and `details.release_at`; record
`details.reference_period`, exact units and the original `details.actual`.
Choose a single metric per event, or distinct event IDs for payrolls and
unemployment. Do not calculate a surprise unless an independently sourced
**pre-release consensus and its availability time** exist. If a scheduled
release was delayed, omitted or later corrected, preserve that fact rather than
substituting a current BLS series value. The archive explicitly lists an
unpublished October 2025 Employment Situation release; the 2018–2025 coverage
manifest must represent that absence accurately.

BLS says its publications are generally [public domain](https://www.bls.gov/opub/copyright-information.htm),
apart from previously copyrighted images and illustrations. Keep attribution
and the original release URL in every normalized event.

## 3. Issuer dividend and split records

For SPY, the existing [source review](corporate-action-source-check.md) already
reconciled all 40 issuer dividends in 2016–2025, matched dated pre-open USD
announcements, reviewed split evidence and created a new immutable combined
revision. The [State Street historical distribution workbook](https://www.ssga.com/us/en/intermediary/resources/documents/etf-dividend-distributions)
supplies amounts and ex/record/payment dates; it did not by itself supply
historical announcement clocks. This work should be reused, not repeated or
silently replaced.

For the first Nasdaq-listed stocks, [Apple's dividend history](https://investor.apple.com/dividend-history/)
provides declared, record, payable and **unadjusted** per-share amounts; its
[investor FAQ](https://investor.apple.com/investor-relations/faq/default.aspx)
identifies the 2020 four-for-one split. A dated
[Apple SEC exhibit](https://www.sec.gov/Archives/edgar/data/320193/000032019320000060/a8-kexhibit991q3202062.htm)
is an example of an original announcement. The current dividend table does
not alone establish every historical announcement clock or all ex-dates.
[Microsoft investor relations](https://www.microsoft.com/en-us/investor/dividends-and-stock-history)
is a candidate issuer history for a second stock. These are source candidates,
not completed AAPL/MSFT action reviews.

For each symbol, reconcile the issuer's original declaration, ex-date,
per-share USD amount, payable date and split effective ratio with a second
source such as the already available Alpaca corporate-action response. Check
the raw-price convention before importing; adjusted prices plus separate
actions would double-count. Treat missing fields or disagreement as review
findings. A symbol's full accounting dataset also requires its own raw daily
prices and historical USD/SGD policy; action records alone cannot run it.

The current pilot paired issuer and Alpaca rows by their chronological quarter
sequence and kept every pair in
`.local/primary-source-pilot/issuer-action-candidate-reconciliation.json`.
This is a candidate comparison, not a proof that no rows were omitted by both
sources. In particular, AAPL's issuer table does not itself verify Alpaca's
ex-dates. Dated company announcements and a separate split-coverage review
are still required before creating a reviewed AAPL or MSFT combined revision.

## Import and review gate

The ignored root `.env` now contains `DATA_SOURCE_CONTACT_EMAIL`. Future source
collection tooling should read this setting when forming an identified
User-Agent such as `TradingLabResearch/0.1 <contact email>`, rather than embedding
an address in scripts. `.env.example` documents the blank setting. Existing app
adapters do not consume this setting yet. No running service was recreated to
load it; the current source artifacts were collected by separate local research
processes.

The app already accepts typed event JSON/CSV through **Strategy sources** and
an immutable review child revision. `HistoricalEvent` requires a source URL,
original content hash, publication/availability clocks and derivation. BLS
releases use `EconomicDetails`; a filing can use a sourced general event until
a more specific event contract is justified. Existing corporate actions belong
in a combined accounting dataset, not in a stand-alone strategy event feed.
The review needs declared coverage, sample source-to-row comparisons, amendment
handling, and a note explaining any conservative clock policy. Only a reviewed
revision can be bound to a run.

**No new keys are needed for this pilot.** SEC and BLS public access require
no API key; issuer public pages require no known key. Existing Alpaca keys can
be used for action cross-checks. No new real-data backtest or event-driven
performance is claimed by this source assessment.

## Next steps and remaining inputs

1. **BLS field extraction completed.** The linked follow-up report records 190
   candidate payroll/unemployment events, exact units, table reconciliation,
   field-specific correction review and period exclusions. Explicit approval of
   coverage and the assumed delivery lag is pending.
2. **SEC document review completed.** Original archived submission bodies,
   embedded documents, literal item tags and both amendment links are checked.
   The candidate uses a declared next-session-close proxy; precise first-public
   timing remains unverified.
3. **Finish equity action accounting.** Find dated AAPL/MSFT announcements,
   corroborate AAPL ex-dates, review split completeness and resolve the four
   MSFT workbook precision artifacts. Reconcile missing Alpaca dates with the
   issuer, then assemble each symbol's raw prices, reviewed actions and FX into
   a new combined revision.
4. **Exercise the existing import path.** Validate candidate JSON/CSV, import
   unreviewed revisions, inspect the review evidence, and create eligible child
   revisions only when their declared coverage is supported. A later deployment
   step requires access to this project's app without changing other services.
5. **Verify source-driven strategies.** Use reviewed streams in published
   strategy versions, replay 2018–2025 sequentially, repeat exact runs and
   independently compare selected decisions, fills and account calculations.
   Current source collection has not demonstrated this real-data acceptance.

No additional key is currently needed for these steps. Pre-release consensus
would be needed for economic-surprise rules; exact original document
availability would be needed to certify precise intraday reactions. Broader
news, analyst ratings, sector histories, Fear & Greed and Congress disclosures
remain later source projects. Complete intraday source coverage is also still
pending if a strategy requests timed intraday execution.
