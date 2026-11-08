# Free Congress, news-derived analyst actions and issuer earnings pilot

**Completed:** the pinned free Congress snapshot is locally retained and audited,
a bounded House/Senate slice is staged, 98 literal analyst announcements are
prepared and imported as eight unreviewed source revisions, and two issuer/SEC
earnings pairs have checked nominal figures. **No new source is automatically
approved and no new financial performance is claimed.** Engine 2.0.0 is unchanged.

The selected information boundary is a retail investor's declared sources and
access level. A reliable intermediary is acceptable. Missing public clocks,
unknown fields, incomplete coverage and amendments remain explicit; no record
is silently moved to its transaction date or converted into an ordinary stock buy.

## Congress snapshot: actual acquisition and qualification

Dataset revision: `bb5e1c4d5dd052ffe4e14def1ac6b1f25f7bc2bb`.
All **45 Parquet files**, totaling **9,085,655 bytes**, match the pinned manifest's
sizes and SHA-256 hashes. Manifest SHA-256:
`303738628ae6cdb385a7374dba595e218016e69f85db2eecacb39e9a0dfea4eb`.
An offline reader independently reproduces all advertised table counts:

| Table | Actual rows read |
| --- | ---: |
| Filing documents | 10,883 |
| Printed transactions | 187,288 |
| Consolidated event versions | 182,595 |

The local filing table matches **every one of the 6,234 document IDs** in our ten
retained official House PTR indexes, grouped by the original index/PDF year:

| Index year | Official IDs | Snapshot IDs | Missing / extra |
| --- | ---: | ---: | --- |
| 2017 support | 801 | 801 | 0 / 0 |
| 2018 | 830 | 830 | 0 / 0 |
| 2019 | 683 | 683 | 0 / 0 |
| 2020 | 733 | 733 | 0 / 0 |
| 2021 | 680 | 680 | 0 / 0 |
| 2022 | 624 | 624 | 0 / 0 |
| 2023 | 460 | 460 | 0 / 0 |
| 2024 | 451 | 451 | 0 / 0 |
| 2025 | 515 | 515 | 0 / 0 |
| 2026 support | 457 | 457 | 0 / 0 |

Calendar filing-year counts differ because reports can belong to a different
index year. Comparing those counts directly had suggested differences; document
identity against the correct index year resolves them. This is a current-index
coverage check, not proof that historical archives retain every original report.
The producer's one failed extraction remains a gap even though its filing is listed.

The bounded staging slice contains **six printed rows**: the two earlier reviewed
Pelosi Apple original/amendment observations, two Senate electronic-report rows
and two Senate paper-report rows for AAPL/MSFT. Both Pelosi source PDF hashes
match our independently retained original bytes exactly. Owner, transaction date,
issuer ticker and amount range reconcile with the prior review. Their exercise
comments are retained. The producer's `purchase` field reflects broad reported
transaction classification; our reviewed economic action is **option exercise**.
It must not become a new ordinary equity purchase signal.

Senate sample records are present in the checked snapshot, but their originals
have not been independently accessed here; the direct portal denial remains.
The [earlier code assessment](congress-dataset-assessment-2026-11-08.md) also
identified filing-day availability proxies, ambiguous consolidation and future
contributor metadata. Accordingly, every staged row retains
`producer_assumed_available_at`, sets `verified_public_at` to **null**, and has
`strategy_eligible=false`. No Congress event dataset was imported or broad source
approval created. Earlier qualified Congress revisions remain unchanged.

Reusable offline checks are in
[qualify_congress_snapshot.py](../backend/scripts/qualify_congress_snapshot.py)
and [congress_snapshot.py](../backend/app/retail/congress_snapshot.py). DuckDB
1.4.3 was installed only into the ignored pilot reader directory and used in a
disposable offline process; it is not a new application/runtime dependency.

## Analyst actions: usable free-first extraction path

The input is the **1,282 retained Alpaca/Benzinga news records**, not a new paid
ratings API. The normalizer accepts only explicit supported single-issuer
headlines, with caller-supplied issuer aliases and an allowed grade vocabulary.
Roundups, other companies, malformed grammar, contradictory target changes and
unsupported currency clauses remain unresolved. It does not ask an LLM to fill
gaps or translate qualitative commentary into a rating.

**98 announcements** are extracted: **96 reiterations, one upgrade and one
downgrade**. The remaining **1,184 input records** are other/unsupported news;
that count is not a claim that they all contain analyst announcements.

| Sample window | Extracted announcements |
| --- | ---: |
| 2019-07-25–31 | 9 |
| 2020-07-25–31 | 9 |
| 2021-07-25–31 | 15 |
| 2022-07-25–31 | 14 |
| 2023-07-25–31 | 12 |
| 2024-07-25–31 | 10 |
| 2025-07-25–31 | 19 |
| 2026-11-02–06 | 10 |

No supported action headline was found in the retained 2018 sample. That does
not mean no analyst actions occurred in 2018. These are sampled publication
windows, not continuous 2018–2025 coverage or an exhaustive individual-action feed.

Each derived event retains the original article content identity, source URL,
creation and current-version availability, and access level. Its
`report_available_at` is the article-version availability—not an invented instant
when the analyst first distributed a research report. Publication/update delays
are not removed. No analyst name is inferred from a firm name. Previous grades
and targets stay null unless explicitly printed; a word such as “maintains” does
not populate a missing previous value. Target-change tags follow literal action
words, without calculating an unstated prior target. Dollar targets use the
explicitly reviewed US Apple/Microsoft feed context; no currency conversion or
future split adjustment is applied. New issuers/currencies require review.

An independent standard-library audit reconciles all **98 events** to the retained
parent headlines, verifies identities and candidate hashes, and checks clocks,
access labels, current grades/targets and missing prior values. All eight
candidate exports round-trip exactly through the existing application import API.
They remain **unreviewed and incomplete** and cannot silently satisfy run readiness.

Open `http://127.0.0.1:18094/sources` and select **SAMPLE news-derived analyst
actions**. Deselect **Public records only** to inspect this licensed news feed;
that switch does not approve a source. The existing historical cutoff and
explicit-review controls remain in force. No existing service was rebuilt or
restarted. Preparation runs the checked-out code separately, then uses the
existing compatible import endpoint.

Code: [literal extraction](../backend/app/retail/analyst_news.py),
[offline preparation](../backend/scripts/prepare_news_analyst_actions.py).
The USD interpretation, finite headline grammar and sampled coverage are
conspicuous research limitations, not universal source promises.

## Earnings: issuer releases plus original SEC exhibits

Both selected issuer pages returned HTTP 200 and are retained with URL, capture
time and exact body hash. Their matching original SEC submissions were reused
from the earlier verified pilot, with hashes rechecked. Selected financial values
must match **one original EX-99 exhibit**, the correct issuer/period, and the
issuer release's EPS statement and rounded revenue headline.

| Issuer / period | Exact reported revenue, USD millions | GAAP diluted EPS, USD/share | Original SEC acceptance, Eastern |
| --- | ---: | ---: | --- |
| AAPL FY2025 Q1, ended 2024-12-28 | 124,300 | 2.40 | 2025-01-30 16:30:23 |
| MSFT FY2025 Q2, ended 2024-12-31 | 69,632 | 3.23 | 2025-01-29 16:08:56 |

Sources: [Apple release](https://www.apple.com/newsroom/2025/01/apple-reports-first-quarter-results/),
[Apple original filing](https://www.sec.gov/Archives/edgar/data/320193/000032019325000007/0000320193-25-000007.txt),
[Microsoft release](https://www.microsoft.com/en-us/Investor/earnings/FY-2025-Q2/press-release-webcast),
[Microsoft original filing](https://www.sec.gov/Archives/edgar/data/789019/000095017025010484/0000950170-25-010484.txt).

Headline revenue rounds to $124.3B/$69.6B; exact nominal millions above come from
original tables. GAAP figures are distinct from adjusted EPS/constant-currency
comparisons. Current or later restated values are not substituted.

The structured records separately retain SEC acceptance, unknown verified public
time, and an explicitly **assumed next-session-close daily delivery**. Date-only
issuer headers and an earnings-call time do not establish original publication
latency. `verified_public_at`, consensus and surprise remain **null**;
`strategy_eligible=false`. These two metric records remain staging evidence, not
an approved full earnings source or a new numeric trading feature. This uses the
[paired-fact normalizer](../backend/app/retail/earnings.py); no engine contract was
changed. Full quarterly extraction across 2018–2025 remains pending.

## Tests, preservation and next work

**325 backend tests including fresh PostgreSQL migration/immutability checks and
62 frontend tests pass**, alongside Ruff and frontend build. New adversarial cases
cover future article versions, wrong tickers, missing priors, contradictory/foreign
currency targets, snapshot hash/identity/range failures, filing-clock isolation,
and issuer/SEC mismatches or facts split across separate exhibits. The engine,
financial accounting, published versions and prior source revisions are unchanged.

Seven actual browser checks pass on the existing source UI: all 19 records in
the inspected 2025 analyst partition render, priors remain null, historical cutoff
and licensed-access filters work, review stays explicit, mobile layout fits and
no runtime errors occur. Three documentation browser checks also pass.

The read-only audit confirms **all 58 pre-existing containers unchanged**, all
**11 prior backtests unchanged** and all **11 earlier source payloads identical**.
Only new unreviewed analyst revisions were added through the existing API. All runtime data, licensed headlines, source bodies, manifests, receipts,
images and private test credentials remain under ignored
`.local/retail-qualification-20261108/`; none is committed as application data.

Next work is targeted: obtain public/provider clocks for additional Congress
cohorts and review ambiguous lineage/instruments; extend news acquisition and
explicitly sourced actions over continuous periods; expand issuer earnings pairs
quarter by quarter. A broader strategy backtest requires reviewed immutable
revisions with declared coverage. No new API key or paid subscription was needed
for this pilot, and no missing history is replaced with zeros.
