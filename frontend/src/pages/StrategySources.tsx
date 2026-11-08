import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Badge, ErrorBox, Field, PageTitle, Panel } from '../components/ui'
import type { StrategyCapabilities, StrategyInputRevision } from '../types'

type SourcePayload = Record<string, unknown> & {
  kind: string
  bars?: Record<string, unknown>[]
  states?: Record<string, unknown>[]
  events?: Record<string, unknown>[]
}

export function StrategySources() {
  const qc = useQueryClient()
  const catalog = useQuery({
    queryKey: ['strategy-inputs'],
    queryFn: () => api<StrategyInputRevision[]>('/strategy-inputs'),
  })
  const capabilities = useQuery({
    queryKey: ['strategy-capabilities'],
    queryFn: () => api<StrategyCapabilities>('/strategy-capabilities'),
  })
  const [selected, setSelected] = useState('')
  const [provider, setProvider] = useState('intraday')
  const [symbols, setSymbols] = useState('SPY')
  const [start, setStart] = useState('2018-01-02'),
    [end, setEnd] = useState('2018-01-31')
  const [minutes, setMinutes] = useState(5),
    [feed, setFeed] = useState('sip'),
    [timezone, setTimezone] = useState('')
  const [access, setAccess] = useState('subscription')
  const [tagRules, setTagRules] = useState('[]')
  const [template, setTemplate] = useState('intraday'),
    [text, setText] = useState(''),
    [format, setFormat] = useState('json'),
    [csv, setCSV] = useState('')
  const [review, setReview] = useState(''),
    [ack, setAck] = useState(false),
    [complete, setComplete] = useState(false)
  const [asOf, setAsOf] = useState(''),
    [publicOnly, setPublicOnly] = useState(true)
  const selectedSource = catalog.data?.find((s) => s.id === selected)
  const detail = useQuery({
    queryKey: ['strategy-input-export', selected],
    queryFn: () => api<{ data: SourcePayload }>(`/strategy-inputs/${selected}/export`),
    enabled: !!selected,
    staleTime: Infinity,
  })
  function inspect(id: string) {
    setSelected(id)
    setReview('')
    setAck(false)
    setComplete(false)
    setAsOf('')
  }
  async function retained(source: StrategyInputRevision) {
    await qc.invalidateQueries({ queryKey: ['strategy-inputs'] })
    inspect(source.id)
  }
  const prepare = useMutation({
    mutationFn: () =>
      api<StrategyInputRevision>(
        `/strategy-inputs/${provider === 'ratings' ? 'benzinga-ratings' : provider === 'news' ? 'alpaca-news' : 'alpaca-intraday'}`,
        'POST',
        {
          symbols: symbols
            .toUpperCase()
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean),
          start,
          end,
          ...(provider === 'intraday'
            ? { bar_minutes: minutes, feed, assumed_delay_seconds: 60 }
            : provider === 'ratings'
              ? { source_timezone: timezone }
              : { keyword_tags: JSON.parse(tagRules), access }),
        },
      ),
    onSuccess: retained,
  })
  const example = useMutation({
    mutationFn: () => api<SourcePayload>(`/strategy-input-templates/${template}`),
    onSuccess: (body) => {
      if (format === 'json') setText(JSON.stringify(body, null, 2))
      else {
        const { bars, states, events, ...metadata } = body
        const rows = bars || states || events || []
        setText(JSON.stringify(metadata, null, 2))
        const keys = Object.keys(rows[0] || {})
        const cell = (value: unknown) =>
          '"' +
          String(
            Array.isArray(value)
              ? value.join('|')
              : typeof value === 'object' && value !== null
                ? JSON.stringify(value)
                : (value ?? ''),
          ).replaceAll('"', '""') +
          '"'
        setCSV(
          [keys.join(','), ...rows.map((row) => keys.map((k) => cell(row[k])).join(','))].join(
            '\n',
          ),
        )
      }
    },
  })
  const ingest = useMutation({
    mutationFn: () =>
      api<StrategyInputRevision>(
        format === 'json' ? '/strategy-inputs/import' : '/strategy-inputs/import-csv',
        'POST',
        format === 'json' ? JSON.parse(text) : { metadata: JSON.parse(text), rows_csv: csv },
      ),
    onSuccess: retained,
  })
  const approve = useMutation({
    mutationFn: () =>
      api<StrategyInputRevision>(`/strategy-inputs/${selected}/approve`, 'POST', {
        acknowledge_publication_policy: ack,
        attest_complete_coverage: complete,
        review_note: review,
      }),
    onSuccess: retained,
  })
  const payload = detail.data?.data
  const rawRows =
    payload?.kind === 'intraday'
      ? (payload.bars ?? [])
      : payload?.kind === 'universe'
        ? (payload.states ?? [])
        : payload?.kind === 'events'
          ? (payload.events ?? [])
          : []
  const cutoff = asOf ? new Date(asOf + 'Z').getTime() : Infinity
  let visible = rawRows.filter(
    (row) =>
      new Date(String(row.available_at)).getTime() <= cutoff &&
      (!row.published_at || new Date(String(row.published_at)).getTime() <= cutoff) &&
      (!row.effective_at || new Date(String(row.effective_at)).getTime() <= cutoff) &&
      (!publicOnly || selectedSource?.kind !== 'events' || row.access === 'public'),
  )
  if (selectedSource?.kind === 'events') {
    const superseded = new Set(visible.map((r) => r.supersedes_event_id).filter(Boolean))
    visible = visible.filter((r) => !superseded.has(r.event_id))
  }
  visible = visible.map((row) =>
    row.score_available_at && Date.parse(String(row.score_available_at)) > cutoff
      ? { ...row, score: null }
      : row,
  )
  const configured = capabilities.data?.configured
  return (
    <>
      <PageTitle
        eyebrow="HISTORICAL STRATEGY INPUTS"
        title="Keep the information clock honest."
        description="Prepare immutable intraday prices, historical classifications, company news, ratings and public disclosures. Original revisions remain unchanged."
      />
      <ErrorBox
        error={
          catalog.error ||
          capabilities.error ||
          detail.error ||
          prepare.error ||
          example.error ||
          ingest.error ||
          approve.error
        }
      />
      <p className="notice">
        Source preparation does not certify history or make it eligible. Review publication/version
        timing and coverage before creating an eligible revision. Congress uses public disclosure
        time; analyst targets remain nominal and disclosed trade amounts remain ranges.
      </p>
      <Panel title="Server connections">
        <div className="timeline-controls">
          {(['alpaca', 'fred', 'llm', 'benzinga'] as const).map((key) => (
            <span key={key}>
              {key}: <strong>{configured?.[key] ? 'configured' : 'not configured'}</strong>
            </span>
          ))}
        </div>
        <small>
          Configured keys do not guarantee historical entitlements. Keys stay in the server .env;
          original CSV/JSON imports need no new API key.
        </small>
      </Panel>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          prepare.mutate()
        }}
      >
        <Panel title="Prepare a provider partition">
          <div className="form-grid">
            <Field label="Source preparation">
              <select
                aria-label="Source preparation"
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
              >
                <option value="intraday">Alpaca intraday bars</option>
                <option value="news">Alpaca / Benzinga company news</option>
                <option value="ratings">Benzinga analyst-rating changes</option>
              </select>
            </Field>
            <Field label="Symbols" hint="Up to five comma-separated symbols per provider request">
              <input
                aria-label="Source symbols"
                value={symbols}
                onChange={(e) => setSymbols(e.target.value)}
                required
              />
            </Field>
            <Field label="From">
              <input
                aria-label="Source from"
                type="date"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                required
              />
            </Field>
            <Field label="Through">
              <input
                aria-label="Source through"
                type="date"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                required
              />
            </Field>
            {provider === 'intraday' && (
              <>
                <Field label="Interval minutes">
                  <select
                    aria-label="Interval minutes"
                    value={minutes}
                    onChange={(e) => setMinutes(Number(e.target.value))}
                  >
                    {[1, 5, 15, 30, 60].map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Price feed">
                  <select
                    aria-label="Price feed"
                    value={feed}
                    onChange={(e) => setFeed(e.target.value)}
                  >
                    <option value="sip">SIP consolidated</option>
                    <option value="iex">IEX venue only</option>
                  </select>
                </Field>
              </>
            )}
            {provider === 'ratings' && (
              <Field label="Verified source timezone">
                <select
                  aria-label="Verified source timezone"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  required
                >
                  <option value="">Confirm from your source contract</option>
                  <option value="America/New_York">America/New_York</option>
                  <option value="UTC">UTC</option>
                </select>
              </Field>
            )}
            {provider === 'news' && (
              <Field label="Historical access">
                <select
                  aria-label="Historical access"
                  value={access}
                  onChange={(e) => setAccess(e.target.value)}
                >
                  <option value="subscription">Licensed/subscription feed</option>
                  <option value="public">Original public timing independently evidenced</option>
                </select>
              </Field>
            )}
          </div>
          {provider === 'news' && (
            <Field label="Optional deterministic keyword tags (JSON)">
              <textarea
                aria-label="Keyword tags JSON"
                value={tagRules}
                onChange={(e) => setTagRules(e.target.value)}
              />
              <small>
                Example: [{JSON.stringify({ tag: 'geopolitics', any_terms: ['Hormuz'] })}]. Rules
                are retained; no retrospective LLM sentiment is generated.
              </small>
            </Field>
          )}
          <p className="muted">
            Use partitions of at most 32 calendar days; combine non-overlapping approved revisions
            when running. Intraday preparation aggregates complete minute rows, assumes a disclosed
            60-second completion delay and omits missing intervals. Current vendor data may be
            revised; original vintages are not certified.
          </p>
          <button
            className="button"
            disabled={
              prepare.isPending ||
              (provider === 'ratings' ? !configured?.benzinga || !timezone : !configured?.alpaca)
            }
          >
            {prepare.isPending ? 'Preparing…' : 'Prepare source revision'}
          </button>
        </Panel>
      </form>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          ingest.mutate()
        }}
      >
        <Panel title="Import source files">
          <div className="form-grid">
            <Field label="Template family">
              <select
                aria-label="Template family"
                value={template}
                onChange={(e) => setTemplate(e.target.value)}
              >
                {['intraday', 'universe', 'news', 'analyst', 'congress', 'economic'].map((kind) => (
                  <option key={kind}>{kind}</option>
                ))}
              </select>
            </Field>
            <Field label="File format">
              <select
                aria-label="File format"
                value={format}
                onChange={(e) => {
                  setFormat(e.target.value)
                  setText('')
                  setCSV('')
                }}
              >
                <option value="json">Full JSON revision</option>
                <option value="csv">CSV rows with JSON metadata</option>
              </select>
            </Field>
          </div>
          <button type="button" className="secondary" onClick={() => example.mutate()}>
            Load labeled synthetic schema example
          </button>
          <Field label={format === 'json' ? 'Source revision JSON' : 'Source metadata JSON'}>
            <textarea
              aria-label="Source JSON"
              className="code-editor"
              value={text}
              onChange={(e) => setText(e.target.value)}
              required
            />
            <input
              aria-label="Upload source JSON"
              type="file"
              accept=".json,application/json"
              onChange={async (e) => {
                const file = e.target.files?.[0]
                if (file) setText(await file.text())
              }}
            />
          </Field>
          {format === 'csv' && (
            <Field label="Source CSV rows">
              <textarea
                aria-label="Source CSV rows"
                className="code-editor"
                value={csv}
                onChange={(e) => setCSV(e.target.value)}
                required
              />
              <input
                aria-label="Upload source CSV"
                type="file"
                accept=".csv,text/csv"
                onChange={async (e) => {
                  const file = e.target.files?.[0]
                  if (file) setCSV(await file.text())
                }}
              />
              <small>
                Array columns use | separators. The details column holds JSON. Required timestamp
                fields use explicit timezones; unknown publication times cannot be waived.
              </small>
            </Field>
          )}
          <button
            className="button"
            disabled={ingest.isPending || !text.trim() || (format === 'csv' && !csv.trim())}
          >
            Import immutable revision
          </button>
        </Panel>
      </form>
      <Panel title="Retained source revisions">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Source</th>
                <th>Kind / coverage</th>
                <th>Rows</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {catalog.data?.map((source) => (
                <tr key={source.id}>
                  <td>
                    <button className="link-button" onClick={() => inspect(source.id)}>
                      {source.name}
                    </button>
                    <small>{source.content_hash.slice(0, 12)}</small>
                    <Badge value={source.synthetic ? 'synthetic' : 'historical'} />
                  </td>
                  <td>
                    {source.kind}
                    {source.stream_id ? ' · ' + source.stream_id : ''}
                    {source.bar_minutes ? ' · ' + source.bar_minutes + 'm' : ''}
                    <small>
                      {source.coverage_start} — {source.coverage_end}
                    </small>
                  </td>
                  <td>{source.row_count}</td>
                  <td>
                    {source.reviewed
                      ? 'Reviewed eligible revision'
                      : 'Viewing-only / pending review'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      {selectedSource && (
        <Panel title={`Inspect source · ${selectedSource.name}`}>
          <p>{selectedSource.availability_policy}</p>
          <p>
            Coverage attested: {String(selectedSource.complete)} · Source access:{' '}
            {selectedSource.access_coverage} · Symbols: {selectedSource.symbols.join(', ')}
          </p>
          {selectedSource.category_catalog.length > 0 && (
            <p>Declared categories/tags: {selectedSource.category_catalog.join(', ')}</p>
          )}
          <div className="form-grid">
            <Field label="Historical cutoff (UTC)">
              <input
                aria-label="Historical cutoff UTC"
                type="datetime-local"
                value={asOf}
                onChange={(e) => setAsOf(e.target.value)}
              />
            </Field>
            {selectedSource.kind === 'events' && (
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={publicOnly}
                  onChange={(e) => setPublicOnly(e.target.checked)}
                />{' '}
                Public records only
              </label>
            )}
          </div>
          <p>
            {visible.length} available records; showing up to 50. The source export retains all
            original rows and versions.
          </p>
          <pre>{JSON.stringify(visible.slice(0, 50), null, 2)}</pre>
          {!selectedSource.reviewed && (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                approve.mutate()
              }}
            >
              <Field label="Source review note">
                <textarea
                  aria-label="Source review note"
                  value={review}
                  onChange={(e) => setReview(e.target.value)}
                  minLength={20}
                  maxLength={2000}
                  required
                />
              </Field>
              <label className="checkbox">
                <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} /> I
                reviewed original publication, version/score availability, source identity and
                access assumptions.
              </label>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={complete}
                  onChange={(e) => setComplete(e.target.checked)}
                />{' '}
                I attest the declared symbol/time coverage, including no-event periods. Missing
                original versions are not complete history.
              </label>
              <button
                className="button"
                disabled={!ack || !complete || review.trim().length < 20 || approve.isPending}
              >
                Create reviewed eligible revision
              </button>
            </form>
          )}
          {selectedSource.reviewed && (
            <p className="success">
              Reviewed immutable revision. Parent {selectedSource.parent_id} remains unchanged.
              Select this exact revision when scheduling.
            </p>
          )}
        </Panel>
      )}
    </>
  )
}
