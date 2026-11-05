# Milestone 3 independent correctness review

## Engine 2.0.0 historical capability extension — independent PASS

Scope: opt-in intraday/event-clock execution; historical sector/membership
selection and ranking; mixed completed daily/intraday operands; calendar and
portfolio scalars; conditional sizing; publication-gated news, analyst ratings,
economic releases and Congress disclosures; immutable source bindings; daily
metrics plus timestamped intraday marks. Existing1.4 daily simulations retain
their separate execution path and canonical hashes. Editor changes began only after this independent gate passed.

Independent reviewer: separate read-only `strategy_platform_review` agent.
Initial adversarial findings:

- **P1, protected-source boundary:** valid typed objects mutated with
  `model_copy` could falsely mark future intraday bars available early; source
  review status was checked by the API but not direct simulation. The engine now
  reconstructs/validates isolated source models, requires reviewed revisions,
  and filters history by maximum publication/source/completion clocks. The
  reviewer independently reproduced both cases and verified rejection after
  the fix. Owner regression: source chronology/review boundary test.
- **P1, recycled ticker identity:** a queued/full or protective exit could sell
  an old holding against a new company's quote and remove the identity evidence
  before the later guard. Every held security is now checked before any range,
  quote, valuation or exit at each event clock; identity/listing transitions
  require explicit terminal-action/valuation history. The original independent
  reproduction now rejects. Owner regressions cover ordinary and protective
  exits.

Independent completed checks include exact1.4 legacy configuration,
profile and full-result baselines; hand SGD costs/FX/benchmark/gross replay;
split/dividend/monthly-flow TWR; partial-sale basis/holding locks; delayed IPO
membership; current/prior split epochs; future price/FX/classification/news prefix
isolation; partition order; public/private news, amendments and score clocks;
analyst/economic version clocks; Congress disclosure timing and amount bounds.
The reviewer independently completed **16 financial/causal groups**, including
2,041 exact Decimal streamed-indicator/prefix comparisons. Three complete
pre-extension1.4 configuration/profile/full-result baselines remain identical.
29 focused implementation tests also passed independently. Both original P1
reproductions now reject at the protected boundary, including queued and
protective exits against a recycled ticker.

An owner reproducibility correction canonicalizes event clocks to UTC before
processing. The reviewer separately reversed UTC/+08:00 partitions and obtained
exact full-result equality, then reran all earlier independent groups and legacy
baselines. No unresolved correctness finding was reported. **This bounded PASS
clears the gate before editor work for this extension.** It does not certify
actual historical sources, source rights/vintages, full-period intraday capacity,
deployment or UI behavior. Private scripts and machine-readable findings,
reproductions and verification are archived under
`.local/strategy-platform-20261105/review/`.

## Engine 1.4.0 funding and granular execution gate (2026-11-05)

Status: **independent backend review PASS, before editor changes**. Reviewer:
separate `funding_execution_review` agent, read-only source review and independent
adversarial harnesses, not just the implementation test suite. Scope: optional repeated
entries, schedules, target allocation/partial exits, monthly contributions,
cash-flow-neutral metrics and continuous period reports. Engine 1.3.0 real-data
acceptance and earlier immutable runs remain historical evidence for that engine.

Reviewer independently checked linked opening-flow TWR and actual/365 MWR,
period P&L/drawdown, same-funded benchmark and gross replay, split/dividend
chronology with distinct opening/closing SGD FX, repeated additions/partial sales
and exact pooled-basis residuals, allocation/slot constraints, protective gap
cancellation of queued additions, future price/FX prefix isolation, long exact
reruns, and config/profile serialization. Seven adversarial groups passed;
the previous independent 2,520 oscillator comparisons and SGD/corporate-action
hand ledger also pass against 1.4 source. A separate built-1.3 versus source-1.4
comparison matched complete legacy configuration/profile/result hashes.

Review findings corrected and verified before PASS: the initial holding-period
check blocked additions; it now constrains ordinary sells from the latest
addition only. The initial additions flag also blocked target trims; trims now
work with additions disabled. No unresolved correctness finding was reported.

Evidence: independent scripts `funding140-independent.py`,
`legacy140-hash-review.py`, `engine130-independent-review.py` retained privately
under `.local/engine-1.4-review/`. Four retained 1.2 financial result baselines
also match 1.4 output exactly, including complete orders/ledger/metrics and hashes
(`.local/engine-1.4-reference-verification.json`). This is a bounded synthetic
financial review, not new historical performance acceptance. Pooled partial-sale
statistics count exit tranches; holding locks reset conservatively on additions;
MWR is bounded and available only for horizons of at least 365 elapsed days.

## Engine 1.3.0 extension — PASS, 2026-11-05

The new MACD/stochastic operands and publication-gated external strategy inputs materially extend engine behavior. The separate read-only `engine_130_review` reviewer completed the mandatory review before strategy-editor work resumed. Engine 1.2.0's passing review below remains historical evidence. Status: **PASS within the bounded extension scope**, with no unresolved correctness blocker reported.

Scope includes indicator seeds/warm-up, delayed publications and crossovers, reviewed immutable source binding, worker/net/gross replay, next-open execution, cash/FX/cost accounting, corporate actions, metrics and reproducibility. Four explicitly synthetic baseline cases were captured from the built 1.2.0 image, including SGD fees/FX and split/dividend accounting, under ignored `.local/engine-1.2-reference.json`.

Independent finding P1: mixed price/external crossover's previous leg used today's already split-adjusted history. With prior close 120, a 2:1 split and today's close 60, comparing against external 100 falsely used prior 60 and missed the crossing. Filtering timestamps alone could not reverse today's rebasing. Correction: share `split_history` over raw bars, materialize current/prior histories separately using actions effective AND available at each clock, and propagate the prior history through recursive expressions. The reviewer separately verified the corrected split-day signal and next-open fill, including a split preannounced before the prior decision (it still cannot rebase prices before its effective date). The owner added an engine regression. Existing price-only crossover semantics are unchanged.

Independent verification:

- 2,520 MACD/stochastic comparisons against separately written EMA/smoothing calculations, varied periods and warm-up boundaries.
- Hand-ledger SGD scenario: 70 shares at USD100, FX1.35, fee2.50; 2:1 split to140 shares; USD140 dividend becomes SGD189. Ending equity10186.50, cash736.50, gross return0.0189 and net0.01865 (float metrics compared with tolerance; Decimal cash exactly). Exact full-result rerun.
- Equal-instant publication timestamps with different timezone offsets and input orders; split effective-date isolation; delayed observations and frozen input boundaries.
- 74 targeted tests independently rerun, covering new inputs, prior Milestone3 adversaries, engine, strategies, workflow, temporal isolation, corporate actions, risk and metrics.

Owner verification, separate from the independent checks: **109 backend tests including PostgreSQL pass**; Ruff lint/format pass. All four complete results exactly match captured engine1.2 outputs after the fix: hold/SGD `1c3a324130a4b76160f923c2f3f2cae50d6b8f197e7aafb439750aaa67809e38`, MA/SGD `8826b9542be41c4cef1dd8266d1c6ef46af50a63349eb238d3466d775d9e420b`, RSI/SGD `ed8c9e0b67fe397ed97a4f31520446e1e182e65b9ec603f346720e4f926b98e8`, hold/SGD/split/dividend `1393f288a9fde0b875a489d881dc34a46a8e14b1f58b5ff2924e9e34acb1b3dd`. Private comparison report: `.local/engine-1.3-reference-verification.json`.

Limits: source publication claims and data rights are not certified. External snapshots represent one value per observation date, not a replay of subsequent revisions. No real-data financial acceptance is claimed. Existing full-fill/daily execution and reporting assumptions remain. This finding, correction and independent recheck clear the required gate before editor changes for this extension.

## Earlier engine 1.2.0 review

Status: **PASS — Milestone 3 review gate cleared for engine 1.2.0**. No strategy-editor code has changed during this review.

The user added a mandatory independent review after Milestone 3 and before Milestone 4. The strategy editor already existed when this instruction arrived; this review applies retroactively before further editor work. Baseline: `6d508da`, engine 1.1.0. Existing test results and synthetic demonstrations are evidence of covered cases, not proof of financial or temporal correctness.

Scope: event ordering at open/close; daily-bar and FX availability; indicator history; pending/protective orders; quantity and exposure constraints; Decimal cash/cost-basis/P&L accounting; splits/dividend receivables; final marks; metrics and reproducibility. A separate read-only reviewer audits the baseline independently. The implementation owner separately reproduces candidate defects and adds regression tests. Findings and final reviewer verification will be recorded here before the gate clears.

## Independent findings and disposition

The separate `independent_engine_review` reviewer audited baseline `6d508da` without editing files or being supplied the implementation owner's candidate findings. All five were independently reproduced with synthetic valid inputs. Baseline line references below refer to that commit, not to the corrected worktree.

| Priority | Baseline location | Reproduction and impact | Correction |
| --- | --- | --- | --- |
| P1 | `backtesting/engine.py:102–103` | Change only execution-day final volume from 1,000 to zero: an earlier opening fill becomes rejected before that volume exists. | Remove final-volume gating from opening execution. Full fills assume the supplied opening quote is executable; liquidity is not inferred from future data. |
| P1 | `backtesting/engine.py:140–178` | With a one-order daily limit, one symbol's close-booked stop consumes the quota before another symbol's opening gap stop. Mutating only the first symbol's later low changes the second symbol's earlier fill. | Separate all opening events from range-based close events. Process opening protection before queued market orders, then closing protection; keep stable ordering for simultaneous events. |
| P2 | `backtesting/engine.py:109–123` | Starting equity 10,000, fee 100, 50% limit, prior close 100: 49 shares fill at next open 101.5. Exposure becomes 4,973.50 / 9,900 = 50.237%, violating the limit. | Share one pure execution-cost quote between risk and ledger; constrain marked notional using post-cost equity. |
| P2 | `backtesting/engine.py:154–161` | Entry 100, stop 90, take 110; next open 120 and later low 80. Baseline records stop 90 at close despite the known opening take-profit. | Honor a protective level crossed at the open before consulting later high/low. Retain stop-first only for genuinely ambiguous intraday ranges. |
| P2 | `analytics/metrics.py:13` | Capital 100, fee 10: buy one share at 90, sell at 10, then remain at zero. A later flat session divides by zero and fails the run. | Record the first total loss as −100%; subsequent absorbing zero-equity sessions use 0% daily returns. Reject negative or unexplained recapitalized equity. |

All five are fixed in engine **1.2.0**, execution model `chronological-open-close-v2`. Baseline regression tests were observed failing before fixes; the reviewer separately reran all five original scenarios against the correction.

## Additional boundary defenses

- A directly constructed `DataView` formerly trusted early availability metadata enough to expose a future session. Normal imports rejected that metadata, but the protected view itself did not. The view now independently checks exchange completion and source/availability timestamps for current and historical cutoffs, and the simulator revalidates dataset timestamps on entry.
- An unsupported `Ledger.execute` side could bypass sell-quantity validation and book fictitious proceeds. The engine's typed order schema did not emit such a side; the ledger boundary now rejects it before state mutation and also rejects nonfinite/nonpositive execution inputs.

## Verification

- `tests/test_milestone3_review.py`: nine adversarial cases pass, including separate allocation/exposure checks, opening-fill invariance, cross-asset intraday invariance, monotonic ledgers, known opening protection, malformed data boundaries, rejected-side atomicity and total-loss metrics.
- The independent reviewer inspected the patch, reran all five independent reproductions, and additionally verified that an opening protective exit cancels a queued ordinary exit without duplicate execution or fees. All six independent checks passed, as did 44 selected financial/temporal/indicator/audit tests. No unresolved defect was found within that bounded scope.
- The owner ran the full backend suite with PostgreSQL enabled: **54 passed**, including worker persistence and transactional claim tests. Ruff lint and formatting checks pass.
- The full four-run PostgreSQL synthetic acceptance demonstration completed under engine 1.2.0: all jobs persisted successfully; original strategy-version results stayed unchanged after publishing revised periods and editing profile fees; every earlier signal, eligible fill and equity value remained identical after later price/volume/FX mutation. Measured results are regenerated in `demo-report.md`; the local execution record is `.local/review-engine-demo-report.json`.

## Review limits

This is an independent code and adversarial reproduction review, not a certification of every financial assumption, vendor history or corporate-action source. Full fills, executable opening quotes, conservative close-booked intraday protection, source action attestations, and price-only versus dividend-complete interpretation remain explicit model limitations. Docker and credentialed real-data/LLM verification remain outstanding.

Existing completed results were not rewritten. Engine 1.1.0 results remain historical artifacts and must be rerun to apply these corrections. The editor already existed before this gate was requested; the independent reviewer's passing fix verification, full 54-test regression, and successful refreshed acceptance scenario now satisfy the gate before any further editor work. No editor implementation was changed in this pass.
