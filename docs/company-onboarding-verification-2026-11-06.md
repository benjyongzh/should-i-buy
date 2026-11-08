# Company onboarding verification — 2026-11-06

Later follow-up: [the full-cycle Docker test](full-cycle-verification-2026-11-06.md) now verifies a separate project on 18082, full-period AAPL/MSFT/SPY onboarding, funded replay and backup restoration. The dated native evidence below retains its original scope; existing 18080 remains unchanged.

## Outcome and environment

Implemented `/companies`, durable collection attempts, bounded Alpaca/SEC
collectors, retained original evidence, immutable reports and explicit reviewed
packages. Initial orchestrated capabilities are daily accounting and SEC filing
presence/item tags. Existing import, source-review, readiness and backtest
contracts are reused; engine 2.0.0 and simulation behavior are unchanged.

**This change is not deployed to the existing Docker application on port 18080.**
Every pre-existing container, homelab PostgreSQL instance, service port and volume
was left untouched. Verification used a separate native preview on loopback
18081, an ignored SQLite database, and a newly created disposable PostgreSQL 16
container on loopback 15439 with temporary storage. These are isolated tests,
not a new full Docker deployment or a container-restart acceptance claim.

Runtime evidence is ignored under `.local/onboarding-verification-20261106/`.
No keys, contact address or raw provider data are committed.

## Automated checks

- **217 backend tests pass**, including PostgreSQL; no skips in that run.
- Ruff lint and formatting checks pass.
- **34 frontend tests pass**, production build and Prettier checks pass.
- SQLite/PostgreSQL migration 005 upgrade, downgrade/re-upgrade and Alembic
  metadata drift checks pass. Updates/deletes of artifacts, evidence links,
  reports and packages are rejected by database triggers. Request configuration
  cannot change; mutable collection status can change.
- PostgreSQL concurrent claim checks assign eight distinct intake jobs to eight
  workers. API tests cover persistent requests, idempotency conflicts, cancellation,
  queue capacity, deadlines, stale leases and protection against an expired worker
  publishing over a new owner.
- Review tests reject missing candidates/evidence, wrong nominal amount/payment
  date, duplicate/out-of-scope actions, false quotes, foreign/tampered artifacts,
  premature/late action clocks, stale report hashes, missing attestations and
  unsupported approvals. A forced source-retention failure rolls back the staged
  accounting output and package together.
- Missing FX and raw session gaps block accounting, without substitution. SEC
  tests reject mismatched acceptance clocks, accession, CIK, primary form/file and
  item headings. Size/host/date/document limits are checked.

Build notes: Vite still reports its existing large-JavaScript-chunk warning.
Backend warnings concern the installed Starlette/httpx test-client combination
and pandas timezone-array deprecation. They do not fail these checks.

## User-selected company regression follow-up

Added `backend/tests/test_selected_company_onboarding.py`: 14 offline regression
cases for arbitrary selected companies, custom benchmark/date/warm-up/lookback
settings, class-share notation, reuse of reviewed revisions without refetching
prices/filings, cross-company evidence rejection, immutable earlier packages,
same-company benchmarks and invalid/unresolved selections. A fictional ticker
proves the coordinator is not restricted to previously demonstrated stocks.

These use visibly **SYNTHETIC** provider fixtures to exercise the review contract;
they do not certify live AMD/CVS/class-share data, nor real company exchange/CIK
metadata. The separate real NVDA evidence below retains its original scope.
Frontend tests exercise NVDA/CVS/class-share selections, custom dates, benchmark,
warm-up, uppercase normalization and the matching persisted job display, while
retaining explicit-review and failure/retry checks.

Latest required checks: **230 backend tests pass, one PostgreSQL test skipped**
(`TEST_POSTGRES_URL` not configured); **36 frontend tests pass**; backend lint/format,
frontend build/format and diff whitespace checks pass. Existing Docker containers
and databases were not accessed or changed. The earlier 217-test disposable
PostgreSQL and 17 live-browser checks were not repeated by this test-only follow-up.

## Real third-ticker collection and review

Request: **NVDA**, benchmark SPY, **2024-04-01–2024-07-31**, 90 calendar days of
warm-up. This is deliberately a bounded onboarding acceptance containing a real
split and dividend; it is not a full 2018–2025 NVDA qualification. Existing
AAPL/MSFT/SPY full-period acceptance remains separately recorded.

Existing Alpaca credentials and SEC contact configuration were sufficient.
The isolated database was seeded with the previously reviewed SPY/ALFRED
reference-FX revision. NVDA prices/actions/filings were newly fetched through
the implemented collector. No synthetic replacements were used.

- SEC current mapping resolves NVDA to CIK **0001045810**, Nasdaq. Historical
  common-stock continuity for this interval was explicitly reviewed.
- Retained **12 original response artifacts**, totaling **4,082,896 bytes**:
  identity, prices, broker actions, filing inventory and eight full submissions.
  All twelve download hashes were independently checked in the browser workflow.
- Accounting candidate contains **292 raw daily bars**: 146 sessions each for
  NVDA/SPY, 2024-01-02–2024-07-31. The reviewed revision reuses **2,494** historical
  reference-FX observations and contains **five** actions: three NVDA plus two
  upstream-reviewed SPY distributions.
- Original retained NVIDIA filings support the March dividend, June split and
  June dividend. Review preserves **$0.04 per pre-split share**, **10:1 effective
  June 10**, and **$0.01 per post-split share**, ex-date June 11/payment June 28.
  Broker ex-dates were reconciled with issuer record/payment terms. Generic text
  proposals did not grant eligibility; explicit issuer/identity/completeness and
  research-policy review created the final package.
- SEC output includes **three events** within the declared New York coverage,
  using the conservative next-session-close clock. Eight documents also cover
  the earlier evidence look-back. There is no inferred sentiment.

| Immutable output in the isolated database | ID / SHA-256 |
| --- | --- |
| Initial request | `d281c335-69e7-4243-b4e2-869598b45bca` |
| Collection report | `ca6a3caf07e3354c8fb61037e96320b1d47b128af1f5c7ab878199fc6f466964` |
| Reviewed package | `fe8eb34c-c971-4d25-9014-8c29665b3341` |
| Package content hash | `5b081acc97f552c031286375f78240b8e767b68470dcbed2033784039e226329` |
| Reviewed accounting dataset | `3b47399a-ad83-45c5-a509-13ba2a9d2d65` |
| Accounting hash | `62b4f3ad16887df869a6450eecceb8ee5a965c161ca33058a8dd2fda083ab895` |
| Reviewed SEC child | `5ee52060-e89a-455a-b866-09217c54eed0` |
| SEC content hash | `b12c16628230fa22593377a730fb9a2971c621e7f3d148325c3ca7c1451132dc` |

Independent stdlib hashing of exported accounting/source content matches the
package references. Raw parents and the original report remain unchanged.

## Backtest integration, independent accounting and chronology

Fixed profile: SGD 10,000; fee SGD 2.50 per executed order; slippage 0.05%; whole
shares; no contributions, leverage or shorts; 95% sizing; daily close decisions
and next strictly later session-open execution. Four fixed rules pass readiness
and each runs twice with identical complete result hashes.

| Rule | Executed orders | Ending SGD equity | Exact repeat |
| --- | ---: | ---: | --- |
| Hold | 1 | 12,644.2779912000 | Yes |
| SMA20/50 crossover | 1 | 12,173.2439558820 | Yes |
| RSI14, entry<30 / exit>65 | 0 | 10,000 | Yes |
| SEC Item 2.02 presence; exit after 20 held sessions | 2 | 11,807.5261372160 | Yes |

These values are **integration diagnostics under research source policies**,
not strategy recommendations or evidence of general profitability. RSI made no
trades; no trades or returns were invented to fill the case.

An independent standard-library Decimal program, with no application imports,
reconciles **340 primary-run daily cash/equity marks and all four fills**. It
checks source/FX availability and age at each clock, next-session fill ordering,
raw open plus slippage, fees, cash affordability, split quantities, dividend
entitlements/payment FX and remaining shares. All **85 SEC rule decisions** and
their cited events separately match the events visible at their clocks.

Example: the hold order buys **7 shares** at raw open **USD884.48**, execution
**USD884.922240**, USD/SGD **1.3475**, fee **SGD 2.50**, leaving
**SGD1,650.4709712000**. The selected FX observation and its modeled availability
both precede the fill. June 10 changes 7 shares to 70; the June 11 dividend creates
a **USD0.70** receivable, converted to SGD only at payment. These checks exercise
the real split and post-split nominal dividend basis.

## Browser, reuse and process persistence

**17 Chromium checks pass** over the initial real review and final request/reuse
workflow: page/navigation, policy/identity/action-coverage gates, evidence hashes,
review publication/idempotency, reload persistence, actual UI queue submission,
worker CLI collection, partial-capability approval, restart preservation and
desktop/mobile layout. No runtime errors were observed; screenshots were visually
inspected. A narrow mobile attempt button was adjusted to wrap its text.

After restarting only the test-owned native API process, all eight complete
result payloads and the original immutable package remain identical. A new real
UI request is processed by `python -m app.worker --once`: it retrieves the current
identity once and reuses the reviewed accounting and SEC revisions. Requested
historical sectors remain visibly blocked and cannot be approved. The new package
references the same dataset/source IDs, rather than copying or mutating them.

## Still pending / required inputs

- Deployment of migration 005 and updated API/worker/frontend to an intended
  project environment. Existing Docker containers were intentionally untouched;
  this feature has no new whole-stack Docker or container-restart verification.
- No new key was required for the demonstrated scope. Both API and worker need
  the existing `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`, `DATA_SOURCE_CONTACT_EMAIL`;
  SGD collection needs an already reviewed historical FX revision.
- Full requested date ranges and other equities require their own identity,
  source completeness and action review. A current SEC mapping is not a historical
  universe, and an empty broker response does not prove no corporate actions.
- General issuer-site extraction, renamed/delisted identities, stock/complex
  distributions and terminal actions remain unsupported by this coordinator.
  Conflicting ex-dates/action identities require the existing manual reviewed
  import path. Uploaded transcripts remain explicitly reviewer-supplied evidence.
- Additional original-time news/ratings archives, historical sectors, intraday
  and Congress collection remain separate source work. Shared BLS/macro data is
  selected through existing source pickers; it is not recollected per company.
- Raw SIP is revised history with assumed evening availability; SEC uses a
  next-session-close proxy; ALFRED uses the previously reviewed reference-FX
  research policy and 14-day age limit. These are not observed original vendor
  deliveries, executable FX, universal news coverage or live execution.

See [operation, configuration and limits](company-onboarding.md) and the
[diagram guide](data-workflow.html#on-demand).
