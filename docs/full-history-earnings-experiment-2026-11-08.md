# Full-history earnings experiment — executed 8 November 2026

[Visual report and flowchart](earnings-experiment.html) · [Data workflow](data-workflow.html)

## Demonstrated scope

AAPL/MSFT quarterly releases cover **2018–2025**, with 32 releases per issuer.
All **64 issuer pages returned HTTP 200**. Each is paired with the exact original
SEC EX-99 exhibit, retained acceptance timestamp, URL and SHA256. All 128 original
bodies were rehashed. A second stdlib extractor, with no application imports,
reconciles **64 nominal revenue and 64 GAAP diluted EPS figures** against the
original tables. Negative Microsoft FY2018Q2 GAAP EPS remains **−0.82**, not
adjusted 0.96. Current quarterly columns are distinct from comparative/annual
columns and the later diluted-share-count row. No consensus or surprise is invented.

The raw revision contains **192 events**: one release-presence, one GAAP EPS and
one revenue observation per quarter. The numeric observations reuse the existing
economic-value contract with explicit company categories and USD/share or USD-million
units; this is a schema compatibility choice, not a macroeconomic classification.
The experiment uses only `earnings.release` presence, not numeric EPS/revenue.

**Timing remains an explicit research assumption.** Both modeled publication and
availability are next exchange-session **close after SEC acceptance**, following
the existing SEC research policy. `verified_public_at` remains null in retained
review evidence. This conservatively delays use but does not prove actual first
retail delivery. A new reviewed child attests only the 64 quarterly-results scope;
it does not certify all issuer announcements, all news or intraday timing. Original
SEC exhibits govern the figures; currently fetched issuer pages corroborate them.

| Immutable source | ID |
| --- | --- |
| Unreviewed original | `d2baf43d-2e34-4769-8eb2-ffa2ce7fbfb4` |
| Reviewed daily research child | `506ce625-7c89-4195-853b-83d1675b1c49` |

Reviewed source hash: `26d582da8497ad5808a63a8a13b20e8c66a9937151aee12cd62a42ee7135014a`.

## News and analyst backfill: acquired, not qualified

All **96 month queries** completed pagination. **766 successful raw response
bodies** were rehashed against byte-count/SHA256 receipts before yearly assembly.
They yielded **35,854 current-version news events**. One blank-headline row is
explicitly quarantined; its original raw response remains retained. Another
**68 older-publication records updated in a later query window** are explicitly
excluded from those publication cohorts. No title, clock or missing body is invented.

Literal, single-issuer headlines yield **1,262 analyst announcements**; **34,592**
headlines remain unresolved by this deliberately narrow extractor. Unreported
prior ratings/targets remain null. Upgrade/downgrade/price-target mentions are not
assumed to be complete ratings history. Authenticated feed access remains
`subscription`, not inferred public access.

| Year | News events | Literal analyst events | Raw pages checked |
| --- | ---: | ---: | ---: |
| 2018 | 2,050 | 83 | 47 |
| 2019 | 2,162 | 112 | 49 |
| 2020 | 2,911 | 178 | 66 |
| 2021 | 4,760 | 117 | 101 |
| 2022 | 5,510 | 113 | 116 |
| 2023 | 6,840 | 258 | 143 |
| 2024 | 5,934 | 194 | 125 |
| 2025 | 5,687 | 207 | 119 |

Sixteen yearly raw revisions are imported through the existing UI/API. All remain
**unreviewed and incomplete**. Query exhaustion is not a certificate of original
article vintages or comprehensive retail news: the API uses update windows, can
return revised text, and a historically created article updated outside its cohort
may be absent. No such source is used in this earnings experiment.

## Controlled experiment and actual outcome

The baseline enters when **SMA20 > SMA50**, exits when **SMA20 < SMA50**, and sizes
new positions to 50% of equity, capped by cash and existing risk limits. At most
two positions, whole shares, no additions, no leverage or shorts. This is a
trend-state rule, not a crossing-only trigger.

A prospective plan was registered before candidate publication. The streamed
strategy conversation requested exactly one change: entry also requires at least
one symbol-scoped `earnings.release` event over **1,440 minutes**, `public_only`.
Both strategies retain identical daily-close execution policies, dataset, profile
and reviewed earnings source binding. Orders execute at a strictly later eligible
open. Exits and sizing are unchanged. Earnings become visible only after their
modeled clocks; release-day EPS cannot enter earlier decisions.

Shared profile: SGD 10,000 initial capital, **zero monthly contributions**, SGD 2.50
per executed order, 0.05% slippage, no spread/commission/FX markup, daily
2018-01-01–2025-12-31, AAPL/MSFT universe and matching SPY benchmark. Historical
initial-release reference USD/SGD uses the existing maximum-age 14-day policy.
Zero contributions is an experiment control; monthly funding capability remains
available independently. Raw bar histories include 2016–2017 indicator warm-up.

| Result | Baseline | Earnings-gated | SPY reference | Cash reference |
| --- | ---: | ---: | ---: | ---: |
| Ending account, SGD | 29,819.54 | 23,302.66 | 25,729.40 | 10,000.00 |
| Total return | +198.20% | +133.03% | +157.29% | 0.00% |
| Maximum drawdown | −32.19% | −19.49% | −30.92% | 0.00% |
| Executed orders | 89 | 59 | 1 | 0 |

| Continuous account period | Baseline return | Earnings-gated return |
| --- | ---: | ---: |
| 2018 | +11.09% | +11.98% |
| 2019 | +50.34% | +19.19% |
| 2020 | +34.11% | +29.05% |
| 2021 | +19.13% | -3.64% |
| 2022 | -25.32% | -2.54% |
| 2023 | +21.49% | +18.76% |
| 2024 | +14.14% | +9.62% |
| 2025 | +7.93% | +10.65% |

The immutable journal conclusion is **mixed**: less drawdown and turnover, lower
ending equity. The candidate trails SPY in this sample; the baseline beats it.
The earnings gate still loses in 2021 and 2022. All eight years are retained,
including negative periods; annual reports do not reset positions or cash.
Repeated full-period tuning remains **in-sample development**, not evidence of
future outperformance. No search for a winning result was performed.

The LLM returned a supported proposal through **199 SSE delta events**. Structural
JSON comparison confirms only the declared entry gate changed. Explicit acceptance
edited the draft; explicit publication created version 2. Its read-only transcript
retains the exact request in the strategy's single permanent conversation. The
candidate and exact repeat have identical result hashes. The verification harness
initially compared JSON key order and stopped before acceptance; structural
comparison corrected this harness issue without changing the proposal.

- [Research journal](http://127.0.0.1:18094/research?study=2be9989e-2b16-40b9-a135-4f4e8c284e26)
- [Daily account comparison, decisions and benchmarks](http://127.0.0.1:18094/compare?runs=75b4b710-87e7-493b-93dd-d940603aaa48,c6261cf8-113d-4096-a08d-cda8ab8f8de2,b83dddb9-2e85-42ee-8c48-46ec9e00b2b0)
- Baseline run: `75b4b710-87e7-493b-93dd-d940603aaa48`
- Candidate run: `c6261cf8-113d-4096-a08d-cda8ab8f8de2`
- Exact repeat: `b83dddb9-2e85-42ee-8c48-46ec9e00b2b0`
- Strategy version 1: `b99d2cc8-6439-4994-96cd-6a6d8266b6c6`
- Strategy version 2: `f78f161a-c9c6-475e-8871-23621ef8a775`
- Dataset hash: `bc123cb86fd083ab04555343158ec4608a527d72cb9077ef9f9bf19f116f5db7`
- Frozen profile hash: `c8ed088e5e04553160dce15aea112717c796e840785abeedfce367fdf0fc7421`

## Independent checks and test evidence

A stdlib-only Decimal34 reconstruction imports **no Trading Lab code**. It checks
all **8,044 account marks, 8,044 strategy decisions, 150 fills, two rejected order
attempts and 308 strategy ledger entries**, across both strategies and their SPY
references. Checks cover split-aware SMA windows, earnings visibility and symbol
scope, next-open chronology, affordable quantities, costs, historical FX selection,
corporate-action entitlements/payment cash, nonnegative cash/long-only positions,
realized/unrealized P&L, drawdown, all 8 year/32 quarter/96 month period reports and
cash references. Monetary tolerance 1e−18SGD; return tolerance 1e−12. The candidate
repeat matches the entire result hash, not just ending equity.

**339 backend tests pass**, including fresh PostgreSQL migrations, causal and
immutability checks; **62 frontend tests pass**, as do Ruff and frontend build.
New adversarial tests cover EPS/share-count/annual-column confusion, negative
GAAP EPS, mismatched exhibits/issuers, duplicate/malformed news, missing coverage,
raw/candidate tampering and earnings values hidden before their declared clock.
Existing pandas/Starlette deprecation warnings and frontend bundle-size warning
remain; no test failure is waived. Engine 2.0.0 and financial simulation code are
unchanged; no material-engine-change review gate is triggered.

## Deployment defect, isolated fix and preservation

The old source catalog loads and validates every entire archive just to list its
metadata. With 230 real source revisions, one measured request takes **25.23s**.
The original-source UI test times out. During concurrent catalog/comparison/audit
requests the existing API automatically restarts once at 06:41:39 UTC and returns 502.
It recovers with its existing restart policy. No manual restart, rebuild, stop,
container replacement or existing database operation was performed. Its 1 GiB limit
makes bulk materialization a concern, but retained Docker evidence does **not**
prove OOM as the restart cause; do not report a confirmed OOM diagnosis.

The fix projects metadata and row counts **inside SQL**, avoiding all archive bodies
in the catalog response/ORM identity map. Import/review, full export, readiness and
frozen run resolution retain full schema/content-hash validation. SQL projection
and unchanged tamper checks pass on SQLite and real PostgreSQL; no schema or
financial engine change is required.

A new disposable API on unused loopback 18096 uses the same real database through
**PostgreSQL-enforced read-only transactions**, with the same 1 GiB memory limit.
All 230 catalog summaries match the retained fully validated API summaries exactly.
Two measured responses take **2.44s and 2.53s**, with zero restarts; memory observed
after the checks is 408.2 MiB, not a guaranteed peak/stress limit. Twelve actual
browser assertions pass using the existing UI and a **browser-local GET-only proxy**
to this fixed API: source rows/cutoffs/licensed filtering, explicit review gate,
read-only published conversation, concluded journal, comparison and mobile layout.
Six documentation browser checks also pass: all yearly rows and four account
series render, line toggles work, the workflow links the report, mobile layout
fits and scripts raise no errors. This is isolated verification, **not deployment
of the fix to the existing app**.
The original UI still uses its original backend and retains this catalog limitation.
The temporary API is removed after verification; existing services are left in place.

The final read-only audit confirms **all 58 pre-existing container identities**,
**all 11 prior backtests/results**, and **all 212 prior source exports** preserved.
**57 containers retain their exact original start/restart state**; the API has the
single observed automatic restart. There are now 14 completed runs and 230 source
revisions. Sixteen new news/analyst revisions and the raw earnings parent remain
unreviewed. This observed recovery verifies retention across that API restart, not
a new entire-stack deployment or database restart test. Tests use a new private
Docker network and tmpfs PostgreSQL with no host DB port; only this turn's temporary
containers/network are cleaned up. Existing homelab PostgreSQL data/ports are
not altered. General deployment success must not be inferred from passing unit tests.

## Reproduction and remaining inputs

From backend with the documented project environment, retain the exact source
receipts and explicit quarterly exhibit inventory, then use:

```sh
python -m scripts.backfill_retail_news --output /private/news
python -m scripts.prepare_historical_news --source-dir /private/news --output /private/yearly
python -m scripts.prepare_earnings_history --inventory /private/earnings-inventory.json --sec-root /private/sec --issuer-dir /private/issuer --output /private/paired
python -m pytest
python -m ruff check .
```

The earnings inventory explicitly selects issuer, accession, original SEC path/
SHA256 and EX-99 filename. Issuer `manifest.json` binds each accession to URL,
local file, HTTP status and exact SHA256. The preparer checks paths and hashes,
rejects mismatches/ambiguous statements and writes new unreviewed candidates.
These CLI helpers do not automatically approve inputs. Resume verifies original
raw bytes as well as normalized candidate bytes; a changed request requires a new
directory. Runtime originals, licensed news text, manifests, screenshots, full
results, private test credentials and audit scripts stay under ignored
`.local/retail-full-history-20261108/`, not committed application fixtures.

**No new API key was needed**: existing Alpaca and server-side LLM configuration
worked; original SEC and issuer pages require no paid key. Existing FRED/ALFRED
reference FX was reused. Contact email remains in server environment, not source.
Original-vintage news, comprehensive analyst actions, continuous insider/amendment
coverage, broader Congress public-posting/lineage evidence, historical sector
membership, full intraday coverage and a scheduled freshness process remain
separate pending qualifications. Exact retail knowledge at every historical moment
is not proven by this backtest. Do not bypass access denials or backdate current
captures. The next safe improvement experiment should be registered in the journal
with frozen controls and retained outcomes before changing another variable.
