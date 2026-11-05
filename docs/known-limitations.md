# Known limitations and remaining release verification

**Current engine 2.0.0:** opt-in intraday/event timing, historical selection,
conditional sizes and news/analyst/economic/Congress rules passed independent
review before editor work. 183 backend/PostgreSQL and 31 frontend tests,
lint/format/build and 17 deployed Chromium workflow checks pass. Isolated Docker
migration/drift/worker/persistence checks pass; all 22 unrelated containers are
unchanged. [Dated evidence](historical-capabilities-verification-2026-11-05.md)
distinguishes exact synthetic acceptance from the two raw real Alpaca source slices.

- Real 2018–2025 event/sector/intraday performance remains unverified. Original
  news/report versions, complete coverage/access evidence, historical security
  states and additional equities' reviewed FX/actions are source requirements.
  Raw Alpaca preparation succeeds but does not certify original vintages.
- Direct Benzinga ratings needs an optional server key/entitlement and confirmed
  publication timezone; it has mocked normalizer/HTTP tests only. Congress uses
  typed source imports and public-disclosure clocks; no real collection/scraper
  or historical first-public archive is configured. Disclosed ranges remain
  ranges. [Specific data/key actions](historical-input-checklist.md).
- Profiles allow up to 50 symbols; runs cap source partitions/rows/intervals/signals.
  Full eight-year one-minute/all-market replay exceeds current bounds. No order
  book, liquidity/participation, per-stock halt, delisting/merger settlement or
  executable intraday FX model is supplied. Held identity/terminal-price failures
  reject explicitly. Daily metrics use daily marks, with separate retained
  intraday reporting; old runs gain no invented intraday points.
- LLM plans are schema-validated proposals with interpretation/data requirements;
  unsupported plans are blocked. Interpretation can still be imperfect and needs
  human review. Acceptance edits the draft; publication remains separate.
  Two live plans passed selected semantic checks, not broad authoring evaluation.

The dated 1.4 and earlier observations below describe their original scope.

**Earlier engine 1.4.0 evidence:** funding and granular timing/sizing are implemented and
independently reviewed. Current reporting checks: 140 backend tests including
PostgreSQL, 26 frontend tests, lint/format/build pass. Account-value/decision
timelines and cash/buy-and-hold overlays pass 12 bounded desktop/mobile browser
checks; see [timeline usage and limits](performance-timeline.md).
Three Q1-2019 real SPY funded cases and exact repeats
pass independent daily accounting/TWR reconciliation. Application restart
preserved all six new results and checked historical inputs/results; 22 unrelated
containers are unchanged. New DCA/partial-exit LLM authoring smoke passed. See
[dated verification](funding-verification-2026-11-05.md).

- Monthly contributions are fixed account-currency amounts on the first calendar
  month's trading-session open; a midmonth start has no retroactive credit.
  Strategy schedules filter close decisions, normally filling next open, so
  monthly DCA normally fills on the second session. Target allocations can miss
  their target through gaps, costs, rounding and rejection. No withdrawals or
  variable salary schedules are implemented.
- Partial exits use pooled average cost and count exit tranches, not tax lots or
  necessarily whole roundtrips. Ordinary sell holding locks conservatively reset
  after additions. Whole-share/minimum-notional rules can leave dust. Investor
  IRR needs 365 elapsed days and a root in the bounded search; it is unavailable
  for the Q1 smoke. A full 2018–2025 funded sweep remains unverified. Selected
  desktop/mobile report/comparison interactions passed the later browser checks.
  Earlier full-history
  1.3 real acceptances remain preserved.

**SPY real-data acceptance now passes under the documented reference-FX research policy.** Combined revision `051e4285-e374-4b44-b82c-a54ffc8a6a6e` supports the three2018–2025 strategies and supplemental2019–2022 runs. All six exact repeats and independent daily accounting/signal/benchmark reconciliation pass. Source review corrected one early FX availability and supplied40 issuer dividends with corroborated pre-US-open USD publication evidence. See [actual results and source limits](real-spy-acceptance-2026-11-05.md). This clears the SPY integration blocker; it does not certify executable FX, original price vintages or other instruments.

Current deployment follow-up: reviewed source revisions/results persisted across isolated app-container recreation, with no schema drift. Live LLM generation/modification using the extended MACD/stochastic/external schema passed explicit acceptance/publication checks. These bounded smoke checks do not establish strategy quality or certify source history.

- The earlier source-only pass had 121 backend/PostgreSQL and 17 frontend tests; current checks are recorded above. Independent engine 1.3 review cleared after a split-day crossover fix; the subsequent1.4 funding gate also passed. MACD/stochastic and reviewed external series drive rules with frozen inputs. Four full engine 1.2 baselines remain exactly equal under1.4; old completed results are retained. Source-preparation tests and real acceptance checks are separate evidence.
- External source approval is an explicit human attestation, not certification of publication accuracy or data rights. FRED retains conservative date-only first-release availability; subsequent revisions are not replayed. Age is measured from observation date, so monthly series require a suitable explicit limit. Current VIX publication times remain unknown and ineligible. Fear & Greed supports timestamped CSV import/review only: no qualified automatic historical feed or real index history was added. News/event rules are implemented in the 2.0 extension; qualified real original-vintage histories remain outstanding. External inputs cannot replace accounting FX or action datasets.
- The original SPY/QQQ/SMH/XLE price-only revisions remain unreviewed. A separate reviewed SPY combined revision passes real financial acceptance; QQQ/SMH/XLE still need their own action reviews and combined inputs. Selected report/comparison desktop/mobile browser checks now pass; exhaustive application, device and accessibility coverage remains unverified.
- Engine 1.1.0 and earlier failed the independent Milestone 3 gate: future daily volume, nonchronological protection, pre-cost risk limits, opening take-profit ordering and zero-equity metrics had confirmed defects. Engine 1.2.0 corrects these. Previously completed results remain immutable and are not retroactively certified; rerun them with the corrected engine before relying on them. See `milestone-3-review.md`.

- Linux homelab Docker build/start, migrations/drift, Nginx/API/PostgreSQL/worker connectivity, and dataset/result persistence across restart and container recreation pass verification (2026-11-04–05), alongside the earlier Windows record. The original diagnostic used explicitly synthetic data and an isolated volume/loopback port 18080; later real-data/report checks are recorded above. External-database deployment, reboot autostart and backup restoration remain untested. See `verification-linux-2026-11-05.md` for the original evidence and pinned commands.
- The backend test count includes unit, API and database integration cases; no coverage percentage is claimed. Provider HTTP is mocked or blocked, even when dummy credentials are present. This isolates automated tests from real keys but does not certify live provider responses or source-data completeness. The missing-key LLM test's former environment inheritance was corrected before real credentials were supplied. See `testing.md`.
- Earlier Alpaca authentication/import checks produced an unreviewed1,259-bar SPY price-only revision. That revision remains blocked and unchanged. The subsequent reviewed combined SPY revision has completed real runs; earlier demonstrations remain explicitly synthetic. No provider subscription or homelab service was changed for this acceptance pass.
- Live OpenAI generation and modification pass with configured `gpt-6-luna` (2026-11-05), including backend schema validation, draft isolation until acceptance, separate explicit publication and preserved earlier versions. The earlier quota failure is resolved for these calls. Interactive LLM proposal acceptance/publication UI, broad output-quality evaluation and model cost/latency comparisons remain unverified. The client does not explicitly set reasoning effort.
- Alpaca supports explicitly selected SIP or IEX. The UI defaults to SIP; legacy API calls retain IEX. IEX is not consolidated volume. Historical SIP access succeeded on the supplied account; no subscription was changed. Either feed's bars may be revised, and 20:15 New York time availability is an assumption. Strict vintage research needs source-provided availability vintages. CSV imports depend on truthful source metadata and complete corporate actions. Missing splits cannot be reliably inferred from prices alone.
- Accounting FX now uses2,494 reviewed initial-release observations, with115 missing initial values omitted and one evidenced conservative availability correction. The explicit14-day age passes all 6,033 full-period clocks; maximum age12.3541667 days. The seven-day default fails2,142 clocks. Current archive404/date-label conflicts have recorded dispositions using ALFRED first-vintage metadata plus conservative weekly-release floors; original intraday publication was not independently certified for every row. Subsequent revisions are not replayed, and lagged reference rates are not executable conversion quotes. See `fx-data-review.md`.
- All40 SPY2016–2025 issuer dividends are reviewed with US dates/amounts and matching original issuer USD announcements published before the US open. Missing Alpaca fields are supplied from the US issuer; its tiny precision difference is documented. ASX evidence supplies publication clocks/USD amounts only; Australian CDI dates and AUD conversion rates are excluded. Source statements can contain errors, such as one Australian notice's incorrect US payment date; the chosen US issuer/Alpaca authority is recorded. See `corporate-action-source-check.md`.
- SPY split coverage review combines empty action responses, raw/split-adjusted equality on2,514 bars and a separate zero-split history source. This is a bounded review of available publisher records, not a guarantee of exhaustive source completeness or proof of original vendor vintages. The reviewed flags record that review; they cannot certify every vendor claim.
- Real raw datasets cannot be backtested until the source's corporate-action coverage has been explicitly reviewed and all effective splits supplied. This is a source-owner attestation, not automatic independent verification. The import forms expose it and new revisions preserve it in their content hash. Unfinished API daily bars are rejected.
- The calendar is regular-session XNYS (also used for US Nasdaq-listed instruments), 1990–2035. Exact per-venue halts and delisting settlement are not modeled. Historical membership/state transitions are supported in 2.0 when reviewed inputs are supplied. Missing in-period sessions reject the run. Manually chosen current symbols can cause survivorship bias.
- Full fills, fixed daily slippage/spread and no market-impact model. Explicit policies allow additions and partial exits; no partial execution/liquidity model, tax/withholding, margin, shorts, cash interest or cash-in-lieu. There is no automatic dividend DRIP; a strategy may reinvest settled cash through ordinary buys. Protective fill timestamps/FX use the disclosed conservative daily-bar convention. Minimum-notional rules can leave unsellable dust.
- Computation is single-process per worker and bounded by dataset/queue limits. Large daily universes/results remain memory resident during simulation; cancellation checks occur per session, with half-second database polling. A stale worker fails visibly rather than automatically retrying. SQLite is for one local worker, PostgreSQL for deployment/concurrency.
- Data imports are bounded synchronous HTTP operations; backtests always run in the separate worker. Provider calls may take up to the reverse proxy timeout; use smaller import ranges when needed.
- The MVP has no login. Keep loopback bindings or put it behind an authenticated trusted access layer. API keys stay on the server. Do not publicly redistribute source market data.
- The version comparison UI shows definitions side by side, with exact numeric fields in JSON. Automated hyperparameter optimization, ML workflows, ensembles and paper/live trading are deferred. Intraday history is supported by 2.0 within its stated limits.
- Backend dependencies currently emit third-party TestClient/Pandas deprecation notices. Tests pass; no runtime monkeypatch or warning suppression hides them.
