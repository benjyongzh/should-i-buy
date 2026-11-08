import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { Badge, ErrorBox, Field, PageTitle, Panel, short } from '../components/ui'

const capabilities = {
  daily_accounting: 'Daily prices, FX and corporate actions',
  sec_filings: 'SEC 8-K filing presence and item tags',
  intraday: 'Intraday data',
  historical_sectors: 'Historical sectors',
  company_news: 'Company news',
  analyst_ratings: 'Analyst ratings',
  congress_trades: 'Congress disclosures',
}
type Capability = keyof typeof capabilities
type Request = {
  symbol: string
  benchmark: string
  start: string
  end: string
  warmup_days: number
  capabilities: Capability[]
}
type Intake = {
  id: string
  status: string
  error: string | null
  cancel_requested: boolean
  request_payload: Request
}
type Artifact = {
  id: string
  kind: string
  source_url: string
  content_hash: string
  metadata: { symbol?: string; title?: string; bytes: number }
}
type Action = {
  symbol: string
  session_date: string
  kind: 'dividend' | 'split'
  value: string
  payment_date: string | null
  available_at: string
}
type Proof = { action: Action; artifact_id: string; quote: string }
type Report = {
  content_hash: string
  payload: {
    identity: { name: string; cik: string; exchange: string; limitation: string } | null
    capabilities: Partial<Record<Capability, { state: string; reason: string }>>
    findings: { capability: string; message: string }[]
    policies: string[]
    action_proposals: (Proof & { state: string })[]
  }
}
type Package = {
  id: string
  content_hash: string
  payload: {
    ready_capabilities: string[]
    dataset: { id: string } | null
    strategy_inputs: { id: string }[]
  }
}
type Detail = Intake & { report: Report | null; artifacts: Artifact[]; packages: Package[] }

export function Companies() {
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState('')
  const [symbol, setSymbol] = useState('AAPL')
  const [benchmark, setBenchmark] = useState('SPY')
  const [start, setStart] = useState('2018-01-01')
  const [end, setEnd] = useState('2025-12-31')
  const [warmup, setWarmup] = useState(730)
  const [maxDocs, setMaxDocs] = useState(100)
  const [requested, setRequested] = useState<Capability[]>(['daily_accounting', 'sec_filings'])
  const [refresh, setRefresh] = useState(false)
  const configuration = useQuery({
    queryKey: ['company-configuration'],
    queryFn: () =>
      api<{ configured: { sec_contact: boolean; alpaca: boolean }; note: string }>(
        '/company-intakes/configuration',
      ),
  })
  const jobs = useQuery({
    queryKey: ['company-intakes'],
    queryFn: () => api<Intake[]>('/company-intakes'),
    refetchInterval: 3000,
  })
  const detail = useQuery({
    queryKey: ['company-intake', selected],
    queryFn: () => api<Detail>(`/company-intakes/${selected}`),
    enabled: !!selected,
    refetchInterval: (q) =>
      ['queued', 'running'].includes(q.state.data?.status || '') ? 2000 : false,
  })
  const create = useMutation({
    mutationFn: () =>
      api<Intake>('/company-intakes', 'POST', {
        symbol: symbol.trim().toUpperCase(),
        benchmark: benchmark.trim().toUpperCase(),
        start,
        end,
        warmup_days: warmup,
        max_sec_documents: maxDocs,
        capabilities: requested,
        refresh,
        idempotency_key: crypto.randomUUID(),
      }),
    onSuccess: (job) => {
      setSelected(job.id)
      void queryClient.invalidateQueries({ queryKey: ['company-intakes'] })
    },
  })
  const operation = useMutation({
    mutationFn: (action: 'cancel' | 'retry') =>
      api<Intake>(`/company-intakes/${selected}/${action}`, 'POST'),
    onSuccess: (job) => {
      setSelected(job.id)
      void queryClient.invalidateQueries({ queryKey: ['company-intakes'] })
      void queryClient.invalidateQueries({ queryKey: ['company-intake', selected] })
    },
  })
  return (
    <div className="company-onboarding">
      <PageTitle
        eyebrow="DATA EVIDENCE"
        title="Company onboarding"
        description="Request a US-listed ticker, inspect retained evidence, then explicitly approve an immutable data package. Strategy readiness remains a separate check."
      />
      <ErrorBox
        error={configuration.error || jobs.error || detail.error || create.error || operation.error}
      />
      <Panel title="Request company data">
        <p>
          SEC contact: {configuration.data?.configured.sec_contact ? 'configured' : 'missing'} ·
          Alpaca: {configuration.data?.configured.alpaca ? 'configured' : 'missing'}
        </p>
        <p className="muted">{configuration.data?.note}</p>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            create.mutate()
          }}
        >
          <div className="form-grid">
            <Field label="Ticker">
              <input
                required
                maxLength={12}
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
              />
            </Field>
            <Field label="Benchmark">
              <input
                required
                maxLength={12}
                value={benchmark}
                onChange={(e) => setBenchmark(e.target.value)}
              />
            </Field>
            <Field label="Start date">
              <input
                required
                type="date"
                value={start}
                onChange={(e) => setStart(e.target.value)}
              />
            </Field>
            <Field label="End date">
              <input required type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
            </Field>
            <Field label="Warm-up calendar days">
              <input
                type="number"
                min={0}
                max={1096}
                value={warmup}
                onChange={(e) => setWarmup(Number(e.target.value))}
              />
            </Field>
            <Field
              label="SEC document limit"
              hint="Exceeding this limit blocks collection; documents are never silently truncated."
            >
              <input
                type="number"
                min={1}
                max={200}
                value={maxDocs}
                onChange={(e) => setMaxDocs(Number(e.target.value))}
              />
            </Field>
          </div>
          <fieldset>
            <legend>Requested capabilities</legend>
            {Object.entries(capabilities).map(([cap, label]) => (
              <label className="checkbox" key={cap}>
                <input
                  type="checkbox"
                  checked={requested.includes(cap as Capability)}
                  onChange={(e) =>
                    setRequested(
                      e.target.checked
                        ? [...requested, cap as Capability]
                        : requested.filter((c) => c !== cap),
                    )
                  }
                />
                {label}
                {!['daily_accounting', 'sec_filings'].includes(cap) &&
                  ' — collector pending; request will report a blocker'}
              </label>
            ))}
          </fieldset>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={refresh}
              onChange={(e) => setRefresh(e.target.checked)}
            />
            Fetch fresh evidence instead of reusing reviewed coverage
          </label>
          <p className="muted">
            Daily requests use SGD accounting, a 14-day reference-FX age limit and raw SIP bars.
            Missing FX or issuer evidence blocks approval. Current ticker mapping requires
            historical continuity review.
          </p>
          <button className="button primary" disabled={create.isPending || !requested.length}>
            {create.isPending ? 'Queuing…' : 'Collect evidence'}
          </button>
        </form>
      </Panel>
      <Panel title="Collection attempts">
        {!jobs.data?.length && <p>No requests yet.</p>}
        {jobs.data?.map((job) => (
          <button
            className="button"
            key={job.id}
            aria-pressed={job.id === selected}
            onClick={() => setSelected(job.id)}
          >
            {job.request_payload.symbol} · {job.request_payload.start}–{job.request_payload.end} ·{' '}
            {job.status} · {short(job.id)}
          </button>
        ))}
      </Panel>
      {detail.data && (
        <Panel title={`${detail.data.request_payload.symbol} evidence review`}>
          <Badge value={detail.data.status} />
          <p>{detail.data.error}</p>
          {['queued', 'running'].includes(detail.data.status) ? (
            <>
              <p>
                Background worker is collecting evidence. A collection report does not make data
                eligible.
              </p>
              <button
                className="button"
                disabled={operation.isPending || detail.data.cancel_requested}
                onClick={() => operation.mutate('cancel')}
              >
                Cancel collection
              </button>
            </>
          ) : (
            <button
              className="button"
              disabled={operation.isPending}
              onClick={() => operation.mutate('retry')}
            >
              Retry as a new collection
            </button>
          )}
          {detail.data.report && (
            <Review key={detail.data.id + detail.data.report.content_hash} detail={detail.data} />
          )}
        </Panel>
      )}
    </div>
  )
}

function Review({ detail }: { detail: Detail }) {
  const queryClient = useQueryClient()
  const report = detail.report!
  const payload = report.payload
  const [approved, setApproved] = useState<Capability[]>([])
  const [proofs, setProofs] = useState<Proof[]>(
    payload.action_proposals.map(({ action, artifact_id, quote }) => ({
      action,
      artifact_id,
      quote,
    })),
  )
  const [note, setNote] = useState('')
  const [policies, setPolicies] = useState(false)
  const [identity, setIdentity] = useState(false)
  const [complete, setComplete] = useState(false)
  const [upload, setUpload] = useState({
    symbol: detail.request_payload.symbol,
    source_url: '',
    title: '',
    text: '',
    available_at: '',
    clock_policy: '',
  })
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['company-intake', detail.id] })
  const retain = useMutation({
    mutationFn: () => api(`/company-intakes/${detail.id}/evidence`, 'POST', upload),
    onSuccess: () => {
      void refresh()
    },
  })
  const submit = useMutation({
    mutationFn: () =>
      api(`/company-intakes/${detail.id}/approve`, 'POST', {
        expected_report_hash: report.content_hash,
        approve_capabilities: approved,
        acknowledge_policies: policies,
        attest_historical_identity: identity,
        attest_action_coverage: complete,
        note,
        actions: approved.includes('daily_accounting') ? proofs : [],
      }),
    onSuccess: () => {
      void refresh()
      void queryClient.invalidateQueries({ queryKey: ['datasets'] })
      void queryClient.invalidateQueries({ queryKey: ['strategy-inputs'] })
    },
  })
  const rawAccounting = payload.capabilities.daily_accounting?.state === 'needs_review'
  const update = (index: number, value: Partial<Proof>) =>
    setProofs(proofs.map((p, i) => (i === index ? { ...p, ...value } : p)))
  return (
    <div className="company-review">
      <ErrorBox error={retain.error || submit.error} />
      <p className="muted">
        This report retains collection-time findings. Reviewed packages below record the
        capabilities approved afterwards.
      </p>
      <p>
        {payload.identity
          ? `${payload.identity.name} · CIK ${payload.identity.cik} · ${payload.identity.exchange}`
          : 'Company identity unresolved.'}
      </p>
      <p className="muted">
        Report hash: <code>{report.content_hash}</code>
      </p>
      {Object.entries(payload.capabilities).map(([cap, state]) => (
        <div key={cap} className="source-capability">
          <h3>
            {capabilities[cap as Capability]} <Badge value={state.state} />
          </h3>
          <p>{state.reason}</p>
        </div>
      ))}
      {payload.findings.map((f, i) => (
        <p key={i}>
          {f.capability}: {f.message}
        </p>
      ))}
      <h3>Information-clock policies</h3>
      <ul>
        {payload.policies.map((p) => (
          <li key={p}>{p}</li>
        ))}
      </ul>
      <details>
        <summary>Retained source evidence ({detail.artifacts.length})</summary>
        {detail.artifacts.map((a) => (
          <p key={a.id}>
            <strong>
              {a.metadata.symbol} {a.kind}
            </strong>{' '}
            ·{' '}
            <a href={`/api/company-intakes/${detail.id}/artifacts/${a.id}`}>
              Download retained bytes
            </a>{' '}
            ·{' '}
            <a href={a.source_url} target="_blank" rel="noreferrer">
              Source
            </a>
            <br />
            <code>{a.content_hash}</code>
          </p>
        ))}
      </details>
      {rawAccounting && (
        <>
          <h3>Corporate action review</h3>
          <p>
            Proposals need review against original issuer records. Check nominal share basis,
            ex-date, payment date and evidence availability. Every broker candidate must be
            reconciled. Completeness also requires checking for actions the broker omitted.
          </p>
          {proofs.map((proof, index) => (
            <details key={index} open={!proof.artifact_id}>
              <summary>
                {proof.action.symbol} {proof.action.kind} · {proof.action.session_date} ·{' '}
                {proof.action.value} ·{' '}
                {proof.artifact_id ? 'proposed evidence' : 'evidence missing'}
              </summary>
              <div className="form-grid">
                {(['symbol', 'session_date', 'value', 'payment_date', 'available_at'] as const).map(
                  (field) => (
                    <Field label={`${field} ${index + 1}`} key={field}>
                      <input
                        value={proof.action[field] || ''}
                        onChange={(e) =>
                          update(index, {
                            action: {
                              ...proof.action,
                              [field]: e.target.value || (field === 'payment_date' ? null : ''),
                            },
                          })
                        }
                      />
                    </Field>
                  ),
                )}
                <Field label={`Kind ${index + 1}`}>
                  <select
                    value={proof.action.kind}
                    onChange={(e) =>
                      update(index, {
                        action: { ...proof.action, kind: e.target.value as Action['kind'] },
                      })
                    }
                  >
                    <option value="dividend">Dividend</option>
                    <option value="split">Split</option>
                  </select>
                </Field>
                <Field label={`Evidence ${index + 1}`}>
                  <select
                    value={proof.artifact_id}
                    onChange={(e) => update(index, { artifact_id: e.target.value })}
                  >
                    <option value="">Select original issuer evidence</option>
                    {detail.artifacts
                      .filter(
                        (a) =>
                          ['sec_submission', 'issuer_evidence'].includes(a.kind) &&
                          a.metadata.symbol === proof.action.symbol,
                      )
                      .map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.metadata.title || a.kind} · {short(a.id)}
                        </option>
                      ))}
                  </select>
                </Field>
              </div>
              <Field label={`Exact evidence quote ${index + 1}`}>
                <textarea
                  rows={5}
                  value={proof.quote}
                  onChange={(e) => update(index, { quote: e.target.value })}
                />
              </Field>
              {index >= payload.action_proposals.length && (
                <button
                  className="button"
                  onClick={() => setProofs(proofs.filter((_, i) => i !== index))}
                >
                  Remove added action
                </button>
              )}
            </details>
          ))}
          <button
            className="button"
            onClick={() =>
              setProofs([
                ...proofs,
                {
                  action: {
                    symbol: detail.request_payload.symbol,
                    session_date: '',
                    kind: 'dividend',
                    value: '',
                    payment_date: '',
                    available_at: '',
                  },
                  artifact_id: '',
                  quote: '',
                },
              ])
            }
          >
            Add an issuer action missing from broker candidates
          </button>
          <details>
            <summary>Supply original issuer transcript</summary>
            <p>
              URLs label provenance. The server stores the supplied text without fetching that URL.
              Verify the transcript and its historical availability yourself.
            </p>
            {(Object.keys(upload) as (keyof typeof upload)[]).map((field) => (
              <Field label={`Issuer ${field}`} key={field}>
                {['text', 'clock_policy'].includes(field) ? (
                  <textarea
                    value={upload[field]}
                    onChange={(e) => setUpload({ ...upload, [field]: e.target.value })}
                  />
                ) : (
                  <input
                    value={upload[field]}
                    onChange={(e) => setUpload({ ...upload, [field]: e.target.value })}
                  />
                )}
              </Field>
            ))}
            <button className="button" disabled={retain.isPending} onClick={() => retain.mutate()}>
              Retain evidence transcript
            </button>
          </details>
        </>
      )}
      <h3>Explicit approval</h3>
      {Object.entries(payload.capabilities).map(([cap, state]) => (
        <label className="checkbox" key={cap}>
          <input
            type="checkbox"
            disabled={!['reviewed', 'needs_review'].includes(state.state)}
            checked={approved.includes(cap as Capability)}
            onChange={(e) =>
              setApproved(
                e.target.checked
                  ? [...approved, cap as Capability]
                  : approved.filter((c) => c !== cap),
              )
            }
          />
          Approve {capabilities[cap as Capability]}
        </label>
      ))}
      <label className="checkbox">
        <input type="checkbox" checked={policies} onChange={(e) => setPolicies(e.target.checked)} />
        I reviewed and accept every information-clock and source limitation above.
      </label>
      <label className="checkbox">
        <input type="checkbox" checked={identity} onChange={(e) => setIdentity(e.target.checked)} />
        I checked historical ticker, issuer and share-class continuity for this interval.
      </label>
      {rawAccounting && (
        <label className="checkbox">
          <input
            type="checkbox"
            checked={complete}
            onChange={(e) => setComplete(e.target.checked)}
          />
          I checked complete split/dividend coverage, including no-event intervals and nominal share
          basis.
        </label>
      )}
      <Field
        label="Review note"
        hint="At least 30 characters; explain source checks and any reconciliations."
      >
        <textarea
          aria-label="Review note"
          minLength={30}
          maxLength={2000}
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
      </Field>
      <button
        className="button primary"
        disabled={
          submit.isPending ||
          !approved.length ||
          !policies ||
          !identity ||
          note.trim().length < 30 ||
          (approved.includes('daily_accounting') && rawAccounting && !complete)
        }
        onClick={() => submit.mutate()}
      >
        Create immutable reviewed package
      </button>
      {detail.packages.map((p) => (
        <div key={p.id} role="status">
          <h3>Reviewed package {short(p.id)}</h3>
          <p>
            Approved: {p.payload.ready_capabilities.join(', ')}. Other requested capabilities retain
            their blockers.
          </p>
          <p>
            Dataset: {p.payload.dataset?.id || 'none'} · Strategy inputs:{' '}
            {p.payload.strategy_inputs.map((s) => s.id).join(', ') || 'none'}
          </p>
          <p>
            <code>{p.content_hash}</code>
          </p>
          <Link to="/backtests/new">Select these immutable revisions for a backtest</Link>
          <p>
            Run-specific readiness still checks the strategy, profile, selected revisions and
            indicator warm-up.
          </p>
        </div>
      ))}
    </div>
  )
}
