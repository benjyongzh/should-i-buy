# Creating the reviewed SPY combined revision

Executed2026-11-05: new reviewed combined dataset **`051e4285-e374-4b44-b82c-a54ffc8a6a6e`** was imported, then all three strategies completed for 2018–2025 and2019–2022, each with an identical repeat. Independent financial reconciliation passed. See [the acceptance report](real-spy-acceptance-2026-11-05.md) for actual evidence, source-policy dispositions, results and limitations. This runbook's remaining preparation text describes the process and earlier state.

A combined revision is a new immutable market-data import containing raw equity bars, accounting FX and corporate actions. It is separate from approved external signal snapshots. The importer already supports it; no new provider credential or engine feature is needed.

Earlier preparation status: price and FX candidates existed while source findings/action evidence remained open. Review flags record a completed source review; they do not perform it or establish historical availability. Those findings have now received the dispositions and source corroboration recorded in the acceptance report.

## Inputs already retained

- Raw SPY SIP bars: `.local/research-history-2016-2025/SPY-unreviewed.json`, 2,514 bars for 2016–2025. Existing app revision: `77640317-c59e-4030-8950-38c5fab8cfd2`.
- Accounting FX candidate: `.local/context-live-20261105-final/usd-sgd-2016-2025-candidate.csv`, 2,494 observations. Source and age audit: `fx-candidate-audit.json` beside it. Every one of 6,033 required 2018–2025 clocks has an eligible observation; 14-day age passes, seven-day age fails at 2,139 clocks. This does not resolve the separate source-evidence flags.
- SPY issuer distributions: `.local/alpaca-actions-20261105/issuer-distributions.xlsx`. Alpaca source pages and `issuer-reconciliation.json` are beside it. See `corporate-action-source-check.md` for the missing dividend, seven missing payment dates and precision difference.

These are private runtime/source artifacts, not committed fixtures. Preserve them and their hashes. Do not overwrite the existing dataset, profiles or completed results.

## Source review before import

1. **FX:** disposition the archive URL/date/lookup flags in `fx-data-review.md`, retaining evidence for any timestamp correction. Use initial-release values, SGD per USD, and defensible publication availability. Missing initial observations remain omitted; do not substitute today's revised history. Re-run the full-period clock/age audit if availability changes. The explicit 14-day reference-rate policy is a modeling choice, not an exemption from the audit or an executable broker quote.
2. **Dividends:** reconcile the issuer's ex-dates, full-precision amounts and payment dates against Alpaca, including the missing 2018-06-15 record. Record the authority chosen for every difference. Review 2016–2017 warm-up coverage as well as 2018–2025; retain actual payment dates beyond 2025 where applicable. Keep announcement evidence separate from a distribution schedule: publishing a schedule is not necessarily publishing the amount.
3. **Splits and availability:** review effective split coverage independently. An empty Alpaca response is not proof of no splits. Establish each action's historically defensible `available_at`; current validation requires it no later than the effective US session open. Do not infer an earlier timestamp from ex-date alone. An unresolved required timestamp remains unresolved rather than being fabricated.
4. **Review manifest:** retain source URLs/files and hashes, source ranges, unresolved/dispositioned findings, transformation rules, any corrected rows, action timing evidence, split-review evidence, FX-age results and reviewer/date. Hash the completed manifest and reference it in the dataset availability policy. The present JSON schema has no separate structured review-manifest field; retain the full manifest beside the source bundle.

## Assemble and import

Use the existing `GET /api/market-data/datasets/{id}/export`, or the retained raw SPY JSON. Preserve all bars exactly, `adjustment_policy=raw`, and the existing Alpaca `decision_time=20:30_America/New_York` convention. Attach the reviewed FX rows and action rows, give the combined revision a descriptive new name, and record the combined source/availability policy.

Accounting CSV contracts:

- FX: `observed_at,available_at,rate` (optional pair is USD/SGD).
- Actions: `symbol,session_date,available_at,kind,value,payment_date`. Dividend session dates are ex-dates; values are USD/share. Splits use the new/old share ratio and omit payment date. Timestamps must include timezone offsets.

Validate the assembled payload as `DatasetInput`, run `validate_dataset` and `validate_coverage` with the actual target profile, and retain the results. Set `corporate_actions_reviewed=true` and `dividends_complete=true` only after the corresponding review has passed. Submit the payload to **`POST /api/market-data/import`**. This reuses the existing bars and avoids the Alpaca-fetch endpoint's five-year request limit. The UI alternative is a fresh CSV import with all three files and the same decision-time convention; do not refetch or mutate the old revision just to attach inputs.

Retain the returned dataset ID/hash. Export it again and compare all component values/hashes with the reviewed bundle. Verify coverage, FX/action counts, flags and availability policy. Import success is distinct from backtest acceptance.

## Integration and financial acceptance

Use the existing continuous 2018–2025 profile with SGD 10,000, SGD 2.50 per executed order, slippage 0.0005, whole shares and the documented 14-day FX policy. Earlier profiles remain unchanged. Publish explicitly defined buy-and-hold, SMA20/50 crossover and RSI strategies; retain sizing/threshold choices in their immutable versions. Schedule all three against the new combined dataset/profile snapshots.

Check selected fills, opening/valuation FX, fees/slippage, cash affordability, split effects, ex-date entitlement, payment-date cash, unpaid final receivables and final marked holdings independently. Repeat identical runs and compare complete results, then inspect year/quarter/month reports on the continuous portfolios. Record actual outcomes and remaining limitations in `verification.md` and `known-limitations.md`. Full-period iterative development remains in-sample research. No real-data acceptance is established by this runbook alone.
