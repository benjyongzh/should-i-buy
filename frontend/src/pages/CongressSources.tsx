import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../lib/api'
import { ErrorBox, Field, PageTitle, Panel } from '../components/ui'

interface Artifact {
  id: string
  kind: string
  source_url: string
  content_hash: string
  metadata: { year?: number; document_id?: string; memento_datetime?: string; http_status?: number }
}
interface Observation {
  observation_id: string
  canonical_transaction_id: string
  filing_kind: string
  symbol: string
  instrument: string
  action: string
  transaction_date: string
  notification_date: string | null
  amount_min: string | null
  amount_max: string | null
  amends_observation_id: string | null
  row_transcript: string
  reconciliation_note: string
  identity_evidence_url: string
}
interface Ledger extends Artifact {
  data: {
    request: {
      name: string
      synthetic: boolean
      first_name: string
      last_name: string
      filing_start: string
      filing_end: string
      symbols: string[]
      observations: Observation[]
    }
    raw_source_id: string
    raw_source_hash: string
    blockers: string[]
    review_warning: string
    canonical_transactions: unknown[]
    clock_audit: {
      canonical_transaction_id: string
      observed_at: string
      disposition: string
      selected_observation_id: string
      event_id: string | null
    }[]
    source: {
      stream_id: string
      events: { event_id: string; category: string; published_at: string }[]
    }
  }
  approvals: {
    data: {
      approved_source_id: string
      approved_source_hash: string
      review: { review_note: string }
    }
  }[]
}
const base = '/research/congress'

export function CongressSources() {
  const qc = useQueryClient()
  const artifacts = useQuery({
    queryKey: ['congress-artifacts'],
    queryFn: () => api<Artifact[]>(base + '/artifacts'),
  })
  const list = useQuery({
    queryKey: ['congress-ledgers'],
    queryFn: () => api<(Artifact & { name: string; blockers: string[] })[]>(base + '/ledgers'),
  })
  const [selected, setSelected] = useState('')
  const detail = useQuery({
    queryKey: ['congress-ledger', selected],
    queryFn: () => api<Ledger>(base + '/ledgers/' + selected),
    enabled: !!selected,
  })
  const [year, setYear] = useState(2022),
    [documentId, setDocumentId] = useState(''),
    [capture, setCapture] = useState('')
  const [packet, setPacket] = useState(''),
    [note, setNote] = useState('')
  const [clockAck, setClockAck] = useState(false),
    [inventoryAck, setInventoryAck] = useState(false),
    [identityAck, setIdentityAck] = useState(false)
  const [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null),
    [receipt, setReceipt] = useState<Record<string, unknown> | null>(null)
  async function act(path: string, body: unknown, kind: 'collect' | 'prepare' | 'approve') {
    setBusy(true)
    setError(null)
    try {
      const result = await api<Record<string, unknown>>(base + path, 'POST', body)
      if (kind === 'prepare') {
        const ledger = result as unknown as Ledger
        setSelected(ledger.id)
        qc.setQueryData(['congress-ledger', ledger.id], ledger)
        setClockAck(false)
        setInventoryAck(false)
        setIdentityAck(false)
        setNote('')
      } else setReceipt(result)
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['congress-artifacts'] }),
        qc.invalidateQueries({ queryKey: ['congress-ledgers'] }),
        qc.invalidateQueries({ queryKey: ['congress-ledger', selected] }),
        qc.invalidateQueries({ queryKey: ['strategy-inputs'] }),
      ])
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }
  const ledger = detail.data
  return (
    <section className="congress-review">
      <PageTitle
        eyebrow="CONGRESS SOURCE REVIEW"
        title="Trace the disclosure before using it."
        description="Acquire official House records, reconcile explicit transaction identities, and review a bounded filing cohort. This workflow does not supply a complete Congress feed."
      />
      <p>
        <Link to="/congress/coverage">
          Full Congress inventory, acquisition progress and Senate access
        </Link>
      </p>
      <ErrorBox error={error || artifacts.error || list.error || detail.error} />
      <Panel title="1 · Retain source evidence">
        <p>
          Original PDFs and exact archived replays are retained with hashes. A verified capture is a
          conservative observed-public bound, never a filing-date substitute or certified first
          publication. No API key is required.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            void act('/house-index', { year }, 'collect')
          }}
        >
          <Field label="House index year">
            <input
              type="number"
              min={2012}
              max={2035}
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
            />
          </Field>
          <button disabled={busy}>Acquire official index</button>
        </form>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            void act(
              '/house-documents',
              { year, document_id: documentId, archive_capture: capture || null },
              'collect',
            )
          }}
        >
          <Field label="House document ID">
            <input
              required
              pattern="[0-9]{7,8}"
              value={documentId}
              onChange={(e) => setDocumentId(e.target.value)}
            />
          </Field>
          <Field
            label="Verified archive capture candidate (UTC YYYYMMDDhhmmss)"
            hint="Optional. The server verifies the actual response, matching bytes and Memento header; an unknown clock remains blocked."
          >
            <input
              pattern="[0-9]{14}"
              value={capture}
              onChange={(e) => setCapture(e.target.value)}
            />
          </Field>
          <button disabled={busy}>Acquire PDF and archive evidence</button>
        </form>
        {busy && <p role="status">Checking or retaining source evidence…</p>}
        {receipt && (
          <details open>
            <summary>Acquisition or approval result</summary>
            <pre>{JSON.stringify(receipt, null, 2)}</pre>
          </details>
        )}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Evidence</th>
                <th>Document</th>
                <th>Response</th>
                <th>Artifact reference</th>
              </tr>
            </thead>
            <tbody>
              {artifacts.data?.map((a) => (
                <tr key={a.id}>
                  <td>
                    <a href={'/api' + base + '/artifacts/' + a.id}>Download {a.kind}</a>
                  </td>
                  <td>
                    {a.metadata.year} · {a.metadata.document_id || 'index'}
                  </td>
                  <td>
                    {a.metadata.http_status}
                    <br />
                    {a.metadata.memento_datetime || 'No archive clock'}
                  </td>
                  <td>
                    <code>{a.id}</code>
                    <details>
                      <summary>Source URL and hash</summary>
                      <a href={a.source_url}>{a.source_url}</a>
                      <p>
                        <code>{a.content_hash}</code>
                      </p>
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      <Panel title="2 · Reconcile a reviewed row packet">
        <p>
          Transcribe selected rows from the retained PDFs. Assign explicit canonical transaction IDs
          and amendment predecessors; identical dates and amounts alone are insufficient. Include
          every selected-domain report, supporting originals and historical issuer identity
          evidence. Rows are manually reviewed; this is not automatic PDF extraction.
        </p>
        <p>
          The packet declares a named reporter, filing interval, company symbols, stream and
          conservative observation-coverage interval. Missing clocks, unresolved taxonomy or an
          incomplete index inventory block approval.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            try {
              void act('/ledgers', JSON.parse(packet), 'prepare')
            } catch (err) {
              setError(err)
            }
          }}
        >
          <Field label="Canonical Congress ledger JSON">
            <textarea
              required
              value={packet}
              onChange={(e) => setPacket(e.target.value)}
              rows={8}
              maxLength={4000000}
            />
          </Field>
          <button disabled={busy || !packet.trim()}>Prepare immutable ledger</button>
        </form>
        <Field label="Inspect retained Congress ledger">
          <select
            value={selected}
            onChange={(e) => {
              setSelected(e.target.value)
              setClockAck(false)
              setInventoryAck(false)
              setIdentityAck(false)
              setNote('')
              setReceipt(null)
            }}
          >
            <option value="">Choose a ledger</option>
            {list.data?.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name} · {l.blockers.length ? 'blocked' : 'ready for explicit review'}
              </option>
            ))}
          </select>
        </Field>
      </Panel>
      {ledger && (
        <>
          <Panel title={ledger.data.request.name}>
            {ledger.data.request.synthetic && (
              <p>
                <strong>SYNTHETIC demonstration source · explicitly selected</strong>
              </p>
            )}
            <p>
              {ledger.data.request.first_name} {ledger.data.request.last_name} · Filed{' '}
              {ledger.data.request.filing_start} through {ledger.data.request.filing_end} ·{' '}
              {ledger.data.request.symbols.join(', ')}
            </p>
            <p>
              <strong>
                {ledger.data.canonical_transactions.length} canonical transactions ·{' '}
                {ledger.data.source.events.length} strategy observations
              </strong>{' '}
              · Stream <code>{ledger.data.source.stream_id}</code>
            </p>
            <p>{ledger.data.review_warning}</p>
            {!!ledger.data.blockers.length && (
              <div role="alert">
                <strong>Approval blocked</strong>
                <ul>
                  {ledger.data.blockers.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Source row</th>
                    <th>Security / action</th>
                    <th>Transaction / notification</th>
                    <th>Disclosed USD range</th>
                    <th>Lineage</th>
                  </tr>
                </thead>
                <tbody>
                  {ledger.data.request.observations.map((o) => (
                    <tr key={o.observation_id}>
                      <td>
                        {o.observation_id}
                        <br />
                        {o.filing_kind}
                      </td>
                      <td>
                        {o.symbol} · {o.instrument}
                        <br />
                        {o.action}
                      </td>
                      <td>
                        {o.transaction_date}
                        <br />
                        {o.notification_date || 'Unknown'}
                      </td>
                      <td>
                        {o.amount_min ?? 'Unknown'}–{o.amount_max ?? 'Open / unknown'}
                      </td>
                      <td>
                        {o.canonical_transaction_id}
                        <br />
                        {o.amends_observation_id && 'Amends ' + o.amends_observation_id}
                        <details>
                          <summary>Row transcript and review</summary>
                          <p>{o.row_transcript}</p>
                          <p>{o.reconciliation_note}</p>
                          <a href={o.identity_evidence_url}>Historical issuer identity evidence</a>
                        </details>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
          <Panel title="3 · Audit the information timeline">
            <ol>
              {ledger.data.clock_audit.map((a, i) => (
                <li key={i}>
                  <strong>{a.observed_at}</strong>
                  <p>
                    {a.disposition.replaceAll('_', ' ')} · selected {a.selected_observation_id}
                  </p>
                  <p>
                    {a.event_id
                      ? 'Strategy observation retained'
                      : 'No new trade signal was emitted; inspect the retained facts and any blockers.'}
                  </p>
                </li>
              ))}
            </ol>
            <details>
              <summary>Immutable ledger and source audit</summary>
              <code>{ledger.content_hash}</code>
              <p>
                Raw source <code>{ledger.data.raw_source_id}</code> ·{' '}
                <code>{ledger.data.raw_source_hash}</code>
              </p>
              <pre>{JSON.stringify(ledger.data, null, 2)}</pre>
            </details>
          </Panel>
          <Panel title="4 · Explicit bounded source approval">
            <p>
              Approval creates a new eligible source revision and retains the raw ledger. It attests
              only this named filing cohort and policy. It does not authorize trading execution or
              establish broad Congress coverage.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault()
                void act(
                  '/ledgers/' + ledger.id + '/approve',
                  {
                    acknowledge_conservative_observation_clocks: clockAck,
                    attest_inventory_and_all_selected_rows: inventoryAck,
                    attest_identity_taxonomy_and_amendments: identityAck,
                    review_note: note,
                  },
                  'approve',
                )
              }}
            >
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={clockAck}
                  onChange={(e) => setClockAck(e.target.checked)}
                />
                I acknowledge conservative observed-public clocks and their limits.
              </label>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={inventoryAck}
                  onChange={(e) => setInventoryAck(e.target.checked)}
                />
                I reviewed the complete selected report inventory and all selected rows.
              </label>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={identityAck}
                  onChange={(e) => setIdentityAck(e.target.checked)}
                />
                I reviewed issuer identities, instrument/action categories and amendment links.
              </label>
              <Field label="Congress source review note">
                <textarea
                  required
                  minLength={40}
                  maxLength={2000}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              </Field>
              <button
                disabled={
                  busy ||
                  !!ledger.data.blockers.length ||
                  !clockAck ||
                  !inventoryAck ||
                  !identityAck ||
                  note.length < 40
                }
              >
                Approve bounded source revision
              </button>
            </form>
            {ledger.approvals.map((a) => (
              <p key={a.data.approved_source_id}>
                Eligible bounded revision: <code>{a.data.approved_source_id}</code> ·{' '}
                {a.data.review.review_note}
              </p>
            ))}
            <p>
              <Link to="/sources">Inspect strategy input revisions</Link> ·{' '}
              <Link to="/research">Return to the research journal</Link>
            </p>
          </Panel>
        </>
      )}
    </section>
  )
}
