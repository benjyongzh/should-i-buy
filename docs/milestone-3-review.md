# Milestone 3 independent correctness review

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
