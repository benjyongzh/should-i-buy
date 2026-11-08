# Strategy conversation verification — 2026-11-07

The editor now has a retained, strategy-scoped streaming conversation, alongside
the existing reviewed proposal/draft/publication mechanism. Migration006 adds
conversation turns and audit snapshots. No financial engine behavior changed.

## Actual live workflow

Tests typed real prompts into **Strategy conversation message** in Chromium,
through Nginx/application/OpenAI on the new isolated18084 project. Configured
model: `gpt-6-luna`. Existing server credentials were used. User authorization for
live testing and selected strategy/result summaries remained in effect.

| Scenario | Observed behavior |
| --- | --- |
| “Safer, smaller positions, more often; exit when conditions look bad” | Asked four specific questions about budget basis, frequency/additions, risk control and exit rules; no configuration/proposal |
| Answer with fixed SGD 500 budget, weekly entries, existing RSI conditions and daily half exits | Generated the requested supported rules after the instruction correction below; user review/acceptance changed only the draft; separate publication created v2 |
| Conditional estimate using selected historical data/run | Gave a qualitative next 12-month scenario, explicit mechanism/method, high uncertainty and selected evidence IDs; no configuration |
| Switch to planning a Paris holiday | Redirected to the current strategy/experiments; no configuration |
| Remove evidence and request an exact next-month AAPL return | Declined to invent a sourced prediction; no estimate/proposal |
| Click **Stop reply** during actual progressive text | Provider stream cancelled; retained interrupted provisional text, no proposal, unchanged draft/version history |

The complete reply is validated before an unaccepted proposal exists. Browser
checks confirmed progressive text before response completion, rather than simply
releasing a completed response in small chunks. The first five completed scenarios
had 35–235 delta events and 14–126 observed UI text updates. Initial substantive text
arrived approximately 2.3–10.3seconds after submission; completion took 2.8–16.1seconds.
These are observed test calls, not latency guarantees. No model cost comparison
or broad authoring-quality certification is claimed.

The estimate explicitly stated that costs can move either way: lower exposure or
traded value may help, while repeated partial exits can increase order count and
fixed fees. It did not claim a defensible numerical magnitude or that the amended
strategy had already been backtested. Estimates remain conversation-only research.

### Findings and corrections retained

- The initial live clarification worked. A following response incorrectly treated
  a fixed SGD 500 spending budget including fees as unsupported. Final validation
  rejected that reply; no proposal was retained. Prompt version
  `strategy-conversation-v2-budget-semantics` now states the engine's actual
  cost-inclusive budget/rounding semantics explicitly. A subsequent real request
  produced the correct fixed sizing, schedule, additions and half exits. This is
  a measured correction, not a guarantee against other semantic mistakes.
- The first estimate correctly observed that metrics plus an opaque version ID
  did not establish the rules a run had tested. The evidence builder was improved
  to include that run's frozen configuration/hash/version number, independently
  of the current draft. A regression also rejects same-date future closing marks.
  A further live estimate turn correctly distinguishes the tested 95%-of-equity
  baseline from the current fixed 500/weekly/half-exit draft. Its streamed reply and
  source snapshot pass the additional checks; total named browser assertions are 42.
- One browser harness attempt used an unreliable Chromium response-body capture;
  a browser stream recorder replaced it. A server/tool restart then interrupted
  another request. Its audit remained `interrupted`, with no proposal. Recovery
  inspected persisted state and did not repeat completed acceptance/publication.
  Temporary browser dependencies were restored under the ignored test directory.
- A cancellation regression exposed cross-realm `DOMException` handling in the
  browser. Cancellation now follows the actual abort signal; the real Stop button
  test verifies the corrected behavior.

Failed/interrupted attempts remain retained rather than being presented as
successful model generations. Old source datasets, strategy versions and result
hashes are audited separately. The compatibility single-request assistant stays
available in a collapsed section; it does not acquire conversation memory or the
new clarification contract.

## Automated and data checks

Final retained conversation counts are **nine provider attempts: six completed,
one failed and two interrupted** (tool/server interruption and the intentional
Stop-button test). Forty-two named live workflow assertions pass, alongside
five final read-only visual checks. The final thread has bounded scrolling,
follows new replies and respects scrolling back to audit earlier messages. The
mobile composer and standalone HTML flowchart render without runtime errors;
the documentation makes no remote requests. Both screenshots were inspected.

The added regression cases exercise clarification→answer→proposal history,
separate publication, duplicate/stale/active requests, orphan recovery, failed
partial retention and secret-safe errors, unknown citations, invalid configuration,
provider refusals/truncation/HTTP errors, Unicode/escape-fragment streaming,
source cutoffs, older-clock history isolation, frozen baseline rules and same-day
future marks. Frontend cases cover incremental UTF-8/SSE, disconnected streams,
errors, clarification choices, partial text, cancellation and estimate cards.

The full frontend suite passes **49 tests**, with TypeScript/Vite build and
Prettier. The final backend suite passes **248 tests including PostgreSQL**;
Ruff lint/format and Alembic no-drift checks pass. Lint used `--no-cache` in the
non-root container because its copied cache directory was not writable. Final
evidence is retained in `backend-tests-final.log` and the deployment audit.
Existing third-party deprecations and the Vite bundle-size advisory remain.

Intraday qualification is a separate source exercise:92 complete monthly
partitions, four blocked months, an independently reconciled January 2019
one-hour-window run/repeat and forced full-period rejection. Congress has no
qualified dataset. See [data evidence and remaining blockers](intraday-congress-verification-2026-11-07.md).

The new project is `trading-lab-strategy-chat-20261107`, with its own database
volume, UI 18084 and loopback PostgreSQL 15442. Pre-existing projects—including 18080
and the 35-result 18082 stack—were not upgraded or restarted by this work. There is
no deployment-success claim for those older frontends.

The final read-only preservation audit matches all 35 prior result hashes, checked
published versions and the accounting dataset hash. The new baseline also exactly
matches its previously independently reconciled result. All 92 intraday child
hashes/parent links and all nine conversation context hashes match. Existing 32
container IDs remain present: five match the captured start/restart/mount state,
while 27 show state differences recorded separately. No operations were performed
on those containers; the cause of those host-state differences is not established.
The audit therefore does not claim that the entire host snapshot is unchanged.

Private evidence is ignored under `.local/strategy-chat-20261107/`: live messages,
provider/audit records, screenshots, stream timing, interrupted/failed attempts,
Stop-button check, source receipts, tests and deployment audit. No key, raw archive
or runtime database is committed. [User/API workflow](strategy-conversation.md)
and [diagram](data-workflow.html#conversation).
