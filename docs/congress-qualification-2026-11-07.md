# Congress qualification follow-up — 2026-11-07

The user explicitly confirmed **strictly personal, non-commercial use and no
application distribution**. This resolves the earlier use-case clarification.
It does not turn transaction/filing dates into historical public timestamps or
establish complete source coverage. No new API key or subscription was needed.

## Acquired and inspected

The official [House disclosure download page](https://disclosures-clerk.house.gov/FinancialDisclosure)
was navigated normally to resolve its actual archive links. Eight original annual
ZIP/XML indexes for 2018–2025 were retained with URLs and hashes:

| Evidence | Observed count |
| --- | ---: |
| Index entries, all filing types | 23,139 |
| PTR index entries (`FilingType=P`) | 4,976 |
| Original Nancy Pelosi PTR PDF samples | 16 |
| Readable sample PDFs | 16 |
| Sample PDFs mentioning Apple | 5 |
| Sample PDFs mentioning Microsoft | 0 |

The zero Microsoft count describes these samples only, not an absence of Microsoft
disclosures. The annual indexes provide filer/name, district, filing type/year/date
and document ID; they do not provide ticker transactions or first-public clocks.
The retained indexes are current downloads, not original index vintages.

## Public-observation bounds actually verified

Internet Archive availability metadata led to three PDF replays. Each replay
returned 200, its `Memento-Datetime` matched the capture timestamp, and its SHA256
matched the corresponding current official PDF. These establish conservative
observed-public bounds for those exact documents, not certified first disclosure.

| House document | Transaction(s) inspected | Verified public observation |
| --- | --- | --- |
| [20018011](https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2021/20018011.pdf) | Spouse AAPL call-option purchase on 2020-12-22 | 2022-03-22 19:21:35 UTC |
| [20020208](https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2022/20020208.pdf) | Two charitable stock contributions on 2021-12-30, reported with `S (partial)` codes | 2022-01-14 11:08:08 UTC |
| [20020515](https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2022/20020515.pdf) | Spouse AAPL option exercise into shares on 2022-01-21 | 2022-10-23 14:43:00 UTC |

The bounds can be much later than when a person first could have learned of a
transaction. They are deliberately not moved back to the trade, filing, signature
or HTTP Last-Modified timestamp. An archive's closest capture can also fall after
the requested lookup date; the actual returned/replayed timestamp is what matters.
No signal is assigned before the evidenced bound.

## Normalization findings and retained raw candidate

Five AAPL candidate groups were reviewed against source text. They include a call
purchase, two charitable-transfer rows, two option exercises and an equity sale.
The following distinctions prevent false strategy signals:

- A call-option purchase is not an ordinary equity purchase.
- Exercising an older option is not a newly initiated discretionary market buy.
- A reported sale code may describe a charitable contribution. The two contribution
  rows must not be deduplicated just because date, asset and amount range match.
- The report owner is the spouse, not automatically the named reporting Member.
- Disclosed amounts remain ranges, not exact trade values or execution prices.

Two supported purchase/exercise observations with verified public bounds were
imported through the existing typed Congress contract as raw revision
`8876a726-87f2-49fa-b43d-a6fa61a77f70` in the new 18086 project. Categories remain
`call_option_purchase` and `option_exercise`; neither is silently tagged as an
ordinary stock purchase. Their disclosed ranges are USD 250,001–500,000 and
USD 1,000,001–5,000,000. `filed_at` remains unknown rather than guessed from a date.
The charitable rows stay in the evidence packet because the existing transaction
enum does not represent charitable transfers truthfully. Untimed rows were not
forced into timestamp-required event records.

**The revision is unreviewed and incomplete. No eligible review child was created.**
Four actual application checks immediately before/at both observation bounds
confirm 0→1→2 visible records. Strategy readiness rejects the raw revision. These
are source/clock integration checks, not a Congress-driven financial backtest.

## Remaining qualification work

Complete selected-company/filer coverage, stable historical issuer mapping,
amendment lineage and an explicit instrument/action taxonomy still require review.
Thousands of index entries are not thousands of normalized transactions. There
is no full 2018–2025 House-and-Senate archive qualified for strategies, and the
earlier direct Senate 403 observation is not resolved by this House exercise.

Next collection should process a defined filer/company domain with all applicable
PTRs and amendments, recording exact evidence and unavailable periods; it should
not approve a sparse positive sample as complete. Additional archival bounds may
be accepted conservatively only after response/content verification. Genuine
unknown clocks and coverage remain blockers. This phase introduces no new source
parser or simulation behavior that silently treats options/transfers as ordinary
equity trades.

Original ZIP/XML/PDF/replay bytes, extraction version, candidate facts, use basis,
headers/hashes, typed raw import and causal checks are retained privately under
`.local/conversation-history-20261107/congress/`. No raw disclosure archive or key
is committed. See [earlier source scope](intraday-congress-verification-2026-11-07.md)
and [current verification](verification.md).

## November8 bounded follow-up

The [March2022 Pelosi/AAPL/MSFT review](congress-bounded-review-2026-11-08.md)
now retains all eleven2022 PTRs and verifies both in-domain PDFs against exact
archive replays. It identifies the March4 Apple row as an amendment of the
earlier January21 option exercise, not another stock purchase. Its earlier
archive bound must be reconciled with the original report's later evidenced
bound. No eligible child or complete Congress source was approved.

## Canonical cohort qualification follow-up

The [later November8 ledger workflow](congress-source-workflow.md) now represents
option exercises and charitable transfers explicitly, retains canonical identities,
and prevents a late-captured original or metadata-only amendment from producing
another signal. A narrow March2022 Pelosi filing-cohort source is approved and
passes a short real test/repeat and ordinary-purchase negative control. Earlier
raw revisions remain unchanged. This does not qualify the full2018–2025 House/
Senate archive. [Actual evidence](congress-ledger-verification-2026-11-08.md).
