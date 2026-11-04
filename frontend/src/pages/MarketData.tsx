import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Database, FileUp } from 'lucide-react'
import { api, useLab } from '../lib/api'
import { Badge, Empty, ErrorBox, Field, PageTitle, Panel } from '../components/ui'
import type { Dataset } from '../types'

export function MarketData() {
  const lab = useLab()
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [provider, setProvider] = useState('csv')
  const [bars, setBars] = useState('')
  const [fx, setFx] = useState('')
  const [actions, setActions] = useState('')
  const [synthetic, setSynthetic] = useState(false)
  const [complete, setComplete] = useState(false)
  const [reviewed, setReviewed] = useState(false)
  const [decisionTime, setDecisionTime] = useState('close_plus_30m')
  const [message, setMessage] = useState('')
  const [symbols, setSymbols] = useState('SPY')
  const [start, setStart] = useState('2018-01-01')
  const [end, setEnd] = useState('2022-12-31')
  const [error, setError] = useState<unknown>(null)
  const upload = useMutation({
    mutationFn: () =>
      api<Dataset>('/market-data/import-csv', 'POST', {
        name,
        provider,
        bars_csv: bars,
        fx_csv: fx,
        actions_csv: actions,
        corporate_actions_reviewed: reviewed,
        synthetic,
        dividends_complete: complete,
        decision_time: decisionTime,
      }),
    onSuccess: async (d) => {
      await qc.invalidateQueries({ queryKey: ['datasets'] })
      setMessage(`Imported ${d.name}. Revision ${d.content_hash.slice(0, 12)} is immutable.`)
    },
  })
  const fetchData = useMutation({
    mutationFn: () =>
      api<Dataset>('/market-data/alpaca', 'POST', {
        symbols: symbols.split(',').map((s) => s.trim().toUpperCase()),
        start,
        end,
        fx_csv: fx,
        actions_csv: actions,
        corporate_actions_reviewed: reviewed,
      }),
    onSuccess: async (d) => {
      await qc.invalidateQueries({ queryKey: ['datasets'] })
      setMessage(
        `Imported ${d.name} with the selected FX/action inputs. Its immutable revision is ready for coverage inspection.`,
      )
    },
  })
  const demo = useMutation({
    mutationFn: () => api<Dataset>('/market-data/demo', 'POST'),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ['datasets'] })
      setMessage(
        'Loaded the explicitly synthetic 2018–2022 demonstration dataset. It is not real market history.',
      )
    },
  })
  async function readFile(file: File | undefined, setter: (s: string) => void) {
    if (!file) return
    if (file.size > 20_000_000) {
      setError(new Error('CSV file exceeds 20 MB'))
      return
    }
    try {
      setter(await file.text())
      setError(null)
    } catch (e) {
      setError(e)
    }
  }
  return (
    <>
      <PageTitle
        eyebrow="EVIDENCE & PROVENANCE"
        title="Know what you are testing."
        description="Immutable daily candles, timestamped FX, and explicit data-quality assumptions."
        action={<Database size={27} className="title-icon" />}
      />
      <ErrorBox error={error || upload.error || fetchData.error || demo.error} />
      {message && (
        <div className="success" role="status">
          {message}
        </div>
      )}
      <Panel
        title="Dataset revisions"
        action={<span className="muted">{lab.datasets.length} snapshots</span>}
      >
        {lab.datasets.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Dataset / revision</th>
                  <th>Source</th>
                  <th>Coverage</th>
                  <th>FX</th>
                  <th>Quality</th>
                </tr>
              </thead>
              <tbody>
                {lab.datasets.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <strong>{d.name}</strong>
                      <small className="mono">{d.content_hash.slice(0, 16)}</small>
                      <Badge value={d.synthetic ? 'synthetic' : 'historical'} />
                    </td>
                    <td>
                      {d.provider}
                      <small>{d.metadata_json.availability_policy}</small>
                    </td>
                    <td>
                      {Object.entries(d.metadata_json.coverage).map(([s, c]) => (
                        <div key={s}>
                          <strong>{s}</strong> {c.start} → {c.end}
                          <small>
                            {c.bars} bars · {c.missing_sessions.length} missing sessions
                          </small>
                        </div>
                      ))}
                    </td>
                    <td>{d.metadata_json.fx_observations} observations</td>
                    <td>
                      {d.metadata_json.dividends_complete
                        ? 'Dividend completeness attested'
                        : 'Price-only'}
                      <small>
                        {d.metadata_json.actions} corporate actions ·{' '}
                        {d.metadata_json.corporate_actions_reviewed
                          ? 'split coverage reviewed'
                          : 'split review not attested'}
                      </small>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title="No market data imported"
            text="Import your historical source files below, connect Alpaca data, or explicitly load a synthetic demonstration dataset."
          />
        )}
      </Panel>
      <div className="two-columns">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            upload.mutate()
          }}
        >
          <Panel title="Import a combined CSV dataset" action={<FileUp size={17} />}>
            <div className="form-grid">
              <Field label="Dataset name">
                <input
                  required
                  value={name}
                  maxLength={160}
                  placeholder="Source, universe, and period"
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>
              <Field label="Provider / source">
                <input required value={provider} onChange={(e) => setProvider(e.target.value)} />
              </Field>
            </div>
            {[
              ['Daily candles (required)', bars, setBars],
              ['USD/SGD FX (required for SGD)', fx, setFx],
              ['Corporate actions (optional)', actions, setActions],
            ].map(([label, value, setter]) => (
              <Field key={String(label)} label={String(label)}>
                <input
                  aria-label={String(label)}
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => readFile(e.target.files?.[0], setter as (s: string) => void)}
                />
                <small>{String(value).length.toLocaleString()} characters loaded</small>
              </Field>
            ))}
            <Field label="Daily decision clock">
              <select value={decisionTime} onChange={(e) => setDecisionTime(e.target.value)}>
                <option value="close_plus_30m">Regular-session data: close + 30 minutes</option>
                <option value="20:30_America/New_York">
                  Includes extended-hours volume: 20:30 New York
                </option>
              </select>
            </Field>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={synthetic}
                onChange={(e) => setSynthetic(e.target.checked)}
              />{' '}
              This is synthetic demonstration data
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={reviewed}
                onChange={(e) => setReviewed(e.target.checked)}
              />{' '}
              I reviewed corporate-action coverage and supplied all effective splits
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={complete}
                onChange={(e) => setComplete(e.target.checked)}
              />{' '}
              Source attests complete dividend history
            </label>
            <button className="button" disabled={!bars || upload.isPending}>
              {upload.isPending ? 'Validating & importing…' : 'Validate and import'}
            </button>
            <details>
              <summary>CSV formats and timestamp rules</summary>
              <p>
                Use raw USD prices, ISO session dates, timezone-aware timestamps, and one row per
                symbol/session. Bars must become available at or after the official close. Holidays
                are excluded from gap checks.
              </p>
              <pre>
                symbol,session_date,open,high,low,close,volume,source_timestamp,available_at
              </pre>
              <pre>observed_at,available_at,rate</pre>
              <p>
                FX rate is SGD per USD. Availability is the actual publication time, separate from
                observation time.
              </p>
              <pre>symbol,session_date,available_at,kind,value,payment_date</pre>
              <p>
                Split values are new shares per old share. Dividends are USD per share on the
                ex-date, with an explicit payment date.
              </p>
            </details>
          </Panel>
        </form>
        <div>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              fetchData.mutate()
            }}
          >
            <Panel title="Fetch Alpaca historical bars">
              <p className="muted">
                Uses server-side data credentials and the IEX feed. Raw, unadjusted daily prices; no
                brokerage execution. Completed volume is available at an assumed 20:15 New York
                time, with decisions at 20:30. Current revised history is not publication-vintage
                data.
              </p>
              <Field label="Symbols">
                <input required value={symbols} onChange={(e) => setSymbols(e.target.value)} />
              </Field>
              <div className="form-grid">
                <Field label="Start date">
                  <input
                    required
                    type="date"
                    value={start}
                    onChange={(e) => setStart(e.target.value)}
                  />
                </Field>
                <Field label="End date">
                  <input
                    required
                    type="date"
                    value={end}
                    onChange={(e) => setEnd(e.target.value)}
                  />
                </Field>
              </div>
              <Field label="Historical FX CSV for this API import (optional)">
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => readFile(e.target.files?.[0], setFx)}
                />
                <small>
                  {fx.length.toLocaleString()} characters loaded; shared with the CSV form
                </small>
              </Field>
              <Field label="Corporate actions CSV for this API import (optional)">
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => readFile(e.target.files?.[0], setActions)}
                />
                <small>{actions.length.toLocaleString()} characters loaded</small>
              </Field>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={reviewed}
                  onChange={(e) => setReviewed(e.target.checked)}
                />{' '}
                I reviewed corporate-action coverage and supplied all effective splits
              </label>
              <button className="secondary" disabled={fetchData.isPending}>
                {fetchData.isPending ? 'Fetching…' : 'Fetch historical bars'}
              </button>
              <small>
                Requires Alpaca market-data access. FX and corporate actions are separate source
                inputs; missing coverage is never fabricated.
              </small>
            </Panel>
          </form>
          <Panel title="Explore the workflow">
            <p className="muted">
              Load deterministic, synthetic SPY candles and USD/SGD rates for 2018–2022. Use them to
              learn the app and verify accounting, never to judge real investment performance.
            </p>
            <button className="secondary" disabled={demo.isPending} onClick={() => demo.mutate()}>
              Load labeled synthetic dataset
            </button>
          </Panel>
        </div>
      </div>
    </>
  )
}
