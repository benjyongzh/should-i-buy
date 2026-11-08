import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { ErrorBox, Field, PageTitle, Panel } from '../components/ui'
interface Job {
  id: string
  status: string
  phase: string
  error: string | null
  request_payload: { start_year: number; end_year: number; chambers: string[] }
  state: {
    house_inventories?: Record<string, { ptr_reports?: number; error?: string }>
    senate_access?: { state: string; http_status?: number }
  }
  total_discovered?: number
  documents_downloaded?: number
  verified_archive_bounds?: number
  qualification?: string
  counts?: {
    chamber: string
    year: number
    status: string
    clock_status: string
    reports: number
  }[]
}
interface Item {
  id: string
  year: number
  report_key: string
  status: string
  clock_status: string
  request_payload: { reporter: string; filing_date: string }
  official_artifact_id: string | null
  text_artifact_id: string | null
  error: string | null
}
const base = '/research/congress'
export function CongressCoverage() {
  const qc = useQueryClient(),
    [params, setParams] = useSearchParams(),
    selected = params.get('collection') || ''
  const jobs = useQuery({
    queryKey: ['congress-collections'],
    queryFn: () => api<Job[]>(base + '/collections'),
    refetchInterval: 5000,
  })
  const job = useQuery({
    queryKey: ['congress-collection', selected],
    queryFn: () => api<Job>(base + '/collections/' + selected),
    enabled: !!selected,
    refetchInterval: 3000,
  })
  const [offset, setOffset] = useState(0),
    [reporter, setReporter] = useState(''),
    [textId, setTextId] = useState('')
  const items = useQuery({
    queryKey: ['congress-items', selected, offset, reporter],
    queryFn: () =>
      api<{ items: Item[]; has_more: boolean }>(
        `${base}/collections/${selected}/items?offset=${offset}&reporter=${encodeURIComponent(reporter)}`,
      ),
    enabled: !!selected,
    refetchInterval: 5000,
  })
  const text = useQuery({
    queryKey: ['congress-item-text', selected, textId],
    queryFn: () => api<unknown>(`${base}/collections/${selected}/items/${textId}/text`),
    enabled: !!selected && !!textId,
  })
  const imports = useQuery({
    queryKey: ['senate-imports'],
    queryFn: () =>
      api<
        {
          id: string
          data: {
            export_id: string
            part_number: number
            total_parts: number
            reports: unknown[]
            blockers: string[]
          }
        }[]
      >(base + '/senate-imports'),
  })
  const [start, setStart] = useState(2018),
    [end, setEnd] = useState(2025),
    [supports, setSupports] = useState('2017,2026'),
    [packet, setPacket] = useState(''),
    [busy, setBusy] = useState(false),
    [error, setError] = useState<unknown>(null)
  async function act(path: string, body: unknown = {}) {
    setBusy(true)
    setError(null)
    try {
      const result = await api<Job>(base + path, 'POST', body)
      if (path === '/collections') setParams({ collection: result.id })
      await Promise.all([
        qc.invalidateQueries({ queryKey: ['congress-collections'] }),
        qc.invalidateQueries({ queryKey: ['congress-collection'] }),
        qc.invalidateQueries({ queryKey: ['senate-imports'] }),
      ])
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }
  const active = job.data && ['queued', 'running'].includes(job.data.status)
  return (
    <section className="congress-review">
      <PageTitle
        eyebrow="FULL CONGRESS COVERAGE"
        title="Measure what is actually covered."
        description="Inventory all filers across the requested years, acquire immutable evidence in resumable batches, and keep missing access, posting clocks and row reviews visible."
      />
      <ErrorBox
        error={error || jobs.error || job.error || items.error || text.error || imports.error}
      />
      <Panel title="Start an all-filer collection">
        <p>
          Uses the confirmed personal, non-commercial research scope. Includes every PTR in the
          current House indexes, without a static ticker or politician list. An acquired PDF or
          extracted text is not a qualified transaction dataset. Senator access may require a normal
          browser session.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            void act('/collections', {
              request_id: crypto.randomUUID(),
              start_year: start,
              end_year: end,
              supporting_years: supports
                .split(',')
                .map((s) => s.trim())
                .filter(Boolean)
                .map(Number),
              chambers: ['house', 'senate'],
              lookup_archives: true,
              acknowledge_personal_noncommercial_use: true,
            })
          }}
        >
          <Field label="Congress start year">
            <input
              type="number"
              min={2012}
              value={start}
              onChange={(e) => setStart(Number(e.target.value))}
            />
          </Field>
          <Field label="Congress end year">
            <input
              type="number"
              min={2012}
              value={end}
              onChange={(e) => setEnd(Number(e.target.value))}
            />
          </Field>
          <Field
            label="Supporting index years"
            hint="Boundary originals, late filings and amendments are retained separately; they are not backdated into the strategy clock."
          >
            <input value={supports} onChange={(e) => setSupports(e.target.value)} />
          </Field>
          <button disabled={busy}>Start full-scope acquisition</button>
        </form>
        <Field label="Inspect Congress collection">
          <select
            value={selected}
            onChange={(e) => {
              setParams(e.target.value ? { collection: e.target.value } : {})
              setOffset(0)
              setTextId('')
            }}
          >
            <option value="">Choose a collection</option>
            {jobs.data?.map((j) => (
              <option key={j.id} value={j.id}>
                {j.request_payload.start_year}–{j.request_payload.end_year} · {j.status} ·{' '}
                {j.id.slice(0, 8)}
              </option>
            ))}
          </select>
        </Field>
      </Panel>
      {job.data && (
        <>
          <Panel title="Coverage and gaps">
            <p>
              <strong>
                {job.data.status} · {job.data.phase}
              </strong>
            </p>
            {job.data.error && <p role="alert">{job.data.error}</p>}
            <p>
              {job.data.documents_downloaded || 0} of {job.data.total_discovered || 0} discovered
              reports acquired · {job.data.verified_archive_bounds || 0} verified archive bounds
            </p>
            <p>
              <progress
                aria-label="Congress acquisition progress"
                value={job.data.documents_downloaded || 0}
                max={job.data.total_discovered || 1}
              />
            </p>
            <p>
              <strong>Full-period strategy eligibility: not qualified</strong>
            </p>
            <p>{job.data.qualification}</p>
            <p>
              Senate server access: {job.data.state.senate_access?.state || 'not tested yet'}{' '}
              {job.data.state.senate_access?.http_status || ''}. A403 or429 stops that source; no
              anti-bot bypass is attempted.
            </p>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>House index</th>
                    <th>Discovered PTRs</th>
                    <th>Inventory error</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(job.data.state.house_inventories || {}).map(([y, v]) => (
                    <tr key={y}>
                      <td>{y}</td>
                      <td>{v.ptr_reports ?? 'Unknown'}</td>
                      <td>{v.error || 'Validated current index; not original vintage'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>
              {active ? (
                <button
                  disabled={busy}
                  onClick={() => void act('/collections/' + selected + '/cancel')}
                >
                  Cancel collection
                </button>
              ) : (
                <button
                  disabled={busy}
                  onClick={() => void act('/collections/' + selected + '/resume')}
                >
                  Resume or retry missing evidence
                </button>
              )}
            </p>
            <details>
              <summary>Per-year acquisition and clock states</summary>
              <pre>{JSON.stringify(job.data.counts, null, 2)}</pre>
            </details>
          </Panel>
          <Panel title="Document review queue">
            <Field label="Filter filer name">
              <input
                value={reporter}
                onChange={(e) => {
                  setReporter(e.target.value)
                  setOffset(0)
                }}
              />
            </Field>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Year / report</th>
                    <th>Filer / filing date</th>
                    <th>Acquisition</th>
                    <th>Historical clock</th>
                    <th>Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {items.data?.items.map((i) => (
                    <tr key={i.id}>
                      <td>
                        {i.year} · {i.report_key}
                      </td>
                      <td>
                        {i.request_payload.reporter}
                        <br />
                        {i.request_payload.filing_date}
                      </td>
                      <td>
                        {i.status}
                        {i.error && <p>{i.error}</p>}
                      </td>
                      <td>{i.clock_status}</td>
                      <td>
                        {i.official_artifact_id && (
                          <a href={'/api' + base + '/artifacts/' + i.official_artifact_id}>
                            Retained response
                          </a>
                        )}
                        {i.text_artifact_id && (
                          <button className="secondary" onClick={() => setTextId(i.id)}>
                            Inspect unreviewed text
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>
              <button disabled={!offset} onClick={() => setOffset(Math.max(0, offset - 50))}>
                Previous reports
              </button>{' '}
              <button disabled={!items.data?.has_more} onClick={() => setOffset(offset + 50)}>
                Next reports
              </button>
            </p>
            {text.data !== undefined && (
              <details open>
                <summary>
                  Extracted text and unvalidated ticker candidates · not trade signals
                </summary>
                <pre>{JSON.stringify(text.data, null, 2)}</pre>
              </details>
            )}
            <p>
              <Link to="/congress">Review source rows, cross-year originals and amendments</Link>
            </p>
          </Panel>
        </>
      )}
      <Panel title="Senate normal-browser access and import">
        <p>
          If the official portal opens from your browser, use its normal acknowledgement and select
          the intended PTR/date/filer query. The reviewed exporter saves reports locally in parts.
          It makes no third-party requests and exports no session cookies. Do not bypass an access
          challenge.
        </p>
        <p>
          <a href="https://efdsearch.senate.gov/search/home/" target="_blank" rel="noreferrer">
            Open official Senate portal
          </a>{' '}
          ·{' '}
          <a href="/senate-browser-export.js" download>
            Download the reviewed browser exporter
          </a>
        </p>
        <p>
          Current captures do not establish historical first-public timestamps. All parts and query
          scope must be reviewed; imports remain ineligible for trading until clocks, identities and
          amendments are qualified.
        </p>
        <Field label="Senate browser export file">
          <input
            type="file"
            accept=".json,application/json"
            onChange={async (e) => {
              try {
                const f = e.target.files?.[0]
                if (f) {
                  if (f.size > 20000000) throw new Error('Use an export part below20MB')
                  setPacket(await f.text())
                }
              } catch (err) {
                setError(err)
              }
            }}
          />
        </Field>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            try {
              void act('/senate-imports', JSON.parse(packet))
            } catch (err) {
              setError(err)
            }
          }}
        >
          <Field label="Senate browser export JSON">
            <textarea rows={5} value={packet} onChange={(e) => setPacket(e.target.value)} />
          </Field>
          <button disabled={busy || !packet.trim()}>
            Import Senate capture as unreviewed evidence
          </button>
        </form>
        {imports.data?.map((i) => (
          <details key={i.id}>
            <summary>
              {i.data.export_id} · part {i.data.part_number}/{i.data.total_parts} ·{' '}
              {i.data.reports.length} reports · unqualified
            </summary>
            <ul>
              {i.data.blockers.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          </details>
        ))}
      </Panel>
    </section>
  )
}
