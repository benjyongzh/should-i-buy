# Congress canonical-ledger verification — 2026-11-08

## Verified scope

A new Congress source-review workflow reconciles the original and amended Apple
option exercise found in the earlier [bounded review](congress-bounded-review-2026-11-08.md).
It now produces an explicitly approved **bounded House filing-cohort revision**,
not a complete Congress feed. The source is exercised in a short real historical
backtest with an exact repeat and a negative control. Engine2.0.0 is unchanged;
source preparation uses its existing causal event/supersession behavior.

**276 backend tests including PostgreSQL and57 frontend tests pass.** Ruff,
formatting, TypeScript/Vite build and migrated-schema drift checks pass. Synthetic
automated fixtures are labeled and isolated from live providers. Live source,
browser and financial checks below are separate evidence. Third-party deprecation
and bundle-size warnings remain visible.

## Fresh isolated project

`trading-lab-congress-ledger-20261108` uses loopback **18090** for UI/API,
**15448** for PostgreSQL and its own volume. Port availability and all pre-existing
container identities/start times/restart counts/mounts were captured before
creation. Read-only `pg_dump` of the prior15446 project was restored only into the
new database; backup SHA256:
`3e32ff5255b50926e8404549176cebd5dbb6c2f42f55adc5ae554fa25e4c4fb8`.
The schema remains at008; existing immutable artifact storage is reused.

The new API/frontend/worker were built and started, processed actual jobs, and
were recreated with final images. The newly created database was restarted.
Ledger/approval/source/result hashes persist. All **47 pre-existing containers**
remain unchanged. All35 older18082 result hashes and all6 source18088 results are
preserved, along with25 prior conversation turns,7 version transcripts, the prior
journal and the original raw Congress revision. No homelab database or existing
service was restarted, replaced or overwritten.

## Real evidence acquisition

The application reacquired the official2022 index containing2,748 entries. Its
selected domain has exactly two Nancy Pelosi PTRs filed March1–31,2022; a third,
February28 original supports amendment reconciliation. AAPL/MSFT are the selected
symbols. All three current official PDFs match the already retained review hashes.

| Report | Role | Actual verified archived observation |
| --- | --- | --- |
| [20020515](https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2022/20020515.pdf) | Original Apple exercise | 2022-10-23 14:43:00 UTC |
| [20020561](https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2022/20020561.pdf) | March4 amendment of that exercise | 2022-03-07 20:36:50 UTC |
| [20020662](https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2022/20020662.pdf) | March21 Tesla-only report; no selected-symbol row | 2022-07-18 12:14:10 UTC |

Each accepted replay returned HTTP200, exact official PDF bytes, and matching
capture/`Memento-Datetime`. The first replay attempt for20020662 returned **HTTP500**
and established no clock. That failed response was retained. One normal retry
succeeded with matching bytes/header; no bypass or invented timestamp was used.
These are conservative observation bounds, not certified first-public releases.
The current index, signature date, notification date and Last-Modified do not
backdate an event.

All rows of the two March reports were reviewed. The March4 AAPL row and February
original describe the same spouse transaction on January21,2022:100 call options
exercised into10,000 shares at a USD100 strike, reported rangeUSD1,000,001–5,000,000.
The amendment changes the notification date from January21 to February28. Apple
issuer/ticker identity was checked against the contemporaneous
[SEC2022Q1 filing cover](https://www.sec.gov/Archives/edgar/data/320193/000032019322000007/aapl-20211225.htm).
Annotations are manual source review, not automatic PDF extraction.

## Canonical source outcome

The UI prepares two linked disclosure observations under one canonical economic
transaction. At the March7 capture, the amended version is the newest observed
filing version and supplies one explicitly classified `option_exercise` event.
The original is captured in October; it remains auditable but does not duplicate,
revert or restart that event. No exact `filed_at` time is invented.

The source uses stream **`HOUSE_PELOSI_MAR22`**, selected symbolsAAPL/MSFT, filing
domainMarch1–31,2022 and declared conservative observation coverageMarch1–December31,
2022. “Complete” applies only to the named current-index filing cohort and its
reviewed supporting originals under this observation policy. It does not assert
all real-world transactions, later-filed amendments, all Congress or first-public
history. There is no MSFT transaction row in these selected reports; that is not
a claim that no MSFT trades occurred elsewhere.

Explicit clock/inventory/identity/taxonomy acknowledgements and a review note in
the UI create a new eligible child while preserving the raw ledger and source.
Ledger: `2c1b46d2-b952-4fef-8d43-b78de7df09ea`; eligible source:
`e246f569-b173-4f78-9f70-c26da982bb81`. Prior raw revision
`8876a726-87f2-49fa-b43d-a6fa61a77f70` remains unchanged and unreviewed.

## Actual historical strategy checks

The shared test profile covers **March7–18,2022** with SGD10,000 capital,
SGD2.50 per order,0.05% slippage, no monthly injections, whole shares and the
existing14-day historical-reference-FX age policy. It uses the reviewed daily
AAPL/SPY/FX/action dataset. The test strategy buys at the next eligible open after
a visible exercise observation, sizes at95% of equity and exits after two held
sessions. This is a plumbing/causality test, not an investment recommendation or
an evaluation of a general Congress-following strategy.

| Case | Orders | Ending SGD value | Disposition |
| --- | ---: | ---: | --- |
| Explicit option-exercise category | 2 | 9,992.0733845500 | One entry and exit; loss retained |
| Identical repeat | 2 | 9,992.0733845500 | Exact full-result hash match |
| Ordinary equity-purchase category | 0 | 10,000 | Correct negative control; exercise is not a market purchase |

Primary run `efc40a0e-b7a9-45a3-8db7-6135679b0f13` and repeat
`55a7da29-7443-4344-ac19-27f2b2ae8181` share result SHA256
`8d9ac60a7d7545920dc1cecb62a429e6adf84e139e30cdb5d175b74750b09a2c`.
The negative control is `653d8bbe-6f4f-4dcc-ac7e-4f8db2b34397`.

Independent stdlib/Decimal34 reconstruction, without application imports, matches
**40 daily marks,20 decisions,4 fills including SPY references, and2 strategy
ledger entries**. It checks historical FX, costs, next-open order timing, sizing,
nonnegative cash, cash/SPY references and period calculations. Selected fills:

| Date / side | Shares | Raw USD open | Executed USD price | SGD/USD reference | Fee SGD | Cash after SGD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| March8 buy | 44 | 158.82 | 158.899410 | 1.3609 | 2.50 | 482.6668889640 |
| March11 sell | 44 | 158.93 | 158.850535 | 1.3609 | 2.50 | 9,992.0733845500 |

The reference FX observation is dated March4 and available under the reviewed
policy at March8 midnight New York time, before the buy open. It is a lagged
reference rate, not an executable conversion quote. Money tolerance is1e-18SGD,
return tolerance1e-12. No dividend/split became effective during this short window;
full-period action accounting remains covered by earlier acceptance.

Actual application evidence previews immediately before/at the March7 bound show
0→1 visible observations; the October original capture leaves the count at1.
A **2018–2025** schedule using this cohort rejects with422 for missing event
coverage; no invalid financial run is queued. The existing full-period funded RSI
baseline was also replayed without Congress inputs and exactly reproduces its
prior hash `5c441348fc9a4f77ba8ffcd3b15fbf974822fd7c73be3d352330938fd4f403a9`.

## Adversarial checks and remaining limits

Tests cover later-captured originals, metadata-only changes, numerically equal
amount formatting, causal economic corrections and stable historical prefixes,
two distinct identical-looking gifts, invalid/branched/cyclic/disconnected lineage,
unknown clocks/taxonomy/amounts, index/date/identity mismatch, synthetic-to-real
relabeling, oversized cohorts, HTTP failures, mismatched replay bytes/Memento
headers, raw/eligible lineage, explicit review and idempotent submission. Legacy
Congress payloads preserve serialization without newly introduced null fields.

Ten actual browser assertions pass for preparation, review gating, taxonomy,
raw preservation, audit timeline and mobile layout; no runtime errors or page
width overflow were observed. PostgreSQL rejects update/delete of the actual
ledger, approval, raw source and eligible source in eight explicitly rolled-back
attempts. Required backend tests include migration/drift and immutable artifact
checks. The independent audit verifies hashes and prior deployment preservation.

Raw bytes/receipts, one failed replay, review annotations, browser screenshots,
source hashes, all runs and independent reconciliation remain private under
`.local/congress-ledger-20261108/`; no keys or runtime archive is committed.

**Still pending:** broader filer/company/date coverage; multi-index cross-year
amendments; original first-public clocks; automatic trustworthy PDF interpretation;
Senate access; and a complete2018–2025 Congress dataset. Company onboarding does
not treat this cohort as general Congress capability. The four incomplete
intraday months, broad original-version news/ratings and historical sector inputs
remain separate source work. No new key, paid subscription, live broker execution
or model training was introduced. See the [workflow](congress-source-workflow.md).
