# AAPL/MSFT accounting and source import — 2026-11-06

**Later acceptance:** [13 real cases and 13 exact repeats](real-equity-acceptance-2026-11-06.md)
now demonstrate backtesting with these inputs. The no-new-backtest statements
below describe this earlier source-import phase.

Status: **reviewed accounting dataset and reviewed BLS/SEC source revisions
imported through the existing deployed HTTP endpoints** on loopback port 18080.
No application code, engine, container or existing completed result was changed.
This completes the requested accounting-source review and import/review phase
under the explicit research availability policies below. No new backtest or
strategy performance is claimed.

## Retained application revisions

| Revision | ID |
| --- | --- |
| Raw AAPL/MSFT daily prices, retained unreviewed | `2ee5bb52-6d0f-4799-958d-245c0076b6ff` |
| Reviewed AAPL/MSFT/SPY accounting dataset | `526cf606-bbff-4d89-8b43-00eeaa5fc16f` |
| Reviewed BLS employment stream, final NY coverage | `6f765c92-71a7-45b3-a5c3-1641c08d8a3a` |
| Reviewed SEC filing stream, final NY coverage | `59bbf500-1a59-4835-a69f-ab7d4a8a4a34` |

Accounting dataset content hash:
`bc123cb86fd083ab04555343158ec4608a527d72cb9077ef9f9bf19f116f5db7`.
All imports were exported and checked against the actual schema and content-hash
functions. Repeated imports returned the same immutable revision IDs. Raw event
parents remain unreviewed; eligible source reviews are new child revisions with
parent hashes and explicit notes.

## Accounting evidence and source discrepancies

- **7,542 raw SIP daily bars:** 2,514 each for AAPL, MSFT and SPY over 2016–2025,
  with no required exchange-session gaps. The earlier SPY bars are reused
  unchanged. Years 2016–2017 support indicator warm-up for 2018 decisions.
- **2,494 USD/SGD observations:** the reviewed SPY ALFRED reference-rate history
  is reused, including its original availability corrections and explicit
  14-day age policy. Opening, closing and decision-clock coverage passes for
  the full 2018–2025 profile. It is not executable intraday FX.
- **121 actions:** 40 dividends per symbol plus AAPL's four-for-one split,
  effective for trading on 2020-08-31. No other split was identified in the
  reviewed sources over this interval.
- All 40 AAPL dividend amounts and issuer record/payment dates match original
  SEC earnings exhibits. A separate [published dividend history](https://www.slickcharts.com/symbol/AAPL/dividend)
  matches all 40 Alpaca ex-dates/payment dates. That publisher's adjusted,
  rounded amounts are deliberately excluded; raw amounts come from Apple.
- All 40 MSFT dividends match dated original company announcements and issuer
  ex/record/payment history. Alpaca's missing early record/payment dates are
  supplied from issuer evidence, with every source preserved.
- Four MSFT workbook numeric cells serialize `0.56000000000000005`. The
  [original announcement](https://news.microsoft.com/source/2020/09/15/microsoft-announces-quarterly-dividend-increase-3/)
  and subsequent declarations explicitly state USD **0.56**; this original
  nominal amount is used, with the workbook discrepancy retained in the review.
- For the August 2023 MSFT ex-date, the workbook gives declaration on June 16
  while the [original announcement](https://news.microsoft.com/source/2023/06/14/microsoft-announces-quarterly-dividend-20/)
  says June 13 and its migrated page is dated June 14. All three are recorded;
  modeled availability uses midnight New York after the latest date, June 17.
- Issuer FAQs corroborate split histories. Raw versus split-adjusted Alpaca
  comparisons over all 5,028 AAPL/MSFT bars show only the recorded AAPL 4:1
  factor, with matching adjusted volumes. Price differences are at most
  USD 0.005 from vendor rounding. Adjusted bars are used solely for this
  cross-check and never for execution or portfolio accounting.

Microsoft's investor-news archive omitted relevant links and contained five
broken announcement links. Located original company pages, plus the company's
distributed original release for one missing page, close those gaps. The
retained evidence records the broken URLs and canonical replacements.

## Availability and completeness policies

These are bounded, explicitly recorded research policies, not certifications of
original intraday delivery latency:

| Input | Retained policy |
| --- | --- |
| Daily prices | Current revised raw SIP bars; completed-bar availability assumed at 20:15 New York; decisions at 20:30 |
| USD/SGD | Existing reviewed ALFRED initial-release reference policy, maximum age 14 days |
| AAPL actions | Original matching SEC exhibit; availability delayed to the next full exchange session's close after SEC acceptance, always before the effective open |
| MSFT actions | Original issuer dates/amount; midnight New York after the latest original declaration, workbook declaration or migrated-page date, always before the effective open |
| BLS events | Reviewed original headline fields only; five-minute post-release-header delivery assumption; October 2025 absence explicit; January 2026 release excluded |
| SEC events | Filing presence/form and literal item tags only; next-session-close publication/availability proxy after acceptance; amendments remain separate later events |

Eligibility applies to the declared source scope. It does not establish all
company news, analyst reports, sector histories or exact historical first-public
times. Split/coverage review combines available source evidence and is not a
guarantee that every vendor is complete.

## Actual HTTP and chronology checks

The first deployed readiness check found that the original event candidates'
UTC year-end cut off New York's final evening decision. New raw/reviewed source
revisions declare coverage from **2018-01-01 00:00 New York through 2025-12-31
23:59:59.999999 New York**. The observations are identical to their predecessor
revisions. Both previous raw and reviewed revisions remain intact.

The existing HTTP workflow demonstrated:

- Accounting import, export and duplicate-import identity.
- Event raw import, explicit review, eligible child lineage and unchanged parent
  exports, including the coverage correction through new revisions.
- **335 real reviewed-event visibility pairs:** hidden immediately before their
  modeled availability, visible at that clock.
- Full 2018–2025 AAPL/MSFT daily-profile readiness with both reviewed streams.
- Rejection of unreviewed source revisions and rejection of sector-dependent
  selection without reviewed historical classifications.
- Preservation of all **38 pre-existing completed result hashes**, as well as
  all original dataset/source rows. No new backtest was scheduled.

The readiness diagnostic uses a saved profile and an unpublished configuration
solely to exercise data requirements; it is not a proposed or accepted trading
strategy. Its passing readiness result does not imply profitable performance.

The targeted backend source/financial regression suite passed **14 tests**;
backend Ruff passes. Exact rerunning of the accounting assembler reproduces the
payload and review hashes. No browser import, new restart/persistence cycle or
new real strategy performance acceptance was performed in this phase. The
successful deployed HTTP calls supersede the earlier native-TestClient transport
block for these import endpoints; that native harness itself was not repaired.

Private evidence is under ignored `.local/company-intake-20261106/`: original
files and hashes, action review, combined payload, preflight, HTTP receipts,
before/after inventories and result hashes, source-coverage predecessors,
deployed verification and exact-regeneration report. Credentials remain in
server environment configuration.

## Next use

In Market data, select the reviewed AAPL/MSFT/SPY dataset. Profiles can allow
AAPL and MSFT with SPY as benchmark, using the reviewed 14-day reference-FX
policy. Strategy sources contains the final reviewed BLS and SEC revisions;
select those revisions when a strategy requires their streams. The source
readiness checks still apply to every selected profile/configuration.

Next acceptance work is real sequential backtesting with these frozen inputs,
recording every strategy version and independently reconciling selected trades.
The longer-term [requested-company onboarding workflow](company-onboarding.md)
builds on this process without making AAPL/MSFT a fixed tradable universe.
