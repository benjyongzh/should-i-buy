# Implementation milestones and verification

## Full 2018–2025 earnings experiment — 2026-11-08

The [executed full-history report](full-history-earnings-experiment-2026-11-08.md)
verifies 64 issuer/SEC quarterly pairs and independently reconciles 128 GAAP facts.
A 192-event immutable child is reviewed only under the explicit next-session-close
research availability proxy; exact public delivery remains unverified. All 96 month
news queries complete: 35,854 news events and 1,262 literal analyst announcements
are imported as 16 yearly **unreviewed/incomplete** sources. One blank-headline row
is quarantined and 68 older publications are explicitly excluded from update windows.

A streamed LLM proposes the exact predeclared earnings-entry gate. Explicit draft
acceptance/publication, version transcript, journal conclusion and exact candidate
repeat pass. The outcome is mixed: SGD 29,819.54 baseline versus 23,302.66 candidate,
with maximum drawdown 32.19% versus 19.49%. All 2018–2025 periods are retained.
Independent reconstruction checks 8,044 marks, 8,044 decisions, 150 fills and 308
ledger entries. **339 backend/PostgreSQL and 62 frontend tests pass**, Ruff/build
pass. Engine 2.0.0 is unchanged. [Visual report](earnings-experiment.html).

The full-history load exposed an automatic API restart and source-catalog UI
failure in the existing deployment. A metadata-only SQL fix passes 339 backend
checks and 12 browser assertions in a separate read-only API, with all 230 summaries
identical and response time 2.44–2.53s instead of 25.23s. It is **not deployed** over
existing containers. All 58 identities, 11 prior runs and 212 source exports remain;
57 runtimes are unchanged and the API records one automatic restart. Exact cause
is unconfirmed. See the report before treating the running source UI as verified.

## Free-source qualification pilot — 2026-11-08

The [executed Congress/analyst/earnings pilot](retail-source-qualification-2026-11-08.md)
checks all 45 pinned snapshot files and reproduces 10,883 filings/187,288 printed
rows/182,595 event versions. All 6,234 House IDs match the ten retained annual
indexes; both reviewed Pelosi PDF hashes and selected facts match. Six rows,
including Senate HTML/paper samples, remain staging-only: filing-date proxy clocks
are not promoted to verified public times, and option exercises are not equity buys.

Literal extraction yields 98 article-derived analyst announcements in eight raw
source revisions. All round-trip through the existing API unreviewed/incomplete;
independent checks reconcile the headlines, missing priors, clocks and access.
Two issuer/SEC earnings pairs have verified nominal figures; public clocks,
consensus and surprise remain unknown. No source is automatically approved and
no new financial backtest is claimed. Engine 2.0.0 is unchanged.

325 backend/PostgreSQL and 62 frontend tests pass, as do Ruff and frontend build.
No existing container is rebuilt or restarted; preparation uses disposable
processes and the existing import path. Seven actual source-UI checks and three
documentation browser checks pass. The read-only audit confirms all 58 existing
containers, 11 prior backtests and 11 prior source payloads unchanged. See the report for exact scope and gaps.

[Free Congress dataset assessment](congress-dataset-assessment-2026-11-08.md):
pinned upstream code and actual manifest are reviewed. It is relevant staging
material, but its availability clock is filing-day end, not measured retail
publication. Synthetic checks reproduce timing, ambiguous cross-document merging
and later-contributor provenance. No broad dataset is imported or qualified.
Earnings will use issuer investor-relations releases plus original SEC exhibits;
free analyst work can start from explicit announcements in existing news access.
Public ratings sites are corroboration candidates, not verified free bulk history.

## Retail information source pilot — 2026-11-08

The target now explicitly models selected retail feeds; direct Senate access is
not mandatory when a suitable provider supplies reviewed information. Existing
Alpaca credentials supply historical/recent AAPL/MSFT news. Nine sample windows
produce 1,282 news records; 58 original SEC filings include 36 Form 4s, four
amendments and 18 earnings-related 8-Ks. An independent audit checks 92 retained
response hashes, all news clocks/identities, 39 insider rows and earnings exhibits.
Eleven unreviewed/incomplete revisions are imported into the existing source UI;
all 11 pre-existing backtests are unchanged. No engine change or new news-driven
performance claim is made.

304 backend/PostgreSQL tests, 62 frontend tests, Ruff and frontend build pass.
Missing article update clocks now fail instead of falling back to creation.
A real older article updated in a later query is retained and explicitly excluded
from that publication cohort. Completed pagination does not establish original
historical coverage. Pilot SEC HTTP-decoding and rendered-XML filename defects
were reproduced and fixed. The source viewer now selects rows by source kind; real exported event/universe
payloads had been hidden by their empty bars array. A separate frontend on 18094
serves this tested fix; six actual browser checks pass, including a real revised
article withheld before its update time. All 57 pre-existing containers remain
unchanged. Existing containers were not restarted: checked-out
adapter fixes are tested through separate preparation/import, not deployed over
the running provider-fetch endpoint. Quiver API is paid and remains optional;
structured analyst access, original news versions, continuous insider history,
amendments and scheduled freshness remain pending. See the
[full pilot evidence, pricing and specific inputs](retail-information-pilot-2026-11-08.md).

## Full Congress acquisition and Senate access — 2026-11-08

**Full historical Congress coverage is not yet qualified.** All ten requested
House indexes validate: 4,976 PTRs in 2018–2025 and 1,258 boundary-support records
in 2017/2026, 6,234 total. The resumable all-filer acquisition is active in the new
18092/15450 project. At the checkpoint 1,213 acquisitions persisted through
recreation/database restart; the same immutable request resumed. The final audit recorded 2,606 acquired PDFs at 00:18 UTC; live
counts are on the new coverage page. All 52 pre-existing containers are unchanged.
Source collection never auto-approves rows.

Normal Senate server/browser access still returns 403. A reviewed normal-browser
export/import bridge exists and passes synthetic checks, but no live Senate
search/results session or real report import is verified. An API key does not
resolve this denial. Current browser captures do not establish historical clocks.

283 backend/PostgreSQL and 60 frontend tests pass, plus migration 009/drift,
lint/format/build. Full-scope testing fixes the eight-digit-only ID assumption,
a cached-index import defect and Nginx's stale API-container address. Cross-year
supporting indexes preserve old ledger serialization. The earlier real bounded
Congress result reproduces exactly under unchanged engine 2.0.0. See the
[complete scope, evidence and specific next actions](congress-full-coverage.md).

## Canonical Congress cohort qualification — 2026-11-08

The [Congress source workflow](congress-source-workflow.md) now acquires bounded
House index/PDF/replay evidence, reconciles explicit canonical transaction and
amendment identities, and creates eligible children only after scoped review.
The March2022 Pelosi AAPL/MSFT filing cohort now qualifies under its conservative
observed-public policy. It is not an all-Congress or complete2018–2025 feed.

**276 backend/PostgreSQL and57 frontend tests pass.** A live HTTP500 replay failure
was retained; one retry established the exact-byte/Memento bound. Ten browser
checks pass. The real short exercise-following test/repeat ends atSGD9,992.07338455
with2 orders; the ordinary-equity-purchase control has0 orders. Independent
reconstruction matches40 marks/20 decisions/4 fills includingSPY references. Full
2018–2025 scheduling rejects missing coverage, and an earlier full-period RSI
result reproduces exactly. Engine2.0.0 is unchanged.

The fresh18090/15448 project preserves all47 pre-existing containers,35 older
results,6 copied source results,25 conversation turns,7 transcripts and the earlier
journal/raw revisions. Actual ledger/approval/source updates and deletes are
rejected by PostgreSQL; persistence passes recreation/restart. See the
[complete evidence and remaining scope](congress-ledger-verification-2026-11-08.md).

## Research journal, real improvement loop and bounded Congress review — 2026-11-08

The product [research journal](research-journal.md) now retains immutable plans,
published candidates, all recorded attempts, notes and conclusions around the
existing simulator. Prospective/retrospective chronology, frozen comparison
controls, atomic scheduling and explicit review/publication are enforced.
Selected journal evidence supplies the strategy's single conversation with
recorded outcomes and yearly reports, with later events/outcomes withheld at
earlier cutoffs. Engine2.0.0 is unchanged.

**259 backend/PostgreSQL and 54 frontend tests pass**, alongside migration/drift,
lint/format/build. A real AAPL2018–2025 browser cycle includes two actual LLM calls,
a reviewed RSI30→25 publication, candidate and exact repeat, comparison and an
immutable conclusion. Independent reconstruction passes8,044 account marks,
4,022 decisions,218 fills and238 strategy ledger entries. The candidate improves
aggregate funded ending equity/drawdown in this sample but misses positive years
and trails the matching SPY reference; no future-performance claim is made.

The new isolated project on18088/15446 survives application recreation/database
restart. All42 pre-existing containers,35 older results,3 copied source results,
23 earlier conversation turns and5 publication transcripts are preserved.
[Complete acceptance evidence](research-journal-verification-2026-11-08.md).

The [bounded House review](congress-bounded-review-2026-11-08.md) verifies two
March2022 filings and archive bounds, and identifies an Apple option-exercise
amendment that must not be counted as a second purchase. No new eligible Congress
revision or Congress-driven backtest is claimed; lineage/coverage/clocks and
Senate access remain blocked.

## Permanent conversation memory, version snapshots and Congress intake — 2026-11-07

Migration 007 enforces one permanent conversation identity per strategy, ordered
finalized turns and immutable publication-time transcripts. Complete eligible
conversation recall replaces the eight-turn window, including proposed rule JSON.
Capacity failure is explicit instead of silently truncating memory. Every version
can open its read-only conversation boundary; later discussion stays in the same
conversation without entering earlier versions. Legacy backfill excludes replies
that completed after publication and leaves unrecorded history empty.

**255 backend/PostgreSQL and 51 frontend tests pass.** Four actual provider calls,
ten explicitly synthetic padding messages and 16 named browser assertions verify
recall beyond eight turns, a remembered 321.09 SGD weekly-buy proposal, explicit
publication, immutable13-message v2 transcript and exclusion of a later 999 SGD idea.
No market observations or financial results were fabricated for this memory test.
SQLite/PostgreSQL immutability, migration/drift, lint/format and build are checked.
The new test project uses 18086/15444 and a restored copy of prior test data.

The user confirmed personal, non-commercial use. House acquisition now retains
eight 2018–2025 indexes (23,139 entries; 4,976 PTRs), 16 original sample PDFs and
three byte-matching public archive replays with verified Memento capture clocks.
Two bounded Congress observations are imported as raw/unreviewed/incomplete;
four real before/at-clock visibility checks pass and strategy readiness rejects
the source. Options, exercises and charitable transfers remain distinguished.
Full House/Senate/company completeness and original first-release timing remain
unqualified. See [history verification](conversation-history-verification-2026-11-07.md)
and [Congress evidence](congress-qualification-2026-11-07.md).

## Streaming strategy conversations and intraday sources — 2026-11-07

**Demonstrated in a new isolated project on 18084/15442:** migration 006, retained
strategy conversations, actual provider-to-browser streaming, ambiguity questions,
clarification answers, explicit draft review/acceptance/publication, evidence audits,
conditional sourced estimates, topic redirection, no-evidence handling and the
actual Stop button. Six complete live scenarios pass, with 42 named browser
assertions plus the separate cancellation check. Failed and interrupted attempts
remain retained. A fixed-budget model misunderstanding was corrected in the prompt;
run evidence now includes its frozen tested rules rather than only a version ID.
Full checks pass: **248 backend tests including PostgreSQL, 49 frontend tests,
Ruff lint/format, Prettier, production build and Alembic no-drift check**.

Alpaca acquisition retains 495 raw responses and 156,183 complete 15-minute bars
for AAPL/MSFT/SPY across 2018–2025. Independent reconstruction checks every bar.
Ninety-two monthly partitions have reviewed children under explicit revised-history
and 60-second-delay research assumptions. Four months with 27 gaps stay unreviewed;
full-period readiness and forced scheduling reject rather than substitute data.
A January 2019 one-hour-after-open case and exact repeat pass independent checks
of all three fills and 21 daily marks. This is not full-period intraday success.

Congress remains **unqualified**: permitted-use classification and original public
availability/archive evidence are missing; direct Senate access returned 403.
No disclosure reports were downloaded and no access conditions were bypassed.
Existing containers/databases were not upgraded or restarted by this work.
See [chat results](strategy-conversation-verification-2026-11-07.md),
[intraday/Congress evidence](intraday-congress-verification-2026-11-07.md)
and the [visual workflow](data-workflow.html#conversation).

Final preservation audit: all 35 earlier result hashes and checked versions remain
unchanged. All 32 pre-task container IDs are present, with five unchanged captured
states and 27 recorded state differences of unestablished cause; no commands
operated on those containers. This is recorded separately from this task's new
test-project deployment rather than claiming an unchanged whole-host snapshot.

## Live user-prompt strategy cycle — 2026-11-07

Following explicit user approval, seven actual editor prompts reached the configured
OpenAI model. Tests covered an exact RSI amendment using a derived result summary,
EMA/volume conditions, cash/fixed sizing, monthly/weekly frequency, partial exits,
profile funding separation, news/ratings/sectors/Congress requirements and intraday
timing. Three proposals were reviewed, accepted into drafts and explicitly published;
unsupported/future-information requests and stale proposals were rejected. One
unnecessary model refusal was retained; a clarification produced the requested
event rules, whose missing-source readiness remained blocked.

Four real 2018–2025 cases and four exact repeats completed. Generated RSI results
exactly match the previously reconciled results. Independent Decimal arithmetic
also reconciles all 4,022 marks/decisions and 284 fills of the new monthly/weekly
rules. Compare and annual/performance timelines render correctly. All 27 original
results, published versions and dataset hashes remain unchanged; this isolated
project now retains 35 completed runs. No application/engine/container changes
were needed. Full checks rerun: 231 backend including PostgreSQL, 42 frontend,
Ruff/format/Prettier/build pass. No new credentials were needed.

The earlier external-disclosure approval blocker is resolved for these tests.
Read the [prompt matrix, results, false refusal and remaining data limits](llm-user-workflow-verification-2026-11-07.md).

## Full-cycle final browser and evidence checks — 2026-11-07

The isolated Docker application on loopback 18082 passes all 17 final research
browser checks: comparison, decision/source inspection, funded reports, all 2,011
decision markers, actual brush zoom, selection from a zoomed chart, retained
zoom after financial-measure changes and mobile rendering. Both marker-rendering
and zoom-reset defects are fixed; 42 frontend tests and build/format checks pass.
The engine and saved financial results are unchanged. The cycle's earlier 231
backend/PostgreSQL tests remain passing evidence; they were not rerun during this
read-only browser continuation.

All 27 result hashes, published versions and the accounting dataset hash still
match the saved post-persistence snapshot. The original November 6 audit verified
all 27 pre-existing containers unchanged. Today's read-only comparison finds 23
original IDs still present and unchanged, while four original IDs are absent;
no operations were performed on those resources. These observations are recorded
separately rather than claiming the entire old host snapshot still matches.

At the end of this earlier browser stage, the local manual cycle was complete
and external results-to-LLM testing awaited approval; no summary had been sent.
The subsequent approved live test above supersedes that blocker. See
[the original full-cycle report](full-cycle-verification-2026-11-06.md).

## Full-cycle isolated Docker and real-data test — 2026-11-06

**Demonstrated:** new isolated Docker project on loopback 18082 with own volume,
migration 005/no drift, actual UI/worker onboarding for AAPL/MSFT/SPY, real
2018–2025 strategy cases, explicit schema-validated RSI v1→v2 amendment and
continuous annual/quarter/month comparison. Thirteen primary cases and 13 exact
repeats pass, including fixed SGD 500 monthly deposits and monthly DCA. Independent
stdlib accounting reconciles 52,286 strategy/benchmark marks, 26,143 decisions,
1,064 fills and 1,570 strategy ledger entries. Three funded synthetic future-input
mutation diagnostics retain identical 1,259-session earlier prefixes.

A 9.1 MB backup restores into a second fresh PostgreSQL/API with all 26 results,
source exports, profiles, strategy versions and company packages unchanged.
Queued work resumes with the expected exact result, both after restore and after
restarting only the new source project. The retained test app has 27 completed
runs. All 27 pre-existing containers retain their original IDs/start times,
restart counts and mount membership; existing 18080 remains unchanged.

A full-history UI marker slowdown was found and fixed using grouped point-only
series, retaining every decision. Current checks: 231 backend/PostgreSQL tests,
42 frontend tests, lint/format/build and final research browser checks pass.
**Not run:** the external LLM amendment call awaits explicit approval for the
strategy plus derived-result payload; automatic approval review rejected that
outbound step. The cycle uses an explicit local amendment and retains its mixed
outcome. A journal artifact is evidence, not a newly implemented journal UI.
See [full measured results, backup and approval scope](full-cycle-verification-2026-11-06.md).

## User-selected company regression coverage — 2026-11-06

Added 14 network-isolated backend cases that carry user-selected symbols, custom
benchmarks, dates, warm-up and event lookback from request through collection,
evidence review and immutable package creation. Cases cover AMD/CVS, a class-share
symbol and an explicitly fictional ticker, plus same-symbol benchmarks, repeated
selection/reuse, cross-company evidence isolation, invalid selections and an
unresolved identity. All market/source fixtures are labeled SYNTHETIC and do not
qualify real histories for those companies. Frontend selection tests now exercise
three ticker/date/benchmark combinations and verify the displayed job matches.

**Latest checks:** 230 backend tests pass; one PostgreSQL integration test is
skipped because `TEST_POSTGRES_URL` is unset. All 36 frontend tests, build,
Ruff lint/format and Prettier pass. The earlier 217-test PostgreSQL run and 17 live
browser checks below remain separate evidence; neither was rerun in this
follow-up. No application behavior, database, container or provider configuration
changed. See [selection test evidence](company-onboarding-verification-2026-11-06.md#user-selected-company-regression-follow-up)
and [next research work](continuous-research.md#recommended-next-deliverable).

## Requested-company onboarding — 2026-11-06

**Demonstrated in isolation:** ticker/date request UI, persistent worker jobs,
raw evidence/hashes, immutable reports, explicit atomic review/packages and reuse
of reviewed revisions. Newly collected NVDA evidence includes eight SEC filings,
the June ten-for-one split and nominal post-split dividend. Four real Apr–Jul 2024 rules
and their exact repeats pass; independent Decimal calculations reconcile 340 daily
cash/equity marks, all four fills and 85 SEC event decisions. A second request
submitted through the UI reuses the same reviewed accounting/SEC IDs and keeps
historical sectors blocked. All eight results and the original package survive
native API restart unchanged.

**Checks:** 217 backend tests including disposable PostgreSQL, 34 frontend tests,
Ruff/format/Prettier/build and 17 Chromium checks pass. SQLite/PostgreSQL migration 005,
drift, immutable triggers, concurrent claims, cancellation, evidence attacks and
publication rollback are covered. No simulation behavior or engine code changed.

**Not deployed:** the existing Docker application on 18080 and every pre-existing
container/database remain untouched. Native 18081 and a new disposable PostgreSQL
on 15439 supplied isolated evidence; this is not whole-stack Docker verification.
Other collector capabilities, exact original delivery clocks and full-period NVDA
qualification remain unverified/blocked as appropriate. See [actual outputs and
limits](company-onboarding-verification-2026-11-06.md), [workflow/configuration](company-onboarding.md)
and [diagram guide](data-workflow.html#on-demand).

## Real equity and event-source acceptance — 2026-11-06

**Demonstrated:** 13 real 2018–2025 cases and 13 exact repeats: hold, SMA20/50
and RSI14 on AAPL/MSFT/SPY, plus fixed BLS/SEC integration rules on AAPL/MSFT.
Independent stdlib arithmetic reconciles 52,286 daily strategy/benchmark marks,
26,143 decisions, 516 strategy fills and 1,080 ledger entries. Annual reports,
cash references, two AAPL compatibility controls and three earlier SPY controls
match; all 38 prior result hashes remain unchanged. Synthetic in-memory future
mutations leave three 1,008-session earlier prefixes unchanged. The complete
backend suite passes 182 tests with one PostgreSQL test skipped because
TEST_POSTGRES_URL is unset; Ruff passes. Native HTTP tests work with permitted
socket access. The standalone results report passes ten Chromium desktop/mobile
checks; the chart screenshot was visually inspected. No engine/application code
or container configuration changed.

These are fixed-rule in-sample results under declared reference-FX and source
availability policies, not exact delivery-vintage certification or proof of
strategy improvement. Broader news, sector and intraday acceptance remain open; the later bounded
onboarding verification above supersedes the earlier coordinator gap. See [measured results, run IDs and limits](real-equity-acceptance-2026-11-06.md)
and the [interactive performance/annual chart](real-equity-results-2026-11-06.html).

## AAPL/MSFT accounting and deployed source review — 2026-11-06

Reviewed accounting dataset `526cf606-bbff-4d89-8b43-00eeaa5fc16f` now contains
7,542 AAPL/MSFT/SPY daily bars, 2,494 reviewed reference-FX observations and 121
actions. Original issuer evidence resolves missing dates, four MSFT workbook
numeric artifacts and one declaration-date discrepancy. Existing HTTP imports,
review children, lineage, export hashes and duplicate identities pass. New York
coverage boundaries were corrected through new immutable revisions; final BLS
and SEC sources pass all 335 visibility pairs and full-period readiness. Raw
sources and missing sector histories are correctly blocked. All 38 earlier
completed result hashes are preserved; 14 targeted financial/source tests and
Ruff pass. No new backtest, browser import or container restart was performed.
See [actual revisions, checks and research-policy limits](company-intake-verification-2026-11-06.md)
and the [requested-company workflow and current limits](company-onboarding.md).

## SEC/BLS primary sources — 2026-11-06

BLS extraction and field-specific correction review produced 190 unreviewed
headline events; 96 source releases passed 288 table comparisons. SEC retrieval
retained 145 submission texts, 2,050 embedded documents, 268 checked item headings
and two separately linked amendments. Candidate schema, isolated route-function
retention, 335 synthetic diagnostic availability pairs and exact extractor
reproduction pass. Native HTTP TestClient startup stalled; deployed import and
real source-driven strategy acceptance remain unverified. The exports retain
explicit BLS five-minute and SEC next-session-close research availability
assumptions and have not been approved. See [actual source evidence and limits](primary-source-verification-2026-11-06.md).

## Historical strategy capabilities — engine 2.0.0, 2026-11-05

**Verified:** independent financial/causal gate before editor work; 183 backend
including PostgreSQL and 31 frontend tests; lint/format/build; isolated Docker
images/migration 004/drift and worker connectivity; 17 real Chromium workflow
checks; exact synthetic multi-source intraday replay and independent SGD fill
arithmetic; two live LLM planning/draft/publication checks. Existing Alpaca keys
returned 78 SPY five-minute intervals (2018-01-02) and 17 AAPL/MSFT news records
(2020-01-02); these real source slices remain raw/unreviewed.

Restart preserved ten earlier result hashes, two new synthetic results, fourteen
source exports, LLM versions/profile and the reviewed daily dataset. Own database
container and all 22 unrelated containers remain unchanged; only own application
services were updated on loopback port 18080.

**Unverified/blocked:** real event/sector-driven and full-period intraday
performance, complete original news versions, live analyst entitlement/key,
reviewed historical classifications and actual Congress collection/publication
history. Typed Congress imports/rules are tested, not a real-data archive.
See [actual evidence and run IDs](historical-capabilities-verification-2026-11-05.md),
[capability semantics](strategy-capabilities.md) and [what to provide](historical-input-checklist.md).
Earlier dated verification below remains historical evidence for its named engine.

## Performance timeline and cash comparisons — 2026-11-05

Completed reports and Compare now share a zoomable account-value timeline with
fill, contribution/corporate-action and optional decision markers. Chart/date
selection opens the saved account snapshot, readable rule outcomes, recorded
reasons and original audit fields. Published versions and different strategies
can share the chart; saved buy-and-hold and modeled zero-interest cash references
are deduplicated under shared assumptions. Different currencies are not overlaid.
Decimal-string percentages now display correctly in exposure/period reports.

**Verified:** 140 backend tests including PostgreSQL, 26 frontend tests, Ruff
lint/format, Prettier and production build. A disposable Chromium browser passed
12 deployed desktop/mobile checks: actual chart selection and zoom, markers,
normalized performance, three-strategy comparison, cash/SPY deduplication,
selected real partial-sale audit, mobile chart size, and no runtime/API failures.
The browser found and verified a fix for the audited-run selector's accessible
name. Screenshots were visually inspected. This is bounded browser verification
of the report/comparison screens, not an exhaustive application/accessibility audit.

The read-only cash endpoint uses frozen initial capital and recorded external
deposits in Decimal; interest and costs are explicitly zero. No engine behavior,
historical result, strategy version, provider or schema changed. Engine remains
1.4.0. Only this project's API/frontend were recreated on loopback port 18080;
the worker/database and unrelated containers were left in place. Final retained
hash/container/cash-curve checks are archived in
`.local/ui-timeline-20261105/verification-final.json`. See
[timeline usage and interpretation limits](performance-timeline.md).

Postdeployment checks matched ten complete retained result hashes and the
reviewed dataset export, independently reconciled all 7,407 cash-baseline marks
for those runs, and confirmed unchanged worker/database IDs plus all 22 unrelated
container IDs, start times, restart counts and port bindings.

## Funding and granular trade controls — 2026-11-05

Engine **1.4.0** is deployed in the isolated Trading Lab project. Strategies can
choose daily/weekly/monthly/once entry decisions, repeated additions, equity/cash
fractions, fixed order budgets, target allocations and partial exits. Profiles
independently configure fixed monthly account-currency contributions, default
zero. Returns/drawdown/period reports exclude external capital; actual balance,
contributed capital, investment P&L and eligible investor IRR are separate.

**Verified:** 136 backend tests including PostgreSQL, 20 frontend tests, Ruff
lint/format, Prettier and production build. Independent review passed before
editor changes; legacy configuration/profile/full-result hashes and four complete
financial baselines match exactly. Three real SPY Q1-2019 funded smoke cases and
three exact repeats completed; separate stdlib arithmetic reconciled 183 strategy
marks, 26 fills/18 exits and 183 independently reconstructed benchmark marks.
Live `gpt-6-luna` generation/modification passed the new schema, draft isolation
and separate publication checks.

Docker images built, migrations ran at head, and only the project's API/worker/
frontend were recreated and restarted on existing loopback port 18080. All six new
results, four retained legacy results, the reviewed dataset and new LLM versions
persist unchanged. The project's PostgreSQL container/volume remained in place;
all 22 unrelated container IDs, start times, restart counts and published ports
match the predeployment record. API/database/frontend are healthy; worker runs.

**Unverified in this extension:** a full 2018–2025 funded sweep and new interactive
browser layout review. Earlier real full-history 1.3 acceptances remain historical
evidence, not 1.4 funded results. See [configuration semantics](funding-and-trade-controls.md),
[dated test results and run IDs](funding-verification-2026-11-05.md), and
[independent review](milestone-3-review.md). No new credentials were needed.

## Real SPY acceptance executed — 2026-11-05

**SPY's combined-data blocker is cleared under the documented reference-FX research policy.** New immutable dataset `051e4285-e374-4b44-b82c-a54ffc8a6a6e` contains2,514 raw SIP bars,2,494 reviewed initial-release FX observations and 40 issuer dividends for 2016–2025. Source review supplies the missing Alpaca action fields and corroborates all 40 amounts with dated original pre-US-open publications. One anomalous2018-07-23 FX availability is delayed to2018-08-01 after the evidenced weekly release. Missing first releases remain omitted. All6,033 clocks pass the explicit14-day age limit; full source assumptions and archive-flag dispositions are retained.

Buy/hold, SMA20/50 and RSI14 completed on real data for **2018–2025** and supplemental **2019–2022**; all six repeats are exactly identical. Independent stdlib arithmetic matched9,057 strategy signals/marks and9,057 benchmark marks,75 strategy fills,262 strategy ledger entries, dividends/receivables, costs and reporting metrics. Input/result hashes and annual linked returns/order/fee totals revalidate. Prior input revisions/results remain unchanged. The isolated API/database/frontend remain healthy and the worker persisted all jobs. No application/engine behavior or frontend code changed in this source/integration pass. **121 backend tests including PostgreSQL** and Ruff lint/format pass; frontend's existing17-test/build result remains the latest check.

See [actual returns, run IDs, independent calculations and limits](real-spy-acceptance-2026-11-05.md). These are real-data model results with95% equity entry sizing, not broker-executable FX, certified original price vintages or out-of-sample evidence. QQQ/SMH/XLE source/action acceptance, original intraday FX/price-vintage certification and real Fear & Greed/news feeds remain unverified. Earlier sections below record their dated states; their SPY blocker statements are superseded by this result.

## Strategy indicators and external inputs — 2026-11-05

Engine **1.3.0** implements MACD, slow stochastic and publication-gated external series in declarative strategy rules. The mandatory independent review passed after finding and fixing previous-crossover split contamination; the finding, adversarial reproduction and independent recheck are in [Milestone 3 review](milestone-3-review.md). Four complete engine 1.2 synthetic financial baselines remain exactly equal. Existing strategies, datasets and completed results were not rewritten.

**Verified:** 109 backend tests including PostgreSQL; 17 frontend tests; Ruff lint/format, Prettier and TypeScript/Vite build. Tests cover hand-calculated oscillator seeds/smoothing/warm-up, delayed releases and prior clocks, missing/stale errors, future-mutation isolation, immutable source review revisions, manifest/hash rejection, worker pinning, synthetic acknowledgement and comparison compatibility. The independent reviewer separately checked 2,520 oscillator calculations, a SGD split/dividend/fee/FX hand-ledger, exact reruns and 74 focused tests.

The isolated Docker project rebuilt and started successfully on `127.0.0.1:18080`. Deployed API → PostgreSQL → separate worker completed three explicitly synthetic MACD/stochastic/external smoke runs; the external rerun was exactly identical. Source review created a new immutable revision; its parent export stayed unchanged. Unreviewed input scheduling returned422. Existing baseline result hash remains `211578ea941eaa5a7a49f0c21c0bf7badccdf5c3ab4ff698b0f50c91ea0557aa`. Private smoke evidence: `.local/strategy-inputs-live-20261105/report.json`.

**Blocked/unverified:** real financial acceptance still requires qualified FX/corporate-action review; the actual SPY revision still rejects scheduling. No real Fear & Greed history or qualified automatic feed was imported. VIX with unknown original publication times cannot be approved for signals. Browser interaction/layout was not separately exercised; frontend workflows use component tests and deployed HTTP/assets. Source rights/publication claims remain a human review obligation, not proven by an approval checkbox. See [source workflow and required inputs](strategy-inputs.md). The earlier sections below retain their dated counts and engine 1.2 state.

After final app-container recreation, source/review revisions, dataset hashes and all three complete results survived unchanged; the latest frontend asset returned 200 with the new controls. Migrations completed and `alembic check` found no drift. The isolated database container/volume was retained. Before/after snapshots verified all **21 existing homelab containers** had unchanged identity, uptime and ports. Live configured `gpt-6-luna` generation produced a validated MACD proposal; modification added stochastic and external operands. Drafts stayed unchanged until explicit acceptance, publication remained separate and prior versions stayed unchanged. These are authoring smoke checks, not strategy quality/performance evidence. Private records: `persistence.json` and `llm-report.json` in the same evidence directory.

## Continuous development and additional data — 2026-11-05

User-selected workflow now iterates over all of 2018–2025, retaining published revisions and every run, with continuous year/quarter/month analysis rather than a mandatory holdout split. Added a separate immutable market-context library and UI. All nine live context imports pass; SPY/QQQ/SMH/XLE each have 2,514 real raw SIP bars for 2016–2025 including warm-up, no calendar gaps, and remain unreviewed. Current checks: **83 backend tests including PostgreSQL**, **12 frontend tests/build**, Ruff, applied migration 003 and no schema drift. Isolated stack is healthy at loopback 18080. Engine 1.2.0 and old result hashes are unchanged. No real return is claimed; FX/action acceptance is still required. See [continuous research evidence](continuous-research.md).

## Current Linux verification — 2026-11-05

FRED follow-up: supplied key authenticated successfully; retrieved 1,266 numeric initial-release USD/SGD observations and omitted 60 explicit missing values. A candidate CSV and retained-source audit are prepared, but not imported/accepted: 266 archival release-date checks found unavailable pages and date/observation mapping discrepancies requiring review. The candidate fails the default seven-day FX age at 1,073 requested-period clocks; the explicit 14-day setting passes all 3,024 clocks. Current backend total is **73 passing tests including PostgreSQL**, with Ruff lint/format passing. Engine/profiles remain unchanged. See [FX source review](fx-data-review.md).

Fresh checks on this homelab verified Docker build/start, migrations/head/drift, frontend/API/PostgreSQL connectivity, separate worker execution, persistence after restart/container recreation, and identical repeat synthetic results. Project `trading-lab-linux-verify-20261104` publishes only `127.0.0.1:18080` and owns its PostgreSQL volume; existing containers/data were untouched. All 63 backend tests including PostgreSQL, 10 frontend tests, production build and Ruff lint/format passed in Linux containers.

Live Alpaca import again returned 201: 1,259 real raw SPY SIP bars, no missing sessions, hash matching the earlier reported import. Live `gpt-6-luna` generation **and modification now pass**, including schema validation, separate proposal acceptance/publication, and preserved earlier versions. The earlier LLM quota failure is historical. Qualified FX/action review and the three real SGD backtests/independent reconciliation remain **blocked**. No real return is claimed. See [current evidence and required inputs](verification-linux-2026-11-05.md).

The following dated sections retain earlier evidence and limitations as they stood then; current status above supersedes their pending Linux/LLM statements. Earlier private Windows artifacts were not present in this checkout.

## Deployment and real-data phase — 2026-11-04

Actual current checks: **63 backend tests passed in a disposable Linux container**, including isolated PostgreSQL migrations/check/rollback/reapply, immutable inputs, concurrent claiming and persisted worker results. The test process was deliberately given dummy Alpaca/LLM credentials; real HTTPX requests remained blocked and all tests passed. The native credential-isolation rerun passed **62 cases with the optional PostgreSQL case skipped**, because its URL was unset. Earlier native PostgreSQL checks used loopback 55432; container checks use only the isolated Compose database and random test-owned schemas. **10 frontend tests** and the TypeScript/Vite production build previously passed; the frontend is unchanged by this test-only patch. Ruff lint/format pass. Existing third-party deprecation notices and the build chunk-size advisory remain visible. See [testing.md](testing.md) for the unit/integration coverage map and limitations.

Credential audit: the missing-key LLM test previously inherited the server environment and could attempt a live call after keys were configured. An autouse fixture now clears inherited provider credentials/model in the test process, clears settings caches and blocks unmocked synchronous/asynchronous HTTPX transport requests. Two regression tests verify these guards. Explicit MockTransport provider fixtures and in-process API tests remain functional; that patch did not edit `.env` or running services. No real credentials were supplied or used for those automated tests. Subsequent credentialed integration checks are recorded below.

Inspected both Compose configurations, Dockerfiles, Nginx, environment loading, data/LLM adapters and the import UI. Fixed nested `.env` exclusion in Docker contexts, added explicit SIP/IEX feed selection and retained the dividend-completeness attestation on Alpaca imports. Feed/error/pagination tests use controlled HTTP responses; import tests check persisted action/attestation data and revision hashes. LLM HTTP tests cover valid strict output, invalid schema, refusal, truncation and provider error, alongside existing explicit draft acceptance/publication workflow tests. No engine behavior or dataset immutability rule changed.

**Docker subsequently VERIFIED after the user installed Desktop:** Windows/WSL 2 Linux engine 29.9.2, Compose 5.6.1. Both image builds, migration exit 0, `alembic check`, PostgreSQL/API/frontend health and independent worker processing passed in isolated project `trading-lab-verify-20261104080751` at loopback port 18080. All **61 backend tests** also passed in the Linux API container, including PostgreSQL; container Ruff checks passed. Nginx served the SPA/assets and proxied API/DB health. Complete dataset/version/profile/run/result comparisons passed after service restart and after container recreation with the retained volume. A second HTTP-submitted job completed after recreation with exactly the same result. The engine remains 1.2.0. Removing an unnecessary recursive env-template exception fixed Docker build-context traversal of an inaccessible test cache. See the runbook for exact evidence and hashes.

**Credentialed Alpaca checks now VERIFIED:** read-only paper account authentication at `https://paper-api.alpaca.markets/v2/account` returned 200. Historical SIP data correctly uses the separate `https://data.alpaca.markets/v2` base. The UI's actual import API, through Nginx, imported 1,259 real raw SPY daily bars for 2018–2022, no missing sessions. The revision remains unreviewed and has no FX/actions; scheduling was correctly rejected with 422 and created no run. Dataset/hash/evidence are recorded in the runbook. Interactive browser import and source publication-vintage certification were not performed.

**BLOCKED:** complete real FX/action reconciliation and the three real SPY runs/independent selected-fill comparison; live LLM generation/modification. An OpenAI key was supplied, but the temporary GPT-5.4 Mini live request returned HTTP 429 with `credit_balance_exhausted`/`insufficient_quota`. No successful completion, proposal acceptance or publication occurred. The saved model field was blank at inspection; GPT-6 Luna is now the recommended cost-focused candidate, not a benchmarked or live-validated winner. No real returns were generated. Standalone Ubuntu/external-DB deployment, Windows reboot autostart and backup/recovery remain unverified.

Free-first source plan: test Alpaca historical SIP, assess ALFRED DEXSIUS initial-release observations with actual publication dates, and reconcile US SPY issuer corporate actions. Historical SIP's documented free access must be checked on the user's account. Fed weekly publication can exceed the default seven-day FX age; any explicit use of the existing 14-day setting must be recorded. Revised equity bars and assumed evening timestamps do not constitute strict vendor-vintage certification. Exact credentials, safe isolated Docker commands, source-review steps and pending acceptance calculations are in [deployment-verification.md](deployment-verification.md) and [data-providers.md](data-providers.md).

## Earlier milestone evidence

Current correctness gate: independent Milestone 3 review **passed for engine 1.2.0** after five confirmed baseline defects were fixed. At that gate the full backend suite passed **54 tests**, including PostgreSQL, and the full four-run synthetic acceptance scenario was regenerated successfully. See `milestone-3-review.md`. Earlier 1.1.0 results remain immutable and require new runs to apply corrections.

The sections below retain the original implementation verification history.

## 1 — Foundation
Implemented modular backend/frontend, configuration, SQLAlchemy/PostgreSQL, Alembic, Compose and project conventions. Native API health and frontend startup/build verified. Migration upgrade/downgrade/reapply and schema-drift checks pass on SQLite and PostgreSQL 16. Docker was unavailable during the original milestones; subsequent Windows Desktop verification is recorded above.

## 2 — Market data / clock
Implemented raw CSV/JSON import, Alpaca adapter, explicit synthetic demo, immutable revision hashes, FX, actions, coverage diagnostics, XNYS calendar and bounded strategy data views. Tests prove future blocking, FX publication gating, missing-session errors, holiday/early-close behavior and import validation. Live Alpaca credentials were unavailable.

## 3 — Simulation
Implemented Decimal ledger, next-open orders, costs, affordability, sizing, exposure/position/frequency limits, protective exits, splits/dividend receivables, marked final holdings, benchmark and analytics. Determinism, round-trip fees, FX valuation, flat/no-trade cases, splits, protective gaps and future-mutation tests pass. Simplified daily/full-fill conventions are documented.

## 4 — Declarative authoring
Implemented bounded typed expression trees, every requested indicator/operator, recursive visual editor, JSON editor, schema validation, draft revisions, publish/history/clone/archive/restore, parent versions and side-by-side definitions. API and frontend workflow tests pass; browser creation/validation/publication verified. Published versions have database immutability triggers.

## 5 — Profiles / jobs / experiments
Implemented shared editable profiles, snapshots, batch experiments, transactional PostgreSQL claiming, token ownership, heartbeat/progress, cancellation, visible stale/failure records and separate worker. Eight concurrent PostgreSQL claimers claimed eight distinct jobs. Snapshot and failure lifecycle tests pass.

## 6 — Dashboard / comparison
Implemented persistent run creation, equity/drawdown/benchmark charts, costs and statistics, filterable orders, trades/signals/ledger, open positions and incompatible-assumption warnings. Frontend TypeScript/production build and workflow tests pass. Synthetic results stay labeled.

## 7 — LLM authoring
Implemented configurable OpenAI-compatible provider interface, strict structured outputs, backend revalidation, persisted proposal preview, explicit draft acceptance and separate publication. Model/prompt/revision metadata retained. Missing-key and human-approval tests pass. Live provider calls remain unverified.

## 8 — Hardening / demonstration
Implemented immutable-input database triggers, bounded requests/trees/imports/queues, server-only credentials, restricted CORS and loopback deployment defaults, input hashes and synchronized documentation. The required four-run synthetic scenario passes version/profile immutability and later-price/FX mutation invariance. Measured results are in `demo-report.md`.

Original pre-review implementation checks: **45 backend tests passed**, including PostgreSQL migrations/rollback, eight-way concurrent claiming, complete worker persistence and immutable inputs. **9 frontend workflow tests passed**; TypeScript and Vite production build passed; Ruff lint/format checks passed; npm audit found **0 vulnerabilities**. Dependency deprecation notices and a frontend chunk-size advisory are disclosed, not hidden.

Live browser verification: created a visual MA strategy, saved and validated its draft, published version 1, selected the SGD profile and an explicit synthetic revision, acknowledged synthetic use, submitted a job, processed it in the separate worker, viewed filled orders/curves, and refreshed the results page successfully. A screenshot is retained in `.local/trading-lab-result.jpg`. The native API health check and frontend HTTP startup succeeded.

The complete four-run acceptance demonstration also passed against native PostgreSQL 16 with engine 1.1.0. The comparison page was inspected with three independently simulated portfolios, its sorted metrics table, and the synthetic-data disclosure; `.local/trading-lab-comparison.jpg` records that view. There were temporary Vite hot-reload connection resets during formatting; fresh navigation and result refresh succeeded afterward.

Provider hardening: official aggregation rules show that Alpaca daily volume includes extended-hours prints. Complete bars are now gated to assumed 20:15 New York publication, evaluated at 20:30, rather than exposing final daily volume at regular close. A dedicated mock-provider test verifies pagination, raw/IEX parameters, evening availability and explicit entitlement errors. Engine version is 1.1.0; old completed results remain unchanged.

Original release status was **locally verified synthetic MVP; Docker and credentialed real-data/LLM validation outstanding**. Docker Desktop verification has since passed as recorded above; credentialed real-data/LLM validation remains outstanding. This is not a verified real-data production deployment.

Final data-quality guards also reject unfinished API daily bars and block unreviewed real raw corporate-action histories. Both have dedicated passing tests; synthetic fixtures remain visibly labeled and unaffected.
