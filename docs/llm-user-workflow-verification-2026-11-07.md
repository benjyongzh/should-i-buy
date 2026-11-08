# Live strategy-prompt workflow verification — 2026-11-07

The user explicitly approved testing the configured external LLM, including strategy
configuration and a compact derived backtest summary. Seven live prompts were typed
into the actual **Strategy assistant prompt** textarea in the Docker-served editor
on `http://127.0.0.1:18082`. These were live UI → application → OpenAI calls,
not mocked responses or direct provider calls standing in for the UI.

The earlier disclosure-approval blocker is resolved for these tests. The endpoint
was `https://api.openai.com/v1`, model `gpt-6-luna`, using the existing server-side
`LLM_API_KEY`, `LLM_MODEL` and `LLM_BASE_URL` configuration. No key, raw market archive
or account credential was included in the user prompts. No new key is required for
the daily indicator workflows tested here.

## Prompt acceptance matrix

| User request | Actual result | Application latency |
| --- | --- | --- |
| Use an AAPL 2018–2025 result summary; lower **only** the RSI14 entry threshold from 30 to 25, preserving all other fields/profile | Exact one-field change; accepted through review and explicitly published as v2 | 11.6s |
| Replace with monthly buys using 20% available cash; require close above EMA200 and volume above its 20-session average; allow additions; daily RSI14 above 65 sells half; salary funding stays in the profile | Correct conditions, cash sizing, monthly entry/daily exit schedules, additions and half exits; reviewed and published as v3 | 18.1s |
| Change only monthly buys to weekly and 20% cash to a fixed SGD 500 budget | Exactly those sizing/schedule changes; existing conditions/half exits preserved; reviewed and published as v4 | 13.6s |
| AAPL/MSFT Technology selection requiring public positive news, analyst upgrades and publicly disclosed Congressional purchases | First response unnecessarily marked weekly scheduling/profile currency unsupported, although those were representable. Retained as an authoring failure; not accepted | 38.2s |
| Clarify the previous request: use the supported weekly convention and independent SGD profile; missing sources are readiness requirements | Correct sector/symbol/event conditions and publication/disclosure requirements; schema supported, data readiness blocked; not accepted or published | 27.5s |
| Restrict buys to 60 minutes after regular market open while retaining completed daily indicators | Generated intraday window with daily expression wrappers and matching source/profile requirements; daily-data readiness blocked; not accepted or published | 17.7s |
| Use tomorrow's closing price today, short AAPL with 3× leverage; block rather than substitute | Null configuration plus explicit unsupported requirements; UI acceptance disabled and server acceptance rejected | 3.1s |

These are single observed responses, not quality or latency guarantees. All seven
responses were schema-valid. The false refusal is a real limitation: structured
output validation does not establish faithful interpretation. Clarification helped
in this instance; no automatic semantic repair or prompt/model change was made.

The monthly replacement selected `good_until_cancelled` pending expiry; the narrow
weekly amendment preserved it. The proposal JSON exposes this setting for review.
The user did not specify expiry explicitly. Half exits can recur on successive
eligible days while RSI remains above 65, with whole-share rounding leaving dust.
Fixed-notional 500 is an account-currency **budget including the fixed fee**, not a
promise of exactly SGD 500 invested or executed at a later opening price.

## Review, publication and data gates

The first browser harness passed 39 named assertions; follow-up browser checks
passed eight more, plus the clarified proposal's semantic/source checks:

- Each proposal left the saved draft and version history unchanged.
- The review checkbox was initially unchecked and **Accept into draft** disabled.
  Acceptance advanced only the draft revision; a separate **Publish new version**
  click created an immutable version with its parent ID and LLM metadata.
- Duplicate acceptance returned409. Saving the draft made an older unaccepted
  intraday proposal stale; attempting acceptance then returned409.
- Unsupported/blocked proposals could not be accepted, including forced server
  requests returning422. No missing-data plan was published or backtested.
- The combined news/ratings/sector/Congress plan failed readiness with
  `historical classification/membership revision required`. Validation reports
  the first encountered blocker. Separate **validation-only diagnostics**, never
  published or run, isolated each event requirement and confirmed explicit missing
  complete coverage errors for `COMPANY_NEWS`, `ANALYST_RATINGS` and `CONGRESS_TRADES`.
- The60-minute request failed readiness because daily candles cannot supply its
  intraday execution. It was not approximated using a daily open.
- Actual Compare rendered the three funded generated versions with shared cash/SPY
  references and no profile-compatibility warning. The monthly report rendered
  eight annual periods and the flow-adjusted performance timeline. No browser
  runtime errors occurred.

Public-access filters, symbol scope,7-day news/rating windows and30-day Congress
disclosure windows were represented. Category strings (`positive`, `upgrade`,
`purchase`) are proposed source bindings requiring real reviewed tag mappings;
they do not establish source availability. No geopolitical/news sentiment history,
analyst archive, sector archive or Congress collection was manufactured.

## Real-data runs and independent checks

New test strategy: `e824a368-831b-46fd-80ad-792f4ce78c1c`. Version1 is an explicit
clone of the original RSI30 baseline; the original research strategy is untouched.
The generated versions are v2 RSI25, v3 monthly-cash/EMA/volume and v4 weekly-fixed.

Four primary cases and four exact repeats completed over all 2018–2025, carrying
cash/holdings/actions continuously across year boundaries. All use SGD 10,000 initial
capital, SGD 2.50 per executed order, 0.05% slippage, whole shares, long-only/no
leverage, and the existing reviewed AAPL/SPY/FX/action revision. The funded cases
add SGD 500 at each month's first session open: 96 deposits, SGD48,000 in total.
Strategy schedules select the first monthly/weekly session's **close decision**;
fills use the next eligible session open, never that decision's earlier open.

| Generated strategy | Monthly contribution | Final account SGD | Time-weighted return | Max drawdown | Fills |
| --- | ---: | ---: | ---: | ---: | ---: |
| v2 RSI25 | 0 | 15,167.44 | 51.67% | −10.14% | 8 |
| v2 RSI25 | 500 | 70,879.38 | 51.01% | −10.21% | 8 |
| v3 Monthly 20% cash, EMA/volume, half exits | 500 | 61,607.30 | 16.10% | −14.38% | 118 |
| v4 Weekly fixed 500, same conditions/half exits | 500 | 59,335.15 | 6.32% | −2.99% | 166 |

These tests establish execution of the requested rules, not an improvement claim.
The funded cash reference ends at SGD58,000; the matching SPY reference ends at
SGD113,823.31, above every funded generated case. Different rules change exposure
and risk. All attempts remain retained; there was no parameter sweep or selection
of only favorable outcomes. The full2018–2025 period is in-sample research.

Every repeat matched its full result hash. Both generated RSI25 cases also exactly
matched the previously independently reconciled RSI25 result payloads. A separate
stdlib-only Decimal34 checker reconstructed the two new EMA/volume sizing rules:
**4,022 daily marks,4,022 decisions and all 284 fills**, including completed-history
EMA/RSI/volume values, monthly/weekly schedules, split-adjusted histories, partial
sale basis, whole-share sizing, affordability, opening prices, fees/slippage,
historical available FX, dividend entitlement/payment, deposits and daily cash,
equity and realized/unrealized profit. Money tolerance was 1e−18 SGD.

For example, the monthly rule's 2018-02-02 buy used 10 shares at raw USD 166,
slipped USD 166.083, available FX 1.3070 SGD/USD and SGD 2.50 fee. Starting cash
SGD 11,000 after two deposits became `11000 −10×166.083×1.3070 −2.50 =8826.79519`.
Its 2018-03-13 partial sale sold 5 shares at USD 182.498705 after slippage, using
FX 1.315 and the same fee. All fills were checked, not only these examples.

Annual/quarterly/monthly exports contain 8/32/96 carried-forward periods for each
primary case. Existing source limitations remain: current revised raw SIP bars,
declared 20:15 New York bar availability/20:30 decisions, reviewed reference rather
than executable FX with 14-day maximum age, and the existing issuer-action review.
This is not original delivery-vintage certification.

## Preservation, checks and remaining work

All 27 original completed result hashes, original published versions and accounting
dataset hash remain unchanged. Eight additional runs bring this isolated project
to 35 completed results. No engine, application code, credentials, container or
deployment configuration was changed for this follow-up. No pre-existing Docker
container/database was operated on. These tests used the already isolated
`trading-lab-full-cycle-20261106` project on 18082 and its own PostgreSQL on 15440.

The complete required checks were rerun: **231 backend tests including PostgreSQL,
42 frontend tests, Ruff lint/format, Prettier and TypeScript/Vite build passed**.
Existing third-party deprecations and the Vite bundle-size advisory remain.

Private evidence is ignored under `.local/llm-user-workflow-20261107/`: typed
prompts/responses, screenshots, published versions, run/period exports,
independent checker, guard diagnostics and test log. No secrets/runtime archives
are committed. The one-off browser harness initially assumed creation returned 200;
correcting it to accept 201 occurred before any LLM call. This was a harness error.

Remaining work: a product research journal and reviewed results-to-prompt assembly;
broader model authoring evaluation, particularly ambiguity and unnecessary refusals;
and qualification of the actual event/sector/intraday archives before those rules
can execute. Available credentials do not create those archives. Existing free
SEC/BLS/issuer inputs remain narrower than full news, analyst and Congress coverage.
No additional subscription/key was requested or configured in this test.

For structured-output behavior and refusal handling, the implementation was checked
against the [official OpenAI guide](https://developers.openai.com/api/docs/guides/structured-outputs).
See [the earlier full cycle](full-cycle-verification-2026-11-06.md),
[data requirements](historical-input-checklist.md) and
[the research workflow](continuous-research.md).
