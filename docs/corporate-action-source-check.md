# Alpaca / issuer corporate-action check — 2026-11-05

## Follow-up: issuer reconciliation and publication evidence completed for SPY

Combined dataset `051e4285-e374-4b44-b82c-a54ffc8a6a6e` now retains40 reviewed issuer dividends for 2016–2025. US ex/payment dates and full-precision amounts come from the issuer workbook. Every amount matches an original dated issuer USD announcement in the ASX archive, published before the US effective open; the minute-level Sydney broadcast time is rounded forward one minute. No Australian CDI ex/payment date or AUD conversion is imported. This closes the missing2018-06-15 row/seven payment dates without fabricating fields. The issuer's2020-06-19 precision is retained, with the Alpaca difference documented.

The43 retained candidate notices include originals/amendments and one later FX notice that is explicitly excluded. US workbook/Alpaca agreement resolves an Australian notice's incorrect2025 December US payment date; January30,2026 is retained. Split coverage review combines empty Alpaca action responses, identical raw/split-adjusted OHLCV over all2,514 bars and an independent publisher's zero-split history. It is a bounded source review, not a guarantee of vendor completeness.

Details and hashes are in `.local/combined-spy-20261105-v2/corporate-action-review.json` and its manifest. [Real acceptance results](real-spy-acceptance-2026-11-05.md) now include actual dividend entitlement/payment/final-receivable reconciliation. The dated diagnostic below records the earlier Alpaca-only limitations; its statement that no reviewed actions were imported is superseded for the new SPY combined revision.

Read-only live checks used the configured Alpaca market-data keys at `GET https://data.alpaca.markets/v1/corporate-actions` for SPY cash dividends, forward splits and reverse splits. Both requests returned HTTP 200; all page tokens were followed and both responses ended without another token. No subscription, running service or application dataset was changed.

The endpoint filters by **process date**, not ex-date. The 2018–2022 query used 2018-01-01–2023-02-01 to include January payments; the 2022–2025 query used 2022-01-01–2026-02-01. Results were then filtered to the intended ex-date interval for comparison with the US State Street historical distribution workbook. The latter request includes one December 2021 ex-date paid in January 2022; it was excluded from the 2022–2025 count.

| Ex-date interval | Issuer rows | Alpaca rows | Findings |
| --- | --- | --- | --- |
| 2018–2022 | 20 | 19 | Missing 2018-06-15; seven returned records lack payment dates; one tiny amount discrepancy |
| 2022–2025 | 16 | 16 | All amounts and payment dates match |

Missing payment dates: 2018-03-16, 2018-09-21, 2018-12-21, 2019-03-15, 2019-06-21, 2019-09-20, 2019-12-20. The 2020-06-19 amount is issuer USD 1.366242/share versus Alpaca USD 1.3662419/share, a difference of USD 0.0000001/share. All comparable populated payment dates match. No numeric discrepancy was silently reconciled or rounded into an imported dataset.

Neither response supplies declaration/publication timestamps. No forward/reverse split records were returned; an empty response alone cannot certify split completeness. Alpaca's [endpoint documentation](https://docs.alpaca.markets/us/reference/corporateactions-1) explicitly warns about delayed receipt/availability. `process_date` is not a historically valid substitute for an announcement timestamp.

Private artifacts retained under ignored `.local/alpaca-actions-20261105/`: raw API JSON pages and their hashes in `report.json`, issuer workbook `issuer-distributions.xlsx`, and exact comparison in `issuer-reconciliation.json`. The primary workbook is linked from [State Street's US distributions page](https://www.ssga.com/us/en/intermediary/resources/documents/etf-dividend-distributions).

Conclusion: Alpaca is a useful second source and newer SPY dividend coverage is materially better in this check. Its historical action response alone does not clear the existing point-in-time review. Reconcile issuer records for missing fields/rows and rounding, review split coverage separately, and obtain declaration evidence before creating a reviewed combined revision. This diagnostic did not import actions or create real backtest returns. No 2023–2025 equity/FX history has yet been imported by this check.
