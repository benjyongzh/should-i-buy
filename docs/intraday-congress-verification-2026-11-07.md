# Intraday and Congress source qualification — 2026-11-07

Follow-up: the user confirmed personal non-commercial use. Original House indexes
and reports plus three verified public archive replays are now retained; two raw
observations pass clock checks but are not complete/approved. The
[new Congress qualification report](congress-qualification-2026-11-07.md) supersedes
the earlier access-only/use-case blocker below. Intraday scope is unchanged.

## Intraday: acquired, reconstructed and partly qualified

Using the existing Alpaca credentials, collection retrieved raw SIP one-minute
responses for **AAPL, MSFT and SPY throughout 2018–2025**. The existing adapter
aggregated complete, exchange-open-aligned 15-minute regular-session intervals.
No substitute source, forward fill or invented minute was used.

| Measured result | Count |
| --- | ---: |
| Monthly three-symbol partitions collected | 96 |
| Retained original HTTP responses/hash checks | 495 |
| Expected 15-minute intervals | 156,210 |
| Actual complete 15-minute bars | 156,183 |
| Missing intervals | 27 |
| Complete partitions with reviewed child revisions | 92 |
| Incomplete partitions retained unreviewed | 4 |

A separate standard-library Decimal checker reconstructed **every** collected
bar's OHLCV from retained raw response bytes, checked page hashes, completion and
availability timestamps, and verified that omitted intervals lack underlying
minute observations. Coverage also checks expected sessions/intervals, duplicate
identity and calendar alignment. Only complete partitions received explicit
complete-coverage attestations through the existing immutable review-child API.
Original parents remain unchanged.

| Unreviewed monthly partition | Missing intervals |
| --- | ---: |
| August 2019 | 3 |
| March 2020 | 21 |
| May 2021 | 2 |
| June 2023 | 1 |

These gaps establish missing provider observations under the complete-minute
contract, not their cause. They were not presumed to be harmless non-trading or
replaced using another bar type. Skipping those months would change the requested
experiment. The entire eight-year intraday history is therefore **not qualified**.

Eligibility is limited to declared retrospective research assumptions: **current
revised raw SIP history**, an assumed 60-second completion delay, and interval-open
full-fill execution proxies. Original publication vintages, actual executable
quotes/auction prints, liquidity and per-stock halt modeling are not certified.
The recorded clocks enforce those policies; they are not evidence of original
delivery latency. Lagged 14-day reference FX and issuer actions remain separate
reviewed accounting inputs. No revised bar is described as an original-time record.

## Actual intraday acceptance

The isolated application on 18084 imports all 96 parents and 92 reviewed children.
A January 2019 test uses all three symbols, SGD 10,000 initial capital, SGD 2.50 per
executed order,0.05% slippage, no contributions, whole shares and no leverage or
shorts. Each symbol enters once with a fixed SGD 1,000 spending budget. Decisions
occur at the completed daily decision clock; buys are eligible only from60minutes
after the next regular session opens. This is a bounded source/execution test,
not a new strategy recommendation or full-period intraday acceptance.

Primary run `1eb60d63-b352-4f7d-adea-9a4ea0457048` and repeat
`441efa58-0ee7-46b2-bd4d-ba82292c338b` have identical complete result hashes.
All three buys execute on 2019-01-03 at 15:30 UTC (**10:30 New York**), after the
prior day's 20:30 New York decision. Independent Decimal34 arithmetic checks
decision-time quantities, raw interval opens, slippage, available historical FX,
fees and every one of the 21 daily cash/equity marks.

| Symbol | Shares | Raw interval open USD | Slipped execution USD | SGD/USD FX |
| --- | ---: | ---: | ---: | ---: |
| AAPL | 4 | 143.97 | 144.041985 | 1.3668 |
| MSFT | 7 | 98.35 | 98.399175 | 1.3668 |
| SPY | 2 | 245.65 | 245.772825 | 1.3668 |

Final account value is SGD 10,212.3247484580. There are no corporate-action events
in this January test; it does not independently qualify new split/dividend cases.

Selecting the92 eligible partitions for a forced 2018–2025 request fails readiness
at an unavailable SPY interval in August 2019. Bypassing the UI and scheduling it
directly also returns 422. No full-period result or skipped-month substitute was
generated. Existing bounds remain 100 source partitions, one million rows and
200,000 execution intervals per run.

Private evidence under `.local/strategy-chat-20261107/` contains raw bytes,
monthly payloads/gap manifests, independent reconstruction, import/review receipts,
readiness rejection and the two bounded run results. No vendor archive or key is
committed. These sources are in the new test project's **Strategy sources** page;
they were not installed into any pre-existing Docker project.

## Congress: inspected, not acquired or qualified

The official [House access page](https://disclosures-clerk.house.gov/FinancialDisclosure)
and [House search conditions](https://disclosures-clerk.house.gov/FinancialDisclosure/ViewSearch)
returned 200 and were retained with hashes. The House conditions display commercial-use
restrictions. The [Senate access page](https://efdsearch.senate.gov/search/home/)
also displays use conditions in the official indexed view; direct retrieval from
this environment returned 403. No agreement was submitted, report downloaded or
access control bypassed. The 403's specific cause is not established.

**No Congress dataset is qualified.** These are concrete outstanding requirements:

1. Establish the permitted-use basis for this project: personal non-commercial
   research versus a commercial product/redistribution. A question was sent to the
   user; no answer was available at this verification stage. Availability online
   is not a declaration of unrestricted use.
2. Obtain original public-posting/first-seen evidence, historical coverage and
   amendment lineage. Transaction dates and filing dates alone cannot establish
   what a human knew at a historical decision clock. Do not manufacture a posting
   time from either date.
3. Normalize original reports with historical issuer/ticker mapping, transaction
   types, disclosed amount bounds and separate amendments, then review/import a
   new child through the existing Congress event contract. Ranges remain ranges.

The existing Alpaca/FRED keys do not solve those requirements. No additional key
was requested or subscription purchased. A suitable permitted archival export
with public-availability evidence can use the existing JSON/CSV path; its coverage
must be checked before claiming 2018–2025 Congress-driven strategies are ready.
This is a source qualification blocker, not a reason to invent disclosures.
