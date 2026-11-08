# SEC and BLS source verification — 2026-11-06

**Later follow-up:** [deployed issuer/source verification](company-intake-verification-2026-11-06.md)
records actual HTTP import and source approval, corrected New York coverage,
and the reviewed AAPL/MSFT accounting revision. The candidate-stage status below
is retained as the earlier evidence; its deployment blockers are superseded
where the follow-up explicitly demonstrates success.

**Completed:** BLS headline extraction/correction review and SEC submission/item/
amendment review for the selected sources. Both produce schema-valid, explicitly
**unreviewed candidate JSON exports**. Source approval, deployment import and
real strategy acceptance are separate remaining steps. No application code,
running service or existing dataset was changed.

## BLS Employment Situation

The retained archive contains 96 releases: 95 for reference months in 2018–2025
and the December 2017 release published in January 2018. The export has **190
events from the 95 releases published during 2018–2025**. The December 2025
report, released January 9, 2026, is excluded. BLS explicitly says the October
2025 release was not published; no replacement observation is fabricated.

Each release supplies two fields, kept in separate categories in stream
`BLS_EMPLOYMENT`:

| Category | Value and units | Checks on every retained release |
| --- | --- | --- |
| `bls_payroll_change` | Monthly seasonally adjusted nonfarm change, **thousand jobs** | Summary B equals B-1 monthly change and B-1 current minus prior employment levels |
| `bls_unemployment_rate` | Seasonally adjusted headline unemployment, **percent** | Summary A equals the current seasonally adjusted A-1 rate |

All **288 numeric reconciliations** passed. Exact tabular figures are retained:
for example, the April 2020 employment change is **−20,537 thousand jobs**,
not the rounded −20.5 million used in the narrative headline. This compares
different tables within each release, not two independent providers.

Nine archive pages explicitly note reissues: eight releases in February–September
2020 and the May 2025 release. The 2020 notices identify household occupation
detail and explicitly exclude the official unemployment rate; the May 2025
notice likewise says headline unemployment was unaffected. Payrolls belong to
the separate establishment survey. The selected fields therefore remain usable
as original-release headline observations under this documented field-level
review. Later correction text, detailed household estimates and later revisions
are not exposed as original-time strategy inputs. This finding does not certify
every field in those archived documents.

The release header supplies its 08:30 Eastern embargo/release clock. Candidate
`available_at` applies an **assumed five-minute delivery lag**. Exact historical
retrieval latency or rare publication delays have not been independently
certified; this remains a research assumption for explicit approval. All events
have original source URLs and retained archive-page hashes. No consensus or
economic surprise is supplied.

Sources: [BLS archive](https://www.bls.gov/bls/news-release/empsit.htm),
[March 2020 release and correction notice](https://www.bls.gov/news.release/archives/empsit_04032020.htm),
[April 2025 release and correction notice](https://www.bls.gov/news.release/archives/empsit_05022025.htm).

## SEC AAPL/MSFT filing events

Downloaded and hashed **145 complete archived submission-text files** covering
68 AAPL and 77 MSFT 8-K/8-K/A filings in 2018–2025. They contain **2,050 embedded
documents**, including primary filings, exhibits and generated supporting files.
Every accession, form, filer CIK and acceptance timestamp agrees with the SEC
submissions inventory. All **268 listed item codes** were found as literal item
headings in the corresponding primary documents.

For 36 submissions the header's public-document count differs from the embedded
block count. Their filing indexes were separately retained and checked: **all
283 indexed file rows are present in the retained submission bodies**. The count
is not used as a completeness shortcut or evidence of an absent corporate action.
The archive snapshot is not a certification that every generated SEC artifact is
an untouched first version.

The candidate stream `SEC_FILINGS` exposes filing presence, form and literal
`sec_item_*` tags. For example, `sec_item_2_02` identifies the source's Results
of Operations item. No sentiment, numeric earnings interpretation, geopolitical
classification or historical sector inference has been generated.

Both amendments have explicit original links in the review artifact:

| Amendment | Original | Scope and treatment |
| --- | --- | --- |
| AAPL `0001193125-18-154948` | `0001193125-18-154515` | Corrects a litigation objection deadline; retained as a separate later event |
| MSFT `0001193125-24-062997` | `0001193125-24-011295` | Updates the cybersecurity incident; retained as a separate later event |

Neither amendment replaces all information in its original filing. No later
wording is backfilled into the earlier filing event. The links were checked
against each amendment's description of its original filing.

SEC acceptance is not exact public availability: the
[SEC FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions)
says first-public timestamps are absent and documents commonly appear after
acceptance. The candidate therefore models **both publication and availability
at the next exchange session's close after the acceptance date**. This is an
explicit conservative research proxy, not an assertion of actual delivery time.
Exact first-public timing and precise intraday reaction remain unverified.

Sources: [SEC API description](https://www.sec.gov/search-filings/edgar-application-programming-interfaces),
[Apple amendment](https://www.sec.gov/Archives/edgar/data/320193/000119312518154948/d563832d8ka.htm),
[Microsoft amendment filing index](https://www.sec.gov/Archives/edgar/data/789019/000119312524062997/0001193125-24-062997-index.htm).

## Validation and practical limits

- Both exports pass the actual `StrategyInput` schema. The existing import/export
  route functions retain and deduplicate them correctly in isolated in-memory
  SQLite. Their exported data matches the validated inputs exactly.
- The actual engine rejects both unreviewed real sources. No eligible review
  revision was persisted, even in the isolated test database.
- Explicitly synthetic in-memory review clones passed **335 before/at availability
  pairs**, future-record mutation checks and invalid-clock rejection. These are
  chronology diagnostics, not imported synthetic market history or backtest returns.
- Repeating both extractors produces identical candidate/review file hashes.
  All retained SEC submission and checked-index hashes were revalidated.
- Native HTTP `TestClient` stalled during lifespan startup; the bounded attempt
  was stopped. HTTP/browser import and deployed PostgreSQL retention of these
  new sources remain unverified. Route-function checks do not certify transport.

Private artifacts under ignored `.local/primary-source-pilot/`:

| File | Purpose |
| --- | --- |
| `bls-employment-unreviewed.json` | Candidate JSON for the existing Strategy sources import |
| `bls-field-review.json` | Every extracted figure, source hash, comparison and correction note |
| `sec-filings-unreviewed.json` | Candidate filing-presence/item-tag JSON |
| `sec-document-review.json` | Header, document hashes, item checks, amendment links and modeled clocks |
| `sec-index-reconciliation.json` | Evidence for the 36 count differences |
| `source-verification.json` | Actual schema, retention and chronology check results |
| `source-reproducibility.json` | Exact regeneration and source/script hashes |

Next: explicitly review the documented availability assumptions and source
coverage, then use the existing application import/review flow. New real
event-driven strategy performance is still unverified.

## Universe scope

AAPL and MSFT are the initial issuer test bed. Each additional tradable equity
requires its own raw-price, FX, action and identity coverage review. These can
be added in bounded groups. This pilot does not qualify every US equity, an
entire exchange, or historical index constituents; a multi-equity research
universe also needs historical membership and delisted-security handling.
