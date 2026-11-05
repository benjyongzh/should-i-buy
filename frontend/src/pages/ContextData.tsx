import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../lib/api'
import { ErrorBox, Field, PageTitle, Panel } from '../components/ui'
import { ContextImport } from '../components/ContextImport'
import type { ContextSnapshot } from '../types'

interface Catalog {
  series_id: string
  name: string
  units: string
  key_required: boolean
  manual_only?: boolean
}
interface Export {
  data: {
    observations: {
      observation_date: string
      value: string
      available_at: string | null
      release_date: string | null
    }[]
  }
}
export function ContextData() {
  const qc = useQueryClient()
  const [series, setSeries] = useState('VIX')
  const [start, setStart] = useState('2018-01-01')
  const [end, setEnd] = useState('2025-12-31')
  const [selected, setSelected] = useState('')
  const [reviewNote, setReviewNote] = useState('')
  const [ackPolicy, setAckPolicy] = useState(false)
  const catalog = useQuery({
    queryKey: ['context-catalog'],
    queryFn: () => api<Catalog[]>('/research/context/catalog'),
  })
  const snapshots = useQuery({
    queryKey: ['context'],
    queryFn: () => api<ContextSnapshot[]>('/research/context'),
  })
  const snapshot = snapshots.data?.find((s) => s.id === selected)
  const detail = useQuery({
    queryKey: ['context-export', selected],
    queryFn: () => api<Export>(`/research/context/${selected}/export`),
    enabled: !!selected,
    staleTime: Infinity,
  })
  const fetchData = useMutation({
    mutationFn: () =>
      api<ContextSnapshot>('/research/context/fetch', 'POST', { series_id: series, start, end }),
    onSuccess: (data) => retained(data.id),
  })
  async function retained(id: string) {
    await qc.invalidateQueries({ queryKey: ['context'] })
    inspect(id)
  }
  function inspect(id: string) {
    setSelected(id)
    setReviewNote('')
    setAckPolicy(false)
  }
  const approve = useMutation({
    mutationFn: () =>
      api<ContextSnapshot>(`/research/context/${selected}/approve`, 'POST', {
        acknowledge_publication_policy: ackPolicy,
        review_note: reviewNote,
      }),
    onSuccess: (data) => retained(data.id),
  })
  return (
    <>
      <PageTitle
        eyebrow="MARKET CONTEXT"
        title="Understand the conditions."
        description="Retained source snapshots for reviewing strategies across 2018–2025 and other periods."
      />
      <p className="warning">
        Imports start viewing-only. Only explicitly reviewed revisions with known publication
        timestamps can drive strategy signals. VIX original publication times are unknown; FRED uses
        a conservative availability policy. Signal inputs do not replace accounting FX.
      </p>
      <ErrorBox
        error={catalog.error || snapshots.error || detail.error || fetchData.error || approve.error}
      />
      <form
        onSubmit={(e) => {
          e.preventDefault()
          fetchData.mutate()
        }}
      >
        <Panel title="Add a source snapshot">
          <Field label="Context series">
            <select
              aria-label="Context series"
              value={series}
              onChange={(e) => setSeries(e.target.value)}
            >
              {catalog.data
                ?.filter((c) => !c.manual_only)
                .map((c) => (
                  <option key={c.series_id} value={c.series_id}>
                    {c.name} · {c.units}
                  </option>
                ))}
            </select>
          </Field>
          <div className="form-grid">
            <Field label="From">
              <input
                aria-label="Context from"
                type="date"
                required
                value={start}
                onChange={(e) => setStart(e.target.value)}
              />
            </Field>
            <Field label="Through">
              <input
                aria-label="Context through"
                type="date"
                required
                value={end}
                onChange={(e) => setEnd(e.target.value)}
              />
            </Field>
          </div>
          <p>
            {series === 'VIX'
              ? 'Public Cboe download; no key needed.'
              : 'Uses the server-side FRED_API_KEY. Initial-release observations; missing values stay missing.'}
          </p>
          <button className="button" disabled={fetchData.isPending}>
            {fetchData.isPending ? 'Retrieving & validating…' : 'Fetch context snapshot'}
          </button>
        </Panel>
      </form>
      <ContextImport series={catalog.data || []} onSuccess={retained} />
      <Panel title="Immutable source snapshots">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Series</th>
                <th>Requested period</th>
                <th>Observations</th>
                <th>Source / revision</th>
                <th>Inspect</th>
              </tr>
            </thead>
            <tbody>
              {snapshots.data?.map((s) => (
                <tr key={s.id}>
                  <td>
                    {s.synthetic ? 'SYNTHETIC · ' : ''}
                    {s.name}
                    <small>
                      {s.research_only === false ? 'Strategy-eligible · reviewed' : 'Viewing only'}
                    </small>
                  </td>
                  <td>
                    {s.requested_start} → {s.requested_end}
                  </td>
                  <td>
                    {s.observation_count}
                    <small>{s.missing_omitted} missing values omitted</small>
                  </td>
                  <td>
                    {s.source}
                    <small className="mono">{s.content_hash.slice(0, 16)}</small>
                  </td>
                  <td>
                    <button type="button" className="secondary" onClick={() => inspect(s.id)}>
                      Inspect {s.series_id}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!snapshots.data?.length && <p>No context snapshots yet.</p>}
      </Panel>
      {snapshot && detail.data && (
        <Panel title={`${snapshot.name} · ${snapshot.units}`}>
          <p>{snapshot.availability_policy}</p>
          {snapshot.research_only === false ? (
            <p>
              Strategy-eligible revision. Source: {snapshot.source_snapshot_id}
              <br />
              {snapshot.review_note}
            </p>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                approve.mutate()
              }}
            >
              <p>
                Review source rights, values, coverage and the publication policy before approving.
                Unknown timestamps cannot be waived. Approval creates a new immutable revision.
              </p>
              <Field label="Source review note">
                <textarea
                  required
                  minLength={20}
                  maxLength={2000}
                  value={reviewNote}
                  onChange={(e) => setReviewNote(e.target.value)}
                />
              </Field>
              <label className="checkbox">
                <input
                  type="checkbox"
                  required
                  checked={ackPolicy}
                  onChange={(e) => setAckPolicy(e.target.checked)}
                />
                I reviewed and acknowledge this source's publication availability policy.
              </label>
              <button
                className="button"
                disabled={!ackPolicy || reviewNote.trim().length < 20 || approve.isPending}
              >
                Create strategy-eligible revision
              </button>
            </form>
          )}
          <ResponsiveContainer width="100%" height={300}>
            <LineChart
              data={detail.data.data.observations.map((p) => ({
                date: p.observation_date,
                value: Number(p.value),
              }))}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" minTickGap={60} />
              <YAxis domain={['auto', 'auto']} />
              <Tooltip />
              <Line dataKey="value" dot={false} isAnimationActive={false} stroke="#0e9f8f" />
            </LineChart>
          </ResponsiveContainer>
          <small>
            Chart dates are observation dates, not release dates. Lines connect reported
            observations for display; missing source values were not filled.
          </small>
          <p>
            <a
              href={`/api/research/context/${snapshot.id}/export`}
              target="_blank"
              rel="noreferrer"
            >
              Open complete snapshot JSON and source hashes
            </a>
          </p>
        </Panel>
      )}
    </>
  )
}
