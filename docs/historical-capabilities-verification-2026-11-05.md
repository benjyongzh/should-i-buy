# Historical capability verification — 2026-11-05

Engine **2.0.0** is deployed in isolated Compose project
`trading-lab-linux-verify-20261104`, at **127.0.0.1:18080**. It adds opt-in
intraday/event execution, historical selection and conditional sizing. Existing
daily strategies use the retained compatibility path. No completed result was
rewritten, and no other project's container or database was modified.

## Demonstrated

| Check | Actual result |
|---|---|
| Independent financial/causal gate | PASS before editor work; 16 independent groups, 2,041 exact Decimal indicator comparisons, legacy baselines and adversarial source/identity/clock checks. Findings/fixes are in [Milestone 3 review](milestone-3-review.md). |
| Backend | `python -m pytest`: **183 passed**, including PostgreSQL migrations, immutable triggers and worker integration. `python -m ruff check .` and formatting pass. Provider tests block unmocked network access. |
| Frontend | `npm test`: **31 passed**; TypeScript/Vite production build and Prettier pass. Vite still reports the existing large-bundle advisory. |
| Docker | API/worker/migration/frontend images built. Migration **004** applied to this project's existing PostgreSQL; `alembic check` reports no drift. API/database/frontend healthy; separate worker running and processing jobs. |
| Browser | **17 passed** in real disposable Chromium: actual intraday chart/balance, markers/references, conditional-size fill reason, disclosure evidence, cutoff filtering, two separate approval attestations, immutable review child, source picker, saved timing/universe controls, mobile chart sizing and no runtime/API failures. A selector-label issue found in the first pass was fixed and verified. Screenshot inspection also corrected compact axis rounding for small monetary ranges. Focused screenshots were inspected. |
| Synthetic deployment acceptance | HTTP source import → explicit review → published strategy/profile → queued worker → completed result → exact repeat; delayed news, subscription analyst upgrade and public Congress disclosure jointly control the first trade. Independent Decimal arithmetic reconciles the fill, cash and ending equity. |
| Real provider access | Existing Alpaca credentials returned **78 raw SIP five-minute SPY intervals for 2018-01-02**, and **17 AAPL/MSFT news records for 2020-01-02**, through deployed preparation endpoints. Both revisions are retained **unreviewed/incomplete**, not backtest-certified. Seven news records have update clocks later than creation. |
| Live LLM | Two configured-model planning calls returned valid schema: once/10%-cash SPY with one-hour window, then 20%-cash plus public COMPANY_NEWS condition. Selected timing/sizing/news semantics were checked. Proposal creation did not change drafts; acceptance edited drafts only; separate publication retained v1 and v2. Unsupported-plan blocking also passes mocked API/UI tests. |
| Persistence/isolation | API/worker/frontend restart preserved **10 earlier complete result hashes**, both new synthetic result hashes, **14 raw/reviewed source exports**, LLM versions, profile and reviewed daily dataset export. This project's database container remained unchanged. All **22 unrelated containers** retain their IDs, start times, restart counts and port bindings. |

The browser is a bounded workflow smoke test, not an exhaustive usability,
accessibility or browser-compatibility certification. The worker has no separate
health endpoint; running state and successful queued work demonstrate connectivity.

## Explicitly synthetic financial smoke

Runs `76c7f9c5-bf74-47fa-b634-3d8072818b3f` and
`cb2ad3a6-8582-4602-9fef-56648c68f41e` are **synthetic**, not historical SPY
performance. Fixture period: 2020-01-02–03, SGD10,000 plus a fixed SGD500 monthly
injection, SGD2.50/order, 0.05% slippage and deliberately defined USD/SGD1.35.
News is available 15:15Z, an analyst change 15:25Z, and the Congress disclosure
15:35Z; its transaction date is earlier. The first order is submitted at 15:35Z
and fills strictly later at **15:40Z**, within the one-hour-after-open window.

The fixed SGD1,000 budget buys seven shares at USD100.05:
`7 × 100.05 × 1.35 + 2.50 = SGD947.9725`. Cash is SGD9,552.0275;
seven shares marked at USD100 produce ending equity SGD10,497.0275. No entry
condition passes before the disclosure. Two daily and 160 intraday marks are
retained. The same-funded cash reference ends at SGD10,500. Both complete result
payloads have hash
`b48f2cabb7b3d6f3507bd72d136d0bffeb5843c5e42b007f1f70be6497fa7d0d`.

## Unverified or blocked by missing inputs

- **No new real news/ratings/Congress/sector-driven or full-period intraday
  strategy performance is claimed.** Real provider access is demonstrated for
  the bounded slices above; original publication-vintage completeness is not.
  Current revised news is gated at its update clock, which cannot recover the
  unavailable earlier text. Approving such history as complete would be wrong
  without originals/coverage evidence.
- Existing FRED/Alpaca/LLM credentials work or were verified in prior acceptance.
  **Benzinga ratings is not configured**; direct live ratings access remains
  blocked without `BENZINGA_API_KEY`/entitlement and a verified source timezone.
  Timestamped file imports need no new key. No paid plan was purchased.
- Real historical sector/member/security identity states and additional equities'
  complete accounting datasets are not supplied. Current sector metadata would
  introduce hindsight/survivorship bias.
- Congress typed import, amendment handling, amount bounds and disclosure-clock
  strategy rules are implemented/tested. **Real collection, ticker normalization
  and public-posting-time review are outstanding.** No automatic official-site
  scraper was added. Transaction/filing dates are not substituted for public time.
- No qualified original-vintage Fear & Greed history or comprehensive geopolitical
  archive is configured. Macro surprise rules need historical pre-release
  consensus; a FRED API key does not supply that input.
- Full 2018–2025 multi-source/intraday capacity, halts, delisting/merger settlement,
  source-rights certification, actual order-book execution and executable
  intraday FX are not verified/implemented. Hard limits reject oversized runs;
  unsupported terminal identity/valuation transitions fail explicitly.
- Earlier [real SPY daily acceptance](real-spy-acceptance-2026-11-05.md) and
  [funded daily smoke](funding-verification-2026-11-05.md) retain their original
  engine/source assumptions; they are not relabeled as new 2.0 source acceptance.

## Evidence and reproduction

Private evidence is retained in ignored `.local/strategy-platform-20261105/`:
`review/`, `integration.json`, `providers.json`, raw-stage normalized provider exports,
`llm.json`, `browser-report.json`, screenshots, pre/post-restart hashes and
`verification-final.json`. It contains source/runtime data and is not committed.

Use the existing project selector and environment file for deployment commands:

```bash
docker compose -p trading-lab-linux-verify-20261104 --env-file .local/compose-linux-verify.env ps -a
docker compose -p trading-lab-linux-verify-20261104 --env-file .local/compose-linux-verify.env run --rm --no-deps migrate python -m alembic check
```

The next input actions are listed in the [data/key checklist](historical-input-checklist.md).
The supported semantics are in [strategy capabilities](strategy-capabilities.md).
