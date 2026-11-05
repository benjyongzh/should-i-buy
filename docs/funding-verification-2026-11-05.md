# Engine 1.4.0 funding and sizing verification — 2026-11-05

**Implemented and verified:** optional strategy timing, repeated buys, cash and
target sizing, partial exits, and independent profile monthly contributions.
The backend passed its mandatory independent correctness gate **before** editor
changes. See [review findings and verification](milestone-3-review.md) and
[configuration/accounting semantics](funding-and-trade-controls.md).

## Automated and independent evidence

- `python -m pytest`: **136 passed, including PostgreSQL**; Ruff lint and format
  pass. Fifteen new financial/causal/API tests cover funding dates/midmonth starts,
  no retroactive/future capital, next-open DCA/once behavior, top-ups, partial
  basis/FX/splits/dividends, allocation/position limits, holding restrictions,
  time-weighted returns/drawdown/period P&L, recapitalization, investor IRR,
  immutable profile snapshots and worker exact repeats. PostgreSQL integration
  additionally executes a funded policy, migrations/drift and concurrent claims
  in a random test-owned schema. Automated provider HTTP remains blocked/mocked.
- `npm test`: **20 passed**; Prettier and TypeScript/Vite production build pass.
  Workflows save funding and DCA/partial settings without automatic publication;
  chart tests distinguish deposited balance from normalized performance. These
  are component/HTTP tests; a new interactive browser layout pass was not run.
- Independent reviewer separately exercised seven adversarial financial groups,
  including an actual/365 investor-return equation, and the prior 2,520 oscillator
  checks. Built-1.3 versus source-1.4 legacy config/profile/full-result hashes match.
  Four complete retained engine 1.2 synthetic outputs also match 1.4 exactly.

## Real SPY funded integration smoke

These are **Q1 2019 integration checks**, not new full 2018–2025 strategy
acceptance or investment recommendations. The earlier full-history 1.3 real
acceptance remains preserved and documented separately.

Input: existing immutable reviewed SPY dataset
`051e4285-e374-4b44-b82c-a54ffc8a6a6e`, content hash
`de0dac7e7817309877fe9ef4697b3b047fde1f880e65b7c3de1bf292e47a4ce8`.
New profile `d4968f01-f496-458b-b671-ca2585d47b4e`: 2019-01-01–2019-03-31,
SGD 10,000 initial capital, SGD 500 monthly, SGD 2.50 per fill,0.05% slippage,
whole shares, historical SGD/USD reference FX with the reviewed 14-day limit,
long only/unlevered. Deposits total SGD 1,500 for all three cases and benchmarks.

| Explicit smoke policy | Ending SGD | Investment P&L SGD | Net TWR | Filled orders |
| --- | ---: | ---: | ---: | ---: |
| Once, all available cash | 12,821.0262 | 1,321.0262 | 12.3130% | 1 |
| Monthly DCA, SGD 500 order budget | 11,557.3731 | 57.3731 | 0.5280% | 3 |
| Target 60%, quarter exits above SMA20 | 11,970.7374 | 470.7374 | 4.2868% | 22 |

All three exact repeats match complete result JSON. Primary run IDs:
`6c7d1fe1-4071-4dd0-ba99-64439d91b50c`,
`0284201e-a66b-4a10-ab05-5337aeb1ab94`,
`b108d3d4-7838-42c5-a832-cc85ad8a34cf`.
Repeat IDs: `f4ac4758-2fc5-4327-b791-6150f3ddd807`,
`9172e0e6-75fe-4b7c-80d5-37f87c688a85`,
`21148e70-1ca0-4b80-b703-05d4c5abe19b`.

A separate stdlib-only replay, importing **no application calculation code**,
reconciled every one of **183 strategy and 183 benchmark daily marks**, all 26
strategy fills, 18 exits, costs, pooled basis allocations, action entitlements and
payments, opening/closing historical FX, pre/post-deposit valuations, linked TWR,
drawdown and investment P&L. Benchmark buys were independently reconstructed
from prior-close affordable quantities and next-open risk/cash checks.

Selected independent arithmetic: the first lump-sum order buys 30 shares on
2019-01-03 at raw USD 248.23. Slippage gives USD 248.354115, historical FX 1.3668,
and SGD 2.50 fee. Cash after the initial SGD 10,000 plus SGD 500 contribution is
`10500 − 30 × 248.354115 × 1.3668 − 2.50 = SGD 313.9878685400`.
The DCA variant buys one share on Jan 3, Feb 4 and Mar 4; its SGD 500 order budget
includes costs and leaves unused cash in the account. The target policy's
Jan 8 four-share partial sale uses raw USD 256.82, slipped USD 256.691590 and
FX 1.3594, with cost basis allocated pro rata and conserved to the final residual.

Private runtime evidence/scripts are retained under `.local/engine-1.4-review/`:
`real-results.json`, `real-independent-reconciliation.json`,
`reconcile-real-funded.py`, configuration/version/profile records and exact-repeat
hashes. These files are not committed or substitutes for source provenance.

## Live authoring and deployment

Existing server credentials with `gpt-6-luna` generated monthly DCA and modified
it to target 60% with quarter RSI exits. Both responses passed the current schema
and requested-policy checks. Neither changed the draft until explicit acceptance;
neither created a version until separate smoke publication; older versions stayed
unchanged. Proposal IDs `fa9afde3-ea13-4e11-844b-be390a46d2e3` and
`2665ca61-ac25-4dff-81ac-eb038d1e9104`; versions
`0f630fda-d6ef-402f-bfec-78c5919b2d8a` and
`9c8fb6e3-7d93-4455-acfe-b1f94e283e99`. This does not assess broad model quality.

New images built and migrations ran at head for the isolated
`trading-lab-linux-verify-20261104` project. Only its API, worker and frontend were
recreated; the database container/volume and loopback port 18080 binding were retained.
New worker jobs completed through Nginx/API/PostgreSQL. After a further application
restart, all six new result hashes, four checked legacy result hashes, the dataset
export and new LLM versions remain identical; the new production UI asset is
served successfully. The PostgreSQL container ID is unchanged, and all 22 unrelated
container IDs/start times/restart counts/port bindings match the predeployment
record. API, database and frontend are healthy; the worker is running. Evidence:
`.local/engine-1.4-review/deployment-final.json`.

## Unverified or intentionally limited

No new full 2018–2025 funded parameter sweep, interactive browser session, variable
salary schedule, withdrawals, tax-lot accounting or live execution is claimed.
Full fills, next-open gaps/rejections, whole-share rounding and source-vintage/FX
limits remain. Monthly schedules filter close decisions, so ordinary DCA fills
at the following open. Investor IRR requires 365 elapsed days and is consequently
unavailable for this Q1 smoke. No new keys were required.
