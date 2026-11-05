import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { api, useLab } from '../lib/api'
import { Badge, Empty, ErrorBox, Field, money, PageTitle, Panel, short } from '../components/ui'
import type { ContextSnapshot, Run, StrategyInputRevision } from '../types'

export function Backtests() {
  const lab = useLab()
  return (
    <>
      <PageTitle
        eyebrow="SIMULATION QUEUE"
        title="Put your rules through time."
        description="Persistent runs, independent portfolios, and a record of every assumption."
        action={
          <Link className="button" to="/backtests/new">
            <Plus size={16} /> New backtest
          </Link>
        }
      />
      <Panel title="All backtests">
        {lab.runs.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Run / strategy</th>
                  <th>Period</th>
                  <th>Capital</th>
                  <th>Dataset</th>
                  <th>Status</th>
                  <th>Progress</th>
                </tr>
              </thead>
              <tbody>
                {lab.runs.map((r) => {
                  const v = lab.versions.find((v) => v.id === r.strategy_version_id)
                  return (
                    <tr key={r.id}>
                      <td>
                        <Link to={`/backtests/${r.id}`}>
                          <strong>
                            {lab.strategies.find((s) => s.id === v?.strategy_id)?.name ||
                              'Strategy'}{' '}
                            · v{v?.number}
                          </strong>
                        </Link>
                        <small className="mono">{short(r.id)}</small>
                      </td>
                      <td>
                        {r.profile_snapshot.start_date}
                        <small>to {r.profile_snapshot.end_date}</small>
                      </td>
                      <td>
                        {money(
                          r.profile_snapshot.starting_capital,
                          String(r.profile_snapshot.account_currency),
                        )}
                      </td>
                      <td>
                        {lab.datasets.find((d) => d.id === r.dataset_id)?.name}
                        <small>
                          <Badge value={r.provenance.synthetic ? 'synthetic' : 'historical'} />
                        </small>
                      </td>
                      <td>
                        <Badge value={r.status} />
                      </td>
                      <td>
                        <progress value={r.progress} max={100} />
                        <small>{r.progress}%</small>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title="No backtests yet"
            text="Publish a strategy, select a dataset, and apply a shared profile to start your first run."
            to="/backtests/new"
            label="Configure a backtest"
          />
        )}
      </Panel>
    </>
  )
}

export function NewBacktest() {
  const lab = useLab()
  const [profileId, setProfile] = useState('')
  const [datasetId, setDataset] = useState('')
  const [selected, setSelected] = useState<string[]>([])
  const [name, setName] = useState('')
  const [ack, setAck] = useState(false)
  const [contexts, setContexts] = useState<string[]>([])
  const [inputIds, setInputIds] = useState<string[]>([])
  const inputs = useQuery({
    queryKey: ['strategy-inputs'],
    queryFn: () => api<StrategyInputRevision[]>('/strategy-inputs'),
  })
  const readiness = useMutation({
    mutationFn: () =>
      Promise.all(
        selected.map(async (id) => ({
          id,
          ...(await api<{ ready_to_run: boolean; blockers: string[]; requirements: unknown }>(
            '/strategy-definitions/requirements',
            'POST',
            {
              config: lab.versions.find((v) => v.id === id)!.config,
              profile_id: profileId,
              dataset_id: datasetId,
              strategy_input_ids: inputIds,
              context_snapshot_ids: contexts,
            },
          )),
        })),
      ),
  })
  const readinessSelection = JSON.stringify([selected, profileId, datasetId, inputIds, contexts])
  useEffect(() => {
    readiness.reset()
  }, [readinessSelection])
  const sources = useQuery({
    queryKey: ['context'],
    queryFn: () => api<ContextSnapshot[]>('/research/context'),
  })
  const navigate = useNavigate()
  const qc = useQueryClient()
  const profile = lab.profiles.find((p) => p.id === profileId)
  const dataset = lab.datasets.find((d) => d.id === datasetId)
  const syntheticInputs =
    dataset?.synthetic ||
    sources.data?.some((s) => contexts.includes(s.id) && s.synthetic) ||
    inputs.data?.some((s) => inputIds.includes(s.id) && s.synthetic)
  const submit = useMutation({
    mutationFn: () =>
      api<Run[]>('/backtests', 'POST', {
        strategy_version_ids: selected,
        profile_id: profileId,
        dataset_id: datasetId,
        experiment_name: name,
        acknowledge_synthetic: ack,
        context_snapshot_ids: contexts,
        strategy_input_ids: inputIds,
      }),
    onSuccess: async (rows) => {
      await qc.invalidateQueries()
      navigate(
        rows.length === 1
          ? `/backtests/${rows[0].id}`
          : `/compare?experiment=${rows[0].experiment_id}`,
      )
    },
  })
  return (
    <>
      <PageTitle
        eyebrow="NEW EXPERIMENT"
        title="Same conditions. Different ideas."
        description="Choose immutable strategy versions and run them against one shared profile and dataset."
      />
      <ErrorBox error={submit.error || sources.error || inputs.error || readiness.error} />
      <form
        onSubmit={(e) => {
          e.preventDefault()
          submit.mutate()
        }}
      >
        <div className="editor-layout">
          <div>
            <Panel title="1. Choose published versions">
              {lab.versions.length ? (
                lab.strategies
                  .filter((s) => !s.archived)
                  .map((s) => (
                    <div className="version-picker" key={s.id}>
                      <h3>{s.name}</h3>
                      {lab.versions
                        .filter((v) => v.strategy_id === s.id)
                        .map((v) => (
                          <label className="check-row" key={v.id}>
                            <input
                              type="checkbox"
                              checked={selected.includes(v.id)}
                              onChange={(e) =>
                                setSelected(
                                  e.target.checked
                                    ? [...selected, v.id]
                                    : selected.filter((x) => x !== v.id),
                                )
                              }
                            />
                            <span>
                              <strong>Version {v.number}</strong>
                              <small>
                                {v.change_summary || 'Published definition'} ·{' '}
                                {v.config_hash.slice(0, 8)}
                              </small>
                            </span>
                          </label>
                        ))}
                    </div>
                  ))
              ) : (
                <Empty
                  title="Publish a strategy first"
                  text="Only immutable published versions can be scheduled."
                  to="/strategies/new"
                  label="Create a strategy"
                />
              )}
            </Panel>
            <Panel title="2. Set shared financial assumptions">
              <Field label="Backtest profile">
                <select required value={profileId} onChange={(e) => setProfile(e.target.value)}>
                  <option value="">Select a profile</option>
                  {lab.profiles.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Link className="text-link" to="/profiles">
                Create or edit profiles ↗
              </Link>
              {profile && (
                <div className="assumption-grid">
                  <div>
                    <small>Starting capital</small>
                    <strong>
                      {money(
                        profile.config.starting_capital,
                        String(profile.config.account_currency),
                      )}
                    </strong>
                  </div>
                  <div>
                    <small>Fixed fee / order</small>
                    <strong>
                      {money(profile.config.fixed_fee, String(profile.config.account_currency))}
                    </strong>
                  </div>
                  <div>
                    <small>Period</small>
                    <strong>
                      {profile.config.start_date} — {profile.config.end_date}
                    </strong>
                  </div>
                  <div>
                    <small>Universe / benchmark</small>
                    <strong>
                      {(profile.config.symbols as string[]).join(', ')} / {profile.config.benchmark}
                    </strong>
                  </div>
                </div>
              )}
            </Panel>
            <Panel title="3. Select the evidence">
              <Field label="Dataset revision">
                <select
                  required
                  value={datasetId}
                  onChange={(e) => {
                    setDataset(e.target.value)
                    setAck(false)
                  }}
                >
                  <option value="">Select an immutable dataset</option>
                  {lab.datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.synthetic ? 'SYNTHETIC · ' : ''}
                      {d.name} · {d.content_hash.slice(0, 8)}
                    </option>
                  ))}
                </select>
              </Field>
              {dataset && (
                <>
                  <p className="muted">
                    {dataset.metadata_json.fx_observations} FX observations ·{' '}
                    {dataset.metadata_json.dividends_complete
                      ? 'Dividends attested complete'
                      : 'Price-only'}
                  </p>
                  {Object.entries(dataset.metadata_json.coverage).map(([s, c]) => (
                    <p key={s}>
                      <strong>{s}</strong> · {c.start} — {c.end} · {c.missing_sessions.length}{' '}
                      missing sessions
                    </p>
                  ))}
                </>
              )}
              <h3>Reviewed external signal inputs</h3>
              <p>
                Required for external expressions.{' '}
                <Link to="/context">Import and review sources</Link> first. Exact revisions are
                frozen for all selected runs.
              </p>
              {sources.data
                ?.filter((s) => s.research_only === false)
                .map((s) => (
                  <label className="check-row" key={s.id}>
                    <input
                      type="checkbox"
                      checked={contexts.includes(s.id)}
                      disabled={contexts.length >= 20 && !contexts.includes(s.id)}
                      onChange={(e) => {
                        setContexts(
                          e.target.checked
                            ? [...contexts, s.id]
                            : contexts.filter((id) => id !== s.id),
                        )
                        setAck(false)
                      }}
                    />
                    <span>
                      {s.synthetic ? 'SYNTHETIC · ' : ''}
                      {s.series_id} · {s.content_hash.slice(0, 12)}
                      <small>
                        {s.requested_start} — {s.requested_end} · {s.units}
                      </small>
                    </span>
                  </label>
                ))}
              <h3>Reviewed strategy sources</h3>
              <p>
                Intraday prices, historical sectors, news, analyst changes and Congress disclosures.{' '}
                <Link to="/sources">Import and review sources</Link>. Only reviewed revisions can be
                selected; exact hashes are retained with every run.
              </p>
              {inputs.data
                ?.filter((s) => s.reviewed)
                .map((s) => (
                  <label className="check-row" key={s.id}>
                    <input
                      type="checkbox"
                      checked={inputIds.includes(s.id)}
                      disabled={inputIds.length >= 100 && !inputIds.includes(s.id)}
                      onChange={(e) => {
                        setInputIds(
                          e.target.checked
                            ? [...inputIds, s.id]
                            : inputIds.filter((id) => id !== s.id),
                        )
                        setAck(false)
                      }}
                    />
                    <span>
                      {s.synthetic ? 'SYNTHETIC · ' : ''}
                      {s.name} · {s.kind} · {s.content_hash.slice(0, 12)}
                      <small>
                        {s.coverage_start} — {s.coverage_end} · {s.symbols.join(', ')}
                      </small>
                    </span>
                  </label>
                ))}
              {syntheticInputs && (
                <label className="checkbox warning">
                  <input
                    required
                    type="checkbox"
                    checked={ack}
                    onChange={(e) => setAck(e.target.checked)}
                  />{' '}
                  I understand this is synthetic data, not historical investment performance.
                </label>
              )}
            </Panel>
          </div>
          <aside>
            <Panel title="Experiment summary">
              <Field label="Experiment name (optional)">
                <input
                  value={name}
                  maxLength={160}
                  placeholder="e.g. Moving-average sensitivity"
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>
              <div className="summary-count">
                <strong>{selected.length}</strong>
                <span>independent virtual portfolios</span>
              </div>
              <p className="muted">
                All versions use identical capital, fees, market data, benchmark, and date range.
                Coverage is validated before jobs enter the queue.
              </p>
              <button
                className="button full"
                disabled={
                  !selected.length ||
                  !profileId ||
                  !datasetId ||
                  submit.isPending ||
                  !!(syntheticInputs && !ack)
                }
              >
                {submit.isPending ? 'Validating coverage…' : 'Queue backtests'}
              </button>
              <button
                type="button"
                className="secondary full"
                disabled={!selected.length || !profileId || !datasetId || readiness.isPending}
                onClick={() => readiness.mutate()}
              >
                Check selected data readiness
              </button>
              {readiness.data?.map((report) => (
                <div key={report.id}>
                  <strong>
                    Version {lab.versions.find((v) => v.id === report.id)?.number}:{' '}
                    {report.ready_to_run ? 'Ready with checked inputs' : 'Blocked'}
                  </strong>
                  {report.blockers.map((b, i) => (
                    <p className="warning" key={i}>
                      {b}
                    </p>
                  ))}
                  <details>
                    <summary>Required historical inputs</summary>
                    <pre>{JSON.stringify(report.requirements, null, 2)}</pre>
                  </details>
                </div>
              ))}
              <small>
                Simulation runs in the background worker. You can safely leave this page.
              </small>
            </Panel>
          </aside>
        </div>
      </form>
    </>
  )
}
