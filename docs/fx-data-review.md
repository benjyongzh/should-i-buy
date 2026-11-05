# USD/SGD source preparation and review — 2026-11-05

## Follow-up: accepted combined SPY reference-FX revision

The2016–2025 candidate has now been reviewed and imported into combined dataset `051e4285-e374-4b44-b82c-a54ffc8a6a6e`. All2,494 numeric values match a fresh ALFRED output_type4 retrieval;115 missing initial values stay omitted. All6,033 required2018–2025 clocks pass14 days, maximum age12.3541667 days. After the conservative correction, seven days fails at2,142 clocks.

Review uses ALFRED first-vintage metadata as the publication authority, with a following-week release floor and next-midnight New York boundary. One impossible same-day vintage for 2018-07-23 is delayed to2018-08-01 after the appropriate weekly table's evidenced July31 release, retaining value1.3653. The2021-03-12 value matches the March15 table; its later FRED availability is retained. Missing initial values are not replaced, including2021-02-24. Failed constructed URLs and conflicting current archive labels have explicit dispositions: those pages are not accepted as original publication clocks. This is acceptance of the stated bounded FRED/reference-rate policy, not a claim to have reconstructed every original intraday release or repaired every publisher archive.

Full review/evidence are `.local/combined-spy-20261105-v2/fx-source-review.json`, raw source responses, `fx-reviewed.csv` and the hashed review manifest. [Real SPY acceptance](real-spy-acceptance-2026-11-05.md) records the completed six runs/six exact repeats and independent calculations. Original candidates below remain unchanged; their unaccepted status describes the earlier preparation stage.

Status: **FRED authentication and initial-release retrieval pass; a candidate CSV is prepared. It has not been accepted/imported into an application dataset.** Original-release source reconciliation still has flagged evidence to review. Corporate-action reconciliation also remains outstanding. Engine 1.2.0, existing profiles, immutable revisions and running services were unchanged.

## Actual retrieval and artifacts

The supplied `FRED_API_KEY` was read only inside a disposable preparation process. A v1 `series/observations` request for `DEXSIUS`, `output_type=4`, returned HTTP 200. Explicit bounds: observation dates 2017-12-01–2022-12-31; real-time dates 1776-07-04–2023-01-31. Earlier observations seed the first 2018 clock; late-2022 observations published in January 2023 cannot enter earlier clocks. Pagination count/offset and query metadata are checked. No latest-value export, interpolation or synthetic fallback was used.

| Item | Result |
| --- | --- |
| Returned observation rows | 1,326 |
| Numeric initial-release observations | 1,266 |
| Explicit missing values omitted | 60 |
| Distinct FRED initial-release dates | 266 |
| Rows matching corresponding Fed archive table | 1,245, including matching missing markers |
| Observation/value lookup mismatches | 12; these are review flags, not proof of 12 wrong rates |
| Archive URLs returning HTTP 404 | 7 |
| Archive page date-label discrepancies | 7 |

Private, Git-ignored artifacts:

- `.local/fred-fx-20261105-audit/usd-sgd-candidate.csv`
- `.local/fred-fx-20261105-audit/report.json`: all query parameters except the key, coverage results, discrepancies, source URLs and raw-response SHA-256 hashes.
- `.local/fred-fx-20261105-audit/raw/`: original FRED JSON and 259 downloaded Fed HTML release pages. Seven URLs returned 404; all 266 dates were attempted.
- CSV SHA-256: `7dfa698560f8d975dc6e618427f5cd5468a6cbe840dca58fac03322690e765fd` (includes the CSV writer's line endings).

An earlier incomplete attempt is retained under `.local/fred-fx-20261105/`. The audited attempt resumed after accommodating the Fed's older table layout and recording unavailable/conflicting evidence; cached originals were reused. Completed preparation output directories cannot be overwritten by the script.

## Proposed availability policy and measured age

Rate units are SGD per USD. `observed_at` is noon on the observation date in `America/New_York`, respecting DST. `available_at` is **midnight New York after the FRED initial-release date**. This is a deliberately conservative date-only boundary, not a claim that publication occurred at midnight. The [Fed describes these as noon buying rates and says dated past releases are not revised](https://www.federalreserve.gov/releases/h10/about.htm); [FRED documents output type 4 as initial release only](https://fred.stlouisfed.org/docs/api/fred/series_observations.html).

This policy retains initial-release values only, rather than replaying all subsequent revisions. Missing initial values stay missing. It models lagged published reference FX, not a broker's executable bid/ask or conversion rate. The source discrepancies below must be resolved or explicitly dispositioned before this candidate is accepted.

Measured against the actual engine's `fx_at`, at session open, close and the Alpaca 20:30 New York decision time:

| Interval | Clocks tested | Failures at 7-day age | Failures at 14-day age | Maximum observation age |
| --- | --- | --- | --- | --- |
| 2018–2022 | 3,777 | 1,346 | 0 | 12.3541667 days |
| Requested 2019–2022 backtest | 3,024 | 1,073 | 0 | 12.3541667 days |

The requested-period worst clock is `2020-12-08T01:30:00Z` (December 7 decision time in New York); it selects the November 25 noon observation, available December 1 midnight New York. There was an eligible rate at every tested clock. The default seven-day setting is unsuitable for this candidate. A future acceptance profile would need an explicitly documented setting such as `max_fx_age_days=14`, followed by a fresh age audit if source/availability policy changes. No profile setting was silently relaxed.

## Evidence still requiring disposition

The audit intentionally compares each observation against the archive at its FRED initial-release date. That mapping is not universally sufficient: a late-ingested observation can belong to an earlier weekly table, and a missing first release may differ from an issuer table. These cases must be investigated, not automatically rewritten or treated as incorrect data.

- Lookup flags: 2018-07-23; 2020-07-03, 2020-11-26/27, 2020-12-24/25; 2021-01-01, 2021-02-24, 2021-03-12, 2021-12-24/31; 2022-11-11. Most are missing initial observations not present in that particular weekly table. On 2021-02-24 FRED's initial value is missing while the corresponding archived table has a numeric value. The missing observation was omitted rather than replaced. No unequal numeric-to-numeric pair was reported by this lookup.
- HTTP 404: release URLs 2017-12-18, 2018-01-16, 2018-05-29, 2018-07-31, 2018-09-04, 2019-02-04 and 2019-08-26. A constructed URL failing is not evidence that no release existed; consult the official release index/alternative archival paths.
- Date labels disagree with the FRED date/URL for 2019-02-25, 2019-05-28, 2019-11-12, 2020-01-06, 2020-01-13, 2020-01-21 and 2020-05-18. For example, [the 20190225 URL labels its release February 27](https://www.federalreserve.gov/releases/h10/20190225/). Do not infer an exact earlier publication time from the URL.

Next review: resolve alternate release URLs; reconcile delayed observations against the appropriate earlier tables; compare date-label conflicts with FRED vintage/release metadata and archived publication evidence. Record the chosen disposition and rerun the clock audit before combining with equities/actions. No unsupported availability timestamp or replacement rate should be introduced merely to clear a check.

## Reproduction and tests

The standalone utility is `backend/scripts/prepare_fred_fx.py`; it prepares files only and has no application-database/import/publication operation. From the repository root, using the existing Linux verification image:

```bash
docker run --rm --env-file .env \
  -v "$PWD:/workspace" -w /workspace/backend \
  trading-lab-linux-verify-20261104-api \
  python -m scripts.prepare_fred_fx --output-dir /workspace/.local/fred-fx-new-review
```

Choose a new output directory for a new completed source snapshot. `--resume` may reuse cached raw files only for an incomplete preparation; completed reports are protected. Native execution reads `FRED_API_KEY` from the process environment; putting it in `.env` alone does not load it into a native process. No app container recreation is required for this preparation workflow. Outbound archive requests are spaced and credentials/query-bearing errors are suppressed.

All **73 backend tests pass including PostgreSQL**; Ruff lint/format checks pass. Ten preparation cases cover publication boundaries/DST, missing/invalid/duplicate/reversed observations, actual observation-based FX age, year boundaries and both archive layouts, sanitized errors, unresolved-evidence flags and completed-output preservation. Automated tests use controlled inputs and block real HTTP. This live audit is separate evidence. The unchanged frontend's prior 10 tests/build remain the latest frontend checks; they were not rerun for this backend-only preparation addition.
