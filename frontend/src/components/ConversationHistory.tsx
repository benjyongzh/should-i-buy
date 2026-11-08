import { useEffect, useRef } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { ErrorBox } from './ui'

interface Turn {
  id: string
  sequence: number
  created_at: string
  status: string
  user_text: string
  partial_text: string
  reply_json: { message?: string; questions?: { question: string; choices: string[] }[] } | null
  error: string | null
  proposal_id: string | null
  context_json: unknown
}
interface Page {
  conversation_id: string
  version_id: string | null
  through_sequence: number
  snapshot_hash: string | null
  origin: string
  published_at?: string
  accepted_chat_turn_id?: string | null
  manual_edits_after_proposal?: boolean
  turns: Turn[]
  has_more: boolean
  next_after: number | null
}

export function ConversationHistory({
  strategyId,
  version,
  onClose,
}: {
  strategyId: string
  version?: { id: string; number: number }
  onClose: () => void
}) {
  const dialog = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const node = dialog.current
    if (node && !node.open) {
      if (node.showModal) node.showModal()
      else node.setAttribute('open', '')
    }
  }, [])
  const base = `/llm/strategies/${strategyId}`
  const pages = useInfiniteQuery({
    queryKey: ['conversation-history', strategyId, version?.id],
    initialPageParam: { after: 0, through: undefined as number | undefined },
    queryFn: ({ pageParam }) =>
      api<Page>(
        version
          ? `${base}/versions/${version.id}/conversation?after=${pageParam.after}`
          : `${base}/history?after=${pageParam.after}${pageParam.through === undefined ? '' : `&through=${pageParam.through}`}`,
      ),
    getNextPageParam: (page) =>
      page.has_more && page.next_after !== null
        ? { after: page.next_after, through: page.through_sequence }
        : undefined,
  })
  const first = pages.data?.pages[0]
  return (
    <dialog
      ref={dialog}
      className="conversation-history"
      aria-label={
        version
          ? `Conversation through version ${version.number} · read only`
          : 'Complete strategy conversation · read only'
      }
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
    >
      <header>
        <h2>
          {version
            ? `Conversation through version ${version.number}`
            : 'Complete strategy conversation'}
        </h2>
        <button type="button" className="secondary" onClick={onClose}>
          Close history
        </button>
      </header>
      <p>
        <strong>Read only.</strong> This is a view of the strategy's one conversation. Continue
        changes in the current strategy conversation after closing this view.
      </p>
      {first && (
        <div className="chat-audit">
          <p>
            Conversation: {first.conversation_id} · through message {first.through_sequence}
          </p>
          {first.published_at && <p>Published: {first.published_at}</p>}
          {first.snapshot_hash && (
            <p>
              Immutable transcript hash: <code>{first.snapshot_hash}</code>
            </p>
          )}
          <p>Capture: {first.origin.replaceAll('_', ' ')}</p>
          {version && !first.accepted_chat_turn_id && (
            <p>
              This version has no accepted conversation proposal recorded. Inspect its published
              rules and change summary for authorship.
            </p>
          )}
          {first.manual_edits_after_proposal && (
            <p>The draft was manually edited after proposal acceptance.</p>
          )}
          {version && (
            <p>
              <a href={`/api/strategy-versions/${version.id}`} target="_blank" rel="noreferrer">
                Read published rules
              </a>
            </p>
          )}
          {version && (
            <a
              href={`/api${base}/versions/${version.id}/conversation/export`}
              target="_blank"
              rel="noreferrer"
            >
              Export complete snapshot and hash
            </a>
          )}
        </div>
      )}
      <ErrorBox error={pages.error} />
      {pages.isPending && <p role="status">Loading retained conversation…</p>}
      {first && !first.turns.length && (
        <p>
          No retained messages existed at this boundary. Earlier unrecorded conversations cannot be
          reconstructed.
        </p>
      )}
      {pages.data?.pages
        .flatMap((page) => page.turns)
        .map((turn) => (
          <article key={turn.id} className="chat-turn">
            <small>
              Message {turn.sequence} · {turn.created_at} · {turn.status}
            </small>
            {first?.accepted_chat_turn_id === turn.id && (
              <p>
                <strong>This proposal supplied the published draft.</strong>
              </p>
            )}
            <p>
              <strong>You</strong>
            </p>
            <p className="chat-text">{turn.user_text}</p>
            <p>
              <strong>Strategy assistant</strong>
            </p>
            <p className="chat-text">
              {turn.reply_json?.message ||
                turn.partial_text ||
                'No completed reply at this boundary.'}
            </p>
            {turn.reply_json?.questions?.map((question) => (
              <div key={question.question}>
                <p>{question.question}</p>
                <ul>
                  {question.choices.map((choice) => (
                    <li key={choice}>{choice}</li>
                  ))}
                </ul>
              </div>
            ))}
            {turn.error && <p>{turn.error}</p>}
            <details>
              <summary>Retained reply, proposal and source audit</summary>
              <pre>{JSON.stringify(turn, null, 2)}</pre>
            </details>
          </article>
        ))}
      {pages.hasNextPage && (
        <button
          type="button"
          className="secondary"
          disabled={pages.isFetchingNextPage}
          onClick={() => pages.fetchNextPage()}
        >
          {pages.isFetchingNextPage ? 'Loading…' : 'Load more messages'}
        </button>
      )}
    </dialog>
  )
}
