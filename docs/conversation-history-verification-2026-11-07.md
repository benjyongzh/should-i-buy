# Conversation recall and version trace — 2026-11-07

Each strategy now has exactly one permanent conversation identity, keyed by its
strategy ID. There is no create/reset/fork-conversation endpoint. Cloning a
strategy creates a new strategy with its own empty conversation. Existing
strategies are backfilled without changing their configuration/version hashes.

## Recall and durable history

The former latest-eight-turn window is removed. Each request supplies all eligible
prior user messages and completed assistant replies, including proposed rule JSON,
in sequence. Provider usage/request bookkeeping is not repeated in the model input.
Failed/interrupted replies do not become facts or rule changes, but their user
instructions remain available. When an earlier reply cites sources that are no
longer selected, that reply is withheld while its user intent is retained.

Historical evidence cutoffs still withhold later-cutoff turns, with their IDs
shown in the audit. That conservative information boundary is explicit; ordinary
current-time conversation retains the full preceding context. Model access to
text is not a guarantee of flawless reasoning or exact recall on every request.

The existing **140,000-character serialized model-input budget** remains. If the
complete eligible conversation and selected evidence exceed it, admission fails
with an explicit error; no oldest messages are silently removed. The complete
archive remains readable. Reducing selected evidence may free room. Automatic
lossy summarization and unlimited model context are not implemented.

The active panel displays recent messages for rendering efficiency. **Read complete
conversation** opens all retained history using bounded pagination. This display
window no longer limits model recall. Completed, failed and interrupted turns
are immutable at the SQLite/PostgreSQL boundary. Corrections append new messages.

## Publication-time transcripts

Migration **007_conversation_versions** adds the one-to-one identity, monotonic
message sequence, immutable transcript snapshots and final-turn protection.
Every API publication captures, in the same transaction:

- All conversation messages present at publication, including source/reply audits.
- A sequence boundary, publication timestamp, configuration hash and transcript hash.
- The accepted chat proposal's turn ID, plus whether manual edits followed acceptance.

Publishing while a reply streams returns409; the user must finish or stop it.
Strategy-row locks serialize publication and new-turn admission. Later messages
continue in the same conversation and do not alter earlier version transcripts.
The existing explicit proposal-review, draft-acceptance and publication gates stay
in place. Manual authorship remains identifiable when no chat proposal supplied a
published draft.

Every version has **Read conversation through version N**. This modal contains no
message composer, editable choices or acceptance controls. It offers pagination,
source/proposal details, published-rule inspection and a complete JSON/hash export.
It is a historical view of the same conversation, not a separate conversation.
Wrong-strategy access is rejected and transcript mutation endpoints do not exist.

Older versions get sidecar snapshots derived from their saved timestamps. Replies
completed after an older publication are not backdated into it: the snapshot can
show the already-submitted user message with `in_progress_at_publication`, but no
later assistant text. Versions with no retained messages say so. These legacy
captures cannot reconstruct chats that were never recorded. Existing published
version rows remain immutable and unchanged.

## Verification

**255 backend tests including PostgreSQL and 51 frontend tests pass**, with Ruff
lint/format, Prettier, TypeScript/Vite build and Alembic no-drift checks. New cases
cover recall beyond eight turns, exact historical rule JSON, cross-strategy
isolation, one-to-one identity, clone isolation, failed-user intent, deselected
facts, historical cutoffs, explicit input-budget failure, pagination beyond 100
messages, immutable version boundaries, active-stream publication rejection and
legacy backfill without future replies. SQLite/PostgreSQL mutation attacks on
conversation identities, finalized turns and snapshots are rejected.

A live Chromium test used four actual provider calls and ten visibly **SYNTHETIC
padding messages**, in a dedicated test strategy with no invented market data or
financial results. The first real prompt defined “small buy” as a fixed SGD 321.09
spending budget and weekly decisions. After the padding, the model recalled both
and generated the requested sizing/schedule without repeating the number in the
amendment prompt. The actual provider context included 11 then 12 prior turns.
Review/acceptance/publication created v2, freezing all 13 messages and identifying
the accepted proposal. A later real prompt considering SGD 999 appeared in the
ongoing conversation but not the v2 transcript. All 16 named browser checks pass;
the historical dialog has no editing/acceptance controls.

Verification uses a new isolated project
`trading-lab-conversation-history-20261107` on 18086/15444. A read-only backup of the
previous 15442 test database was restored into a new volume, then upgraded from 006
to 007. The source 18084 application and pre-existing containers were not upgraded
or restarted. Migration was tested on real retained history as well as fresh
SQLite/PostgreSQL schemas. No simulation/financial engine code changed.

Final read-only audit: all 37 pre-existing container IDs/start/restart/mount states
match the captured baseline. All 35 earlier 18082 results are unchanged; the three
source 18084 results match both source and restored copy. The original nine turns
are unchanged apart from the new sequence column in the copy. All five transcript
hashes verify, the three strategies each have one conversation identity, and the
old real v2 legacy boundary contains only its three then-existing turns. Five
additional read-only browser checks pass for desktop/mobile historical dialogs,
Escape dismissal and the standalone history diagram; screenshots were inspected.

Private evidence is ignored under `.local/conversation-history-20261107/`:
backup/copy receipt, tests, live recall/snapshot records, screenshots and final
preservation audit. See the [conversation guide](strategy-conversation.md),
[visual workflow](data-workflow.html#conversation-history) and
[Congress follow-up](congress-qualification-2026-11-07.md).

The implementation uses manually managed message history with the existing
configured model/API; the [official OpenAI conversation-state guide](https://developers.openai.com/api/docs/guides/conversation-state)
describes the need to manage context-window limits.
