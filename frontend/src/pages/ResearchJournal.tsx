import { useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, useLab } from '../lib/api'
import { ConversationHistory } from '../components/ConversationHistory'
import { ErrorBox, Field, PageTitle, Panel } from '../components/ui'

interface Attempt {
  id: string
  status: string
  error: string | null
  result_hash: string | null
  metrics: Record<string, unknown> | null
  metric_deltas: Record<string, string>
}
interface JournalEvent {
  id: string
  created_at: string
  kind: string
  content_hash: string
  payload: Record<string, unknown>
}
interface Study {
  id: string
  strategy_id: string
  parent_id: string | null
  content_hash: string
  created_at: string
  payload: {
    question: string
    hypothesis: string
    planned_change: string
    evaluation_criteria: string
    mode: 'prospective' | 'retrospective'
    baseline: Attempt & { strategy_version_id: string }
    baseline_config: unknown
    controls: Record<string, string>
    profile_snapshot: unknown
    provenance: { synthetic?: boolean }
    conversation_through_sequence: number
    warning: string
  }
  state?: string
  events?: JournalEvent[]
  attempts?: Attempt[]
}

export function ResearchJournal() {
  const lab = useLab()
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const selected = params.get('study') || ''
  const list = useQuery({
    queryKey: ['research-studies'],
    queryFn: () => api<Study[]>('/research/studies'),
  })
  const query = useQuery({
    queryKey: ['research-study', selected],
    queryFn: () => api<Study>(`/research/studies/${selected}`),
    enabled: !!selected,
    refetchInterval: 2500,
  })
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  const retryRequests = useRef(new Map<string, string>())
  const [baseline, setBaseline] = useState('')
  const [question, setQuestion] = useState('')
  const [hypothesis, setHypothesis] = useState('')
  const [change, setChange] = useState('')
  const [criteria, setCriteria] = useState('')
  const [mode, setMode] = useState('prospective')
  const [candidate, setCandidate] = useState('')
  const [attachId, setAttachId] = useState('')
  const [note, setNote] = useState('')
  const [assessment, setAssessment] = useState('inconclusive')
  const [summary, setSummary] = useState('')
  const [next, setNext] = useState('')
  const [synthetic, setSynthetic] = useState(false)
  const [history, setHistory] = useState<{ id: string; number: number } | null>(null)
  const study = query.data
  const bound = study?.events?.find((e) => e.kind === 'candidate')
  const concluded = study?.state === 'concluded'
  const completed = lab.runs.filter((r) => r.status === 'completed')
  const attempts = study?.attempts || []
  const compareIds = study
    ? [
        study.payload.baseline.id,
        ...attempts.filter((r) => r.status === 'completed').map((r) => r.id),
      ].slice(0, 6)
    : []

  async function mutate(path: string, body: unknown, created = false) {
    setBusy(true)
    setError(null)
    const fields = body as Record<string, unknown>
    const { request_id: requestId, ...content } = fields
    const retryKey = path + JSON.stringify(content)
    let requestBody = body
    if (requestId) {
      if (!retryRequests.current.has(retryKey))
        retryRequests.current.set(retryKey, String(requestId))
      requestBody = { ...fields, request_id: retryRequests.current.get(retryKey) }
    }
    try {
      const result = await api<Study>(path, 'POST', requestBody)
      retryRequests.current.delete(retryKey)
      if (path.endsWith('/notes')) setNote('')
      qc.setQueryData(['research-study', result.id], result)
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['research-studies'] }),
        qc.invalidateQueries({ queryKey: ['runs'] }),
        qc.invalidateQueries({ queryKey: ['chat-studies'] }),
      ])
      if (created) setParams({ study: result.id })
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="research-journal">
      <PageTitle
        eyebrow="RESEARCH JOURNAL"
        title="Test an idea. Keep the evidence."
        description="Register a hypothesis, compare published versions under frozen conditions, and retain every recorded attempt and conclusion."
      />
      <ErrorBox error={error || list.error || query.error || lab.error} />
      <Panel title="Research plans">
        <Field label="Open a plan">
          <select
            aria-label="Open research plan"
            value={selected}
            onChange={(e) => {
              setParams(e.target.value ? { study: e.target.value } : {})
              setCandidate('')
              setAttachId('')
              setNote('')
              setSummary('')
              setNext('')
              setSynthetic(false)
              setError(null)
            }}
          >
            <option value="">Register a new plan</option>
            {(list.data || []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.payload.mode} · {s.payload.question}
              </option>
            ))}
          </select>
        </Field>
      </Panel>
      {!selected && (
        <Panel title="Register a research plan">
          <p>
            Prospective plans must precede candidate publication. Use retrospective mode when
            reviewing versions or runs that already exist. Repeated 2018–2025 evaluation is
            in-sample research.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              void mutate(
                '/research/studies',
                {
                  request_id: crypto.randomUUID(),
                  baseline_run_id: baseline,
                  question,
                  hypothesis,
                  planned_change: change,
                  evaluation_criteria: criteria,
                  mode,
                  parent_id: params.get('parent') || null,
                },
                true,
              )
            }}
          >
            {params.get('parent') && (
              <p>
                Follow-on to plan <code>{params.get('parent')}</code>
              </p>
            )}
            <Field label="Completed baseline run">
              <select
                required
                aria-label="Completed baseline run"
                value={baseline}
                onChange={(e) => setBaseline(e.target.value)}
              >
                <option value="">Choose a completed run</option>
                {completed.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.id.slice(0, 8)} ·{' '}
                    {lab.strategies.find(
                      (s) =>
                        s.id ===
                        lab.versions.find((v) => v.id === r.strategy_version_id)?.strategy_id,
                    )?.name || r.strategy_version_id}{' '}
                    · {r.profile_snapshot.start_date} to {r.profile_snapshot.end_date}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Registration mode">
              <select value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="prospective">
                  Prospective · candidate published after this plan
                </option>
                <option value="retrospective">
                  Retrospective · existing versions and outcomes
                </option>
              </select>
            </Field>
            <Field label="Research question">
              <input
                required
                minLength={10}
                maxLength={2000}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
              />
            </Field>
            <Field label="Hypothesis">
              <textarea
                required
                minLength={10}
                maxLength={4000}
                value={hypothesis}
                onChange={(e) => setHypothesis(e.target.value)}
              />
            </Field>
            <Field label="Planned rule change">
              <textarea
                required
                minLength={10}
                maxLength={4000}
                value={change}
                onChange={(e) => setChange(e.target.value)}
              />
            </Field>
            <Field label="Evaluation criteria">
              <textarea
                required
                minLength={10}
                maxLength={4000}
                value={criteria}
                onChange={(e) => setCriteria(e.target.value)}
              />
            </Field>
            <button disabled={busy}>Register immutable plan</button>
          </form>
        </Panel>
      )}
      {study && (
        <>
          <Panel title={study.payload.question}>
            <p>
              <strong>
                {study.payload.mode.toUpperCase()} · {study.state}
              </strong>{' '}
              · {study.created_at}
              {study.payload.provenance.synthetic && ' · SYNTHETIC'}
            </p>
            <p>
              <strong>Hypothesis:</strong> {study.payload.hypothesis}
            </p>
            <p>
              <strong>Planned change:</strong> {study.payload.planned_change}
            </p>
            <p>
              <strong>Evaluate:</strong> {study.payload.evaluation_criteria}
            </p>
            <p>{study.payload.warning}</p>
            <p>
              <Link to={`/strategies/${study.strategy_id}`}>
                Continue the strategy conversation
              </Link>{' '}
              · Select this research plan in the chat evidence picker to discuss its recorded
              outcomes.
            </p>
            <p>
              Conversation checkpoint at registration: through message{' '}
              {study.payload.conversation_through_sequence}. Published versions retain their own
              read-only transcript.
            </p>
            <p>
              <Link to={`/backtests/${study.payload.baseline.id}`}>Baseline run</Link> ·{' '}
              <Link to={`?parent=${study.id}`}>Register a follow-on plan</Link>
              {study.parent_id && (
                <>
                  {' '}
                  · <Link to={`?study=${study.parent_id}`}>Parent plan</Link>
                </>
              )}
            </p>
            <details>
              <summary>Frozen conditions and source hashes</summary>
              <code>{study.content_hash}</code>
              <pre>
                {JSON.stringify(
                  {
                    controls: study.payload.controls,
                    profile: study.payload.profile_snapshot,
                    baseline_rules: study.payload.baseline_config,
                  },
                  null,
                  2,
                )}
              </pre>
            </details>
          </Panel>
          <Panel title="Published candidate">
            {bound ? (
              <>
                <p>
                  Version {String(bound.payload.number)} ·{' '}
                  <code>{String(bound.payload.config_hash)}</code>
                </p>
                <details>
                  <summary>Compare baseline and candidate rules</summary>
                  <pre>
                    {JSON.stringify(
                      { baseline: study.payload.baseline_config, candidate: bound.payload.config },
                      null,
                      2,
                    )}
                  </pre>
                </details>
                <button
                  className="secondary"
                  onClick={() =>
                    setHistory({
                      id: String(bound.payload.strategy_version_id),
                      number: Number(bound.payload.number),
                    })
                  }
                >
                  Read candidate conversation snapshot
                </button>
              </>
            ) : (
              <>
                <p>
                  Review and publish the change in the strategy editor first. Binding retains that
                  exact immutable version.
                </p>
                <Field label="Candidate version">
                  <select value={candidate} onChange={(e) => setCandidate(e.target.value)}>
                    <option value="">Choose a published candidate</option>
                    {lab.versions
                      .filter(
                        (v) =>
                          v.strategy_id === study.strategy_id &&
                          v.id !== study.payload.baseline.strategy_version_id &&
                          (study.payload.mode === 'retrospective' ||
                            Date.parse(v.created_at) >= Date.parse(study.created_at)),
                      )
                      .map((v) => (
                        <option key={v.id} value={v.id}>
                          v{v.number} · {v.change_summary}
                        </option>
                      ))}
                  </select>
                </Field>
                <button
                  disabled={busy || !candidate || concluded}
                  onClick={() =>
                    void mutate(`/research/studies/${study.id}/candidate`, {
                      strategy_version_id: candidate,
                    })
                  }
                >
                  Bind reviewed candidate
                </button>
              </>
            )}
            {!!bound && !concluded && (
              <>
                {study.payload.provenance.synthetic && (
                  <label>
                    <input
                      type="checkbox"
                      checked={synthetic}
                      onChange={(e) => setSynthetic(e.target.checked)}
                    />{' '}
                    I explicitly acknowledge synthetic demonstration data
                  </label>
                )}
                <p>
                  <button
                    disabled={busy || (!!study.payload.provenance.synthetic && !synthetic)}
                    onClick={() =>
                      void mutate(`/research/studies/${study.id}/schedule`, {
                        request_id: crypto.randomUUID(),
                        acknowledge_synthetic: synthetic,
                      })
                    }
                  >
                    Schedule candidate attempt
                  </button>
                </p>
                <Field label="Existing candidate run ID">
                  <input value={attachId} onChange={(e) => setAttachId(e.target.value)} />
                </Field>
                <button
                  className="secondary"
                  disabled={busy || !attachId}
                  onClick={() =>
                    void mutate(`/research/studies/${study.id}/runs`, { run_id: attachId })
                  }
                >
                  Attach matching run
                </button>
              </>
            )}
          </Panel>
          <Panel title="Recorded attempts">
            <p>
              Every attempt scheduled here is retained, including failures and repeats. External
              runs appear after explicit attachment. Deltas are candidate minus baseline, without a
              claim that larger is always better.
            </p>
            <p>
              {compareIds.length > 1 && (
                <Link to={`/compare?runs=${compareIds.join(',')}`}>
                  Compare account timelines, periods and benchmarks (first 6 runs)
                </Link>
              )}
            </p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Status</th>
                    <th>Ending equity Δ (SGD)</th>
                    <th>Max drawdown Δ</th>
                    <th>Executed orders Δ</th>
                  </tr>
                </thead>
                <tbody>
                  {attempts.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <Link to={`/backtests/${r.id}`}>{r.id.slice(0, 8)}</Link>
                      </td>
                      <td>
                        {r.status}
                        {r.error && <p role="alert">{r.error}</p>}
                      </td>
                      <td>{r.metric_deltas.ending_equity ?? '—'}</td>
                      <td>{r.metric_deltas.max_drawdown ?? '—'}</td>
                      <td>{r.metric_deltas.executed_orders ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!attempts.length && <p>No candidate attempts recorded yet.</p>}
            {attempts.map((r) => (
              <details key={r.id}>
                <summary>Attempt {r.id.slice(0, 8)} audit</summary>
                <pre>{JSON.stringify(r, null, 2)}</pre>
              </details>
            ))}
          </Panel>
          {!concluded && (
            <Panel title="Record the conclusion">
              <p>
                Assess all recorded outcomes against the plan. Conclusions are immutable; use notes
                or a follow-on plan for later interpretations.
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  void mutate(`/research/studies/${study.id}/conclusion`, {
                    assessment,
                    summary,
                    next_hypothesis: next,
                  })
                }}
              >
                <Field label="Assessment">
                  <select value={assessment} onChange={(e) => setAssessment(e.target.value)}>
                    {['inconclusive', 'improved', 'worse', 'mixed'].map((value) => (
                      <option key={value}>{value}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Conclusion and trade-offs">
                  <textarea
                    required
                    minLength={10}
                    maxLength={4000}
                    value={summary}
                    onChange={(e) => setSummary(e.target.value)}
                  />
                </Field>
                <Field label="Next hypothesis">
                  <textarea
                    maxLength={4000}
                    value={next}
                    onChange={(e) => setNext(e.target.value)}
                  />
                </Field>
                <button
                  disabled={
                    busy ||
                    !attempts.length ||
                    attempts.some((r) => ['queued', 'running'].includes(r.status))
                  }
                >
                  Record immutable conclusion
                </button>
              </form>
            </Panel>
          )}
          <Panel title="Append-only decision timeline">
            <ol>
              {study.events?.map((e) => (
                <li key={e.id}>
                  <strong>{e.kind}</strong> · {e.created_at}
                  {e.kind === 'candidate' && (
                    <p>Published version {String(e.payload.number)} bound after review.</p>
                  )}
                  {e.kind === 'run' && (
                    <p>
                      <Link to={`/backtests/${String(e.payload.run_id)}`}>
                        Open recorded attempt {String(e.payload.run_id).slice(0, 8)}
                      </Link>
                    </p>
                  )}
                  {e.kind === 'note' && <p>{String(e.payload.text)}</p>}
                  {e.kind === 'conclusion' && (
                    <>
                      <p>
                        <strong>{String(e.payload.assessment)}</strong> ·{' '}
                        {String(e.payload.summary)}
                      </p>
                      {!!e.payload.next_hypothesis && (
                        <p>Next hypothesis: {String(e.payload.next_hypothesis)}</p>
                      )}
                    </>
                  )}
                  <details>
                    <summary>Evidence payload and hash</summary>
                    <pre>{JSON.stringify(e.payload, null, 2)}</pre>
                    <code>{e.content_hash}</code>
                  </details>
                </li>
              ))}
            </ol>
            <form
              onSubmit={(e) => {
                e.preventDefault()
                void mutate(`/research/studies/${study.id}/notes`, {
                  request_id: crypto.randomUUID(),
                  text: note,
                })
              }}
            >
              <Field label="Research note">
                <textarea
                  required
                  maxLength={4000}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              </Field>
              <button disabled={busy || !note.trim()}>Append note</button>
            </form>
          </Panel>
          {history && (
            <ConversationHistory
              strategyId={study.strategy_id}
              version={history}
              onClose={() => setHistory(null)}
            />
          )}
        </>
      )}
    </section>
  )
}
