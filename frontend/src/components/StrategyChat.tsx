import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { streamEvents } from '../lib/stream'
import { ErrorBox } from './ui'
import type { Proposal } from '../pages/StrategyEditor'
import type { Strategy } from '../types'

interface Evidence {
  id: string
  name: string
  kind: string
  content_hash: string
  source_url: string | null
  reviewed: boolean
  synthetic: boolean
  summary: unknown
  availability_policy: string
}
interface Context {
  context_hash: string
  evidence_cutoff: string
  retrieval: string
  evidence: Evidence[]
  model?: string
  prompt_version?: string
  history_turn_ids?: string[]
  recall_mode?: string
  excluded_future_turn_ids?: string[]
  withheld_reply_turn_ids?: string[]
}
interface Reply {
  message: string
  outcome: string
  questions: { question: string; choices: string[] }[]
  estimates: {
    estimate: string
    horizon: string
    method: string
    uncertainty: string
    evidence_ids: string[]
  }[]
  assumptions: string[]
  data_requirements: string[]
  unsupported_requests: string[]
}
interface Turn {
  id: string
  user_text: string
  status: string
  partial_text: string
  reply_json: Reply | null
  context_json: Context
  error: string | null
  proposal_id: string | null
  source_revision: number
}
interface Choice {
  id: string
  name: string
  status?: string
}

function Sources({ context }: { context: Context }) {
  return (
    <details className="chat-audit">
      <summary>Evidence and activity audit · {context.evidence.length} selected sources</summary>
      <p>{context.retrieval}</p>
      <p>Evidence cutoff: {context.evidence_cutoff}</p>
      <p>
        Context hash: <code>{context.context_hash}</code>
      </p>
      {context.model && (
        <p>
          Model: {context.model} · {context.prompt_version} · previous turns supplied:{' '}
          {context.history_turn_ids?.length || 0}. {context.recall_mode || 'Captured recall policy'}
          {!!context.excluded_future_turn_ids?.length &&
            ` · ${context.excluded_future_turn_ids.length} later-cutoff turns withheld`}
          {!!context.withheld_reply_turn_ids?.length &&
            ` · ${context.withheld_reply_turn_ids.length} incomplete/deselected-evidence replies withheld while user intent is retained`}
        </p>
      )}
      {!context.evidence.length && (
        <p>
          No market data or research results supplied. The assistant can clarify intent and rules,
          but has no sourced basis for a market estimate.
        </p>
      )}
      {context.evidence.map((source) => (
        <article key={source.id} className="chat-source">
          <strong>{source.name}</strong>
          <p>
            {source.kind} ·{' '}
            {source.synthetic
              ? 'SYNTHETIC'
              : source.kind === 'research_journal' || source.kind === 'backtest_result'
                ? 'Research output'
                : 'Real source'}{' '}
            · {source.reviewed ? 'Reviewed revision' : 'Not source-qualified / research output'}
          </p>
          <p>{source.availability_policy}</p>
          <code>{source.content_hash}</code>
          {source.source_url && /^https?:\/\//.test(source.source_url) && (
            <p>
              <a href={source.source_url} target="_blank" rel="noreferrer">
                Source location
              </a>
            </p>
          )}
          <details>
            <summary>Exact evidence supplied</summary>
            <pre>{JSON.stringify(source.summary, null, 2)}</pre>
          </details>
        </article>
      ))}
      <details>
        <summary>Full context snapshot</summary>
        <pre>{JSON.stringify(context, null, 2)}</pre>
      </details>
    </details>
  )
}

export function StrategyChat({
  strategy,
  onProposal,
}: {
  strategy: Strategy
  onProposal: (proposal: Proposal) => void
}) {
  const qc = useQueryClient()
  const history = useQuery({
    queryKey: ['strategy-chat', strategy.id],
    queryFn: () => api<Turn[]>(`/llm/strategies/${strategy.id}/turns`),
    refetchInterval: (query) =>
      Array.isArray(query.state.data) &&
      query.state.data.some((turn) => turn.status === 'streaming')
        ? 1000
        : false,
  })
  const profiles = useQuery({
    queryKey: ['chat-profiles'],
    queryFn: () => api<Choice[]>('/backtest-profiles'),
  })
  const datasets = useQuery({
    queryKey: ['chat-datasets'],
    queryFn: () => api<Choice[]>('/market-data/datasets'),
  })
  const inputs = useQuery({
    queryKey: ['chat-inputs'],
    queryFn: () => api<Choice[]>('/strategy-inputs'),
  })
  const runs = useQuery({ queryKey: ['chat-runs'], queryFn: () => api<Choice[]>('/backtests') })
  const studies = useQuery({
    queryKey: ['chat-studies', strategy.id],
    queryFn: () =>
      api<{ id: string; payload: { question: string } }[]>(
        `/research/studies?strategy_id=${strategy.id}`,
      ),
  })
  const [studyIds, setStudyIds] = useState<string[]>([])
  const [message, setMessage] = useState(''),
    [busy, setBusy] = useState(false),
    [partial, setPartial] = useState('')
  const [error, setError] = useState<unknown>(null),
    [context, setContext] = useState<Context | null>(null)
  const [activity, setActivity] = useState<string[]>([]),
    [profile, setProfile] = useState(''),
    [dataset, setDataset] = useState('')
  const [sourceIds, setSourceIds] = useState<string[]>([]),
    [runIds, setRunIds] = useState<string[]>([]),
    [cutoff, setCutoff] = useState('')
  const [draftMessage, setDraftMessage] = useState('')
  const controller = useRef<AbortController | null>(null)
  const thread = useRef<HTMLDivElement | null>(null)
  const followReply = useRef(true)
  useEffect(() => () => controller.current?.abort(), [strategy.id])
  const selection = {
    profile_id: profile || null,
    dataset_id: dataset || null,
    strategy_input_ids: sourceIds,
    run_ids: runIds,
    study_ids: studyIds,
    as_of: cutoff ? new Date(cutoff).toISOString() : null,
  }
  const rows = Array.isArray(history.data) ? history.data : []
  useEffect(() => {
    if (thread.current && followReply.current)
      thread.current.scrollTop = thread.current.scrollHeight
  }, [rows.length, partial])
  async function preview() {
    setError(null)
    try {
      setContext(await api<Context>(`/llm/strategies/${strategy.id}/context`, 'POST', selection))
    } catch (e) {
      setError(e)
    }
  }
  async function send() {
    if (!message.trim() || busy) return
    followReply.current = true
    setError(null)
    setBusy(true)
    setPartial('')
    setActivity(['Preparing selected local evidence'])
    setDraftMessage(message)
    const text = message
    setMessage('')
    controller.current = new AbortController()
    try {
      await streamEvents(
        `/llm/strategies/${strategy.id}/turns`,
        {
          request_id: crypto.randomUUID(),
          expected_revision: strategy.draft_revision,
          message: text,
          selection,
        },
        (event) => {
          if (event.type === 'context') setContext((event.data as { context: Context }).context)
          if (event.type === 'delta')
            setPartial((previous) => previous + (event.data as { text: string }).text)
          if (event.type === 'status')
            setActivity((previous) => [...previous, (event.data as { message: string }).message])
          if (event.type === 'complete') {
            const result = event.data as { turn: Turn; proposal: Proposal | null; stale: boolean }
            qc.setQueryData<Turn[]>(['strategy-chat', strategy.id], (previous) => [
              ...(Array.isArray(previous) ? previous.filter((t) => t.id !== result.turn.id) : []),
              result.turn,
            ])
            setDraftMessage('')
            setPartial('')
            setActivity((previous) => [
              ...previous,
              result.turn.reply_json?.outcome === 'clarify'
                ? 'Waiting for your clarification; no proposal created'
                : 'Validated reply retained',
            ])
            if (result.stale)
              setError(
                new Error(
                  'The saved draft changed during this reply. Review it and ask for a fresh proposal.',
                ),
              )
            else if (result.proposal) onProposal(result.proposal)
          }
        },
        controller.current.signal,
      )
    } catch (e) {
      setMessage(text)
      setError(
        controller.current?.signal.aborted
          ? new Error('Stopped. Partial text is unvalidated and cannot update the draft.')
          : e,
      )
    } finally {
      setBusy(false)
      await qc.invalidateQueries({ queryKey: ['strategy-chat', strategy.id] })
      setDraftMessage('')
      setPartial('')
    }
  }
  return (
    <div className="strategy-chat">
      <p>
        Discuss this strategy, resolve unclear choices, then review proposed rules. Estimates are
        labeled research hypotheses and never become historical signals.
      </p>
      <details>
        <summary>Choose evidence to share with the configured LLM</summary>
        <label>
          Research profile
          <select
            aria-label="Chat research profile"
            value={profile}
            disabled={busy}
            onChange={(e) => {
              setProfile(e.target.value)
              setContext(null)
            }}
          >
            <option value="">No profile selected</option>
            {(Array.isArray(profiles.data) ? profiles.data : []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Accounting dataset
          <select
            aria-label="Chat accounting dataset"
            value={dataset}
            disabled={busy}
            onChange={(e) => {
              setDataset(e.target.value)
              setContext(null)
            }}
          >
            <option value="">No data selected</option>
            {(Array.isArray(datasets.data) ? datasets.data : []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Source revisions (up to 20)
          <select
            multiple
            aria-label="Chat source revisions"
            disabled={busy}
            value={sourceIds}
            onChange={(e) => {
              setSourceIds(Array.from(e.target.selectedOptions, (o) => o.value).slice(0, 20))
              setContext(null)
            }}
          >
            {(Array.isArray(inputs.data) ? inputs.data : []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Completed research runs (up to 5)
          <select
            multiple
            aria-label="Chat research runs"
            disabled={busy}
            value={runIds}
            onChange={(e) => {
              setRunIds(Array.from(e.target.selectedOptions, (o) => o.value).slice(0, 5))
              setContext(null)
            }}
          >
            {(Array.isArray(runs.data) ? runs.data : [])
              .filter((p) => p.status === 'completed')
              .map((p) => (
                <option key={p.id} value={p.id}>
                  {p.id.slice(0, 8)} · completed research
                </option>
              ))}
          </select>
        </label>
        <label>
          Research journal plans (up to 5)
          <select
            multiple
            aria-label="Chat research plans"
            disabled={busy}
            value={studyIds}
            onChange={(e) => {
              setStudyIds(Array.from(e.target.selectedOptions, (o) => o.value).slice(0, 5))
              setContext(null)
            }}
          >
            {(Array.isArray(studies.data) ? studies.data : []).map((p) => (
              <option key={p.id} value={p.id}>
                {p.payload.question}
              </option>
            ))}
          </select>
        </label>
        <ErrorBox error={studies.error} />
        <label>
          Evidence cutoff (your local time; blank = now)
          <input
            type="datetime-local"
            aria-label="Chat evidence cutoff"
            value={cutoff}
            disabled={busy}
            onChange={(e) => {
              setCutoff(e.target.value)
              setContext(null)
            }}
          />
        </label>
        <button type="button" className="secondary" disabled={busy} onClick={preview}>
          Preview evidence
        </button>
      </details>
      {context && <Sources context={context} />}
      <div
        ref={thread}
        role="log"
        onScroll={(event) => {
          const node = event.currentTarget
          followReply.current = node.scrollHeight - node.scrollTop - node.clientHeight < 80
        }}
        aria-label="Strategy conversation"
        aria-live="polite"
        aria-relevant="additions"
      >
        {rows.map((turn) => (
          <article key={turn.id} className="chat-turn">
            <p>
              <strong>You</strong>
            </p>
            <p className="chat-text">{turn.user_text}</p>
            <p>
              <strong>Strategy assistant · {turn.reply_json?.outcome || turn.status}</strong>
            </p>
            <p className="chat-text">
              {turn.reply_json?.message || turn.partial_text || 'No completed reply'}
            </p>
            {turn.error && <p role="alert">{turn.error}</p>}
            {turn.reply_json?.questions.map((q) => (
              <div key={q.question} className="chat-question">
                <strong>{q.question}</strong>
                <div>
                  {q.choices.map((choice) => (
                    <button
                      key={choice}
                      type="button"
                      className="secondary"
                      disabled={busy}
                      onClick={() =>
                        setMessage(
                          (previous) =>
                            `${previous}${previous ? '\n' : ''}${q.question}: ${choice}`,
                        )
                      }
                    >
                      {choice}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {turn.reply_json?.estimates.map((estimate, i) => (
              <aside key={i} className="chat-estimate">
                <strong>Estimate · research only</strong>
                <p>{estimate.estimate}</p>
                <p>Horizon: {estimate.horizon}</p>
                <p>Basis: {estimate.method}</p>
                <p>Uncertainty: {estimate.uncertainty}</p>
                <p>
                  Evidence:{' '}
                  {estimate.evidence_ids
                    .map(
                      (id) =>
                        turn.context_json.evidence.find((source) => source.id === id)?.name || id,
                    )
                    .join(', ')}
                </p>
              </aside>
            ))}
            {(['assumptions', 'data_requirements', 'unsupported_requests'] as const).map((key) =>
              turn.reply_json?.[key]?.length ? (
                <div key={key}>
                  <strong>{key.replaceAll('_', ' ')}</strong>
                  <ul>
                    {turn.reply_json[key].map((item, i) => (
                      <li key={i}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null,
            )}
            <Sources context={turn.context_json} />
            {turn.proposal_id && (
              <div>
                <small>
                  Retained proposal {turn.proposal_id} · saved draft revision {turn.source_revision}
                  . Acceptance and publication are separate actions.
                </small>
                <button
                  type="button"
                  className="secondary"
                  disabled={busy || turn.source_revision !== strategy.draft_revision}
                  onClick={async () => {
                    try {
                      const proposal = await api<Proposal & { accepted: boolean }>(
                        `/llm/proposals/${turn.proposal_id}`,
                      )
                      if (proposal.accepted)
                        throw new Error('This proposal has already been accepted.')
                      onProposal(proposal)
                    } catch (e) {
                      setError(e)
                    }
                  }}
                >
                  Review saved proposal
                </button>
                <a href="#strategy-proposal-review">Go to proposal review</a>
              </div>
            )}
          </article>
        ))}
        {draftMessage && (
          <article className="chat-turn">
            <strong>You</strong>
            <p className="chat-text">{draftMessage}</p>
            <strong>Strategy assistant · {busy ? 'streaming, unvalidated' : 'incomplete'}</strong>
            <p className="chat-text" aria-label="Streaming assistant reply">
              {partial || 'Preparing reply…'}
            </p>
          </article>
        )}
      </div>
      {!!activity.length && (
        <ol aria-label="Assistant activity" className="chat-activity">
          {activity.map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ol>
      )}
      <ErrorBox error={error || history.error} />
      <textarea
        aria-label="Strategy conversation message"
        maxLength={5000}
        value={message}
        disabled={busy}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="For example: I want smaller positions, but help me choose what small means."
        rows={4}
      />
      <button type="button" className="button" disabled={busy || !message.trim()} onClick={send}>
        {busy ? 'Streaming reply…' : 'Send message'}
      </button>
      {busy && (
        <button type="button" className="secondary" onClick={() => controller.current?.abort()}>
          Stop reply
        </button>
      )}
    </div>
  )
}
