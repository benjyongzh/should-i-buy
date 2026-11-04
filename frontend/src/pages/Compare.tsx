import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useLab, useResults } from '../lib/api'
import { Badge, Empty, ErrorBox, money, number, PageTitle, Panel, percent } from '../components/ui'
import { EquityChart } from '../components/EquityChart'

export function Compare() {
  const lab = useLab()
  const [params, setParams] = useSearchParams()
  const experiment = params.get('experiment') || ''
  const [ids, setIds] = useState<string[]>([])
  const [sort, setSort] = useState('total_return')
  const completed = lab.runs.filter((r) => r.status === 'completed')
  const selected = completed.filter(
    (r) => ids.includes(r.id) || (experiment && r.experiment_id === experiment),
  )
  const results = useResults(selected)
  const comparable =
    new Set(
      selected.map(
        (r) =>
          r.provenance.dataset_hash +
          ':' +
          r.provenance.profile_hash +
          ':' +
          r.provenance.engine_version,
      ),
    ).size <= 1
  const label = (id: string) => {
    const v = lab.versions.find((v) => v.id === id)
    return `${lab.strategies.find((s) => s.id === v?.strategy_id)?.name || 'Strategy'} · v${v?.number}`
  }
  const rows = selected
    .map((r, i) => ({ run: r, result: results[i]?.data }))
    .sort(
      (a, b) =>
        Number(b.result?.metrics[sort] ?? -Infinity) - Number(a.result?.metrics[sort] ?? -Infinity),
    )
  return (
    <>
      <PageTitle
        eyebrow="EXPERIMENT COMPARISON"
        title="Understand the trade-offs."
        description="Compare returns, risk, and execution costs together. Historical winners are research, not a forecast."
      />
      <ErrorBox error={results.find((r) => r.error)?.error} />
      <Panel title="Select completed runs">
        <label className="field">
          <span>Experiment group</span>
          <select
            value={experiment}
            onChange={(e) => {
              setIds([])
              setParams(e.target.value ? { experiment: e.target.value } : {})
            }}
          >
            <option value="">Choose runs manually</option>
            {lab.experiments.map((e) => (
              <option key={e.id} value={e.id}>
                {e.name}
              </option>
            ))}
          </select>
        </label>
        {!experiment && (
          <div className="compare-picker">
            {completed.map((r) => (
              <label key={r.id} className="checkbox">
                <input
                  type="checkbox"
                  checked={ids.includes(r.id)}
                  disabled={ids.length >= 6 && !ids.includes(r.id)}
                  onChange={(e) =>
                    setIds(e.target.checked ? [...ids, r.id] : ids.filter((x) => x !== r.id))
                  }
                />
                {label(r.strategy_version_id)} <small>{r.id.slice(0, 8)}</small>
                <Badge value={r.provenance.synthetic ? 'synthetic' : 'historical'} />
              </label>
            ))}
          </div>
        )}
        {!completed.length && (
          <Empty
            title="Complete a backtest to compare results"
            text="Multiple versions can share one profile and dataset while retaining independent portfolios."
            to="/backtests/new"
            label="Create an experiment"
          />
        )}
      </Panel>
      {!comparable && (
        <div className="warning">
          These runs use different profile settings or dataset revisions. They are not strictly
          comparable; review the disclosed assumptions below.
        </div>
      )}
      {selected.some((r) => r.provenance.synthetic) && (
        <div className="warning">
          Selected results include synthetic demonstration data. They do not establish real
          historical performance.
        </div>
      )}
      {selected.length > 0 && (
        <>
          <Panel title="Net equity curves">
            <EquityChart
              series={selected.flatMap((r, i) =>
                results[i]?.data
                  ? [{ name: label(r.strategy_version_id), equity: results[i].data!.equity }]
                  : [],
              )}
            />
          </Panel>
          <Panel
            title="Performance comparison"
            action={
              <select
                aria-label="Sort comparison"
                value={sort}
                onChange={(e) => setSort(e.target.value)}
              >
                <option value="total_return">Sort by net return</option>
                <option value="max_drawdown">Sort by drawdown</option>
                <option value="sharpe_ratio">Sort by Sharpe</option>
                <option value="total_commissions">Sort by commissions</option>
              </select>
            }
          >
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Strategy</th>
                    <th>Ending equity</th>
                    <th>Net return</th>
                    <th>Drawdown</th>
                    <th>Sharpe</th>
                    <th>Orders</th>
                    <th>Fees</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map(({ run: r, result: d }) => (
                    <tr key={r.id}>
                      <td>
                        <Link to={`/backtests/${r.id}`}>{label(r.strategy_version_id)}</Link>
                        <small>
                          {r.profile_snapshot.start_date} — {r.profile_snapshot.end_date}
                        </small>
                        <small>
                          Profile {r.provenance.profile_hash.slice(0, 8)} · Data{' '}
                          {r.provenance.dataset_hash.slice(0, 8)}
                        </small>
                      </td>
                      <td>
                        {money(
                          d?.metrics.ending_equity,
                          String(r.profile_snapshot.account_currency),
                        )}
                      </td>
                      <td>{percent(d?.metrics.total_return)}</td>
                      <td>{percent(d?.metrics.max_drawdown)}</td>
                      <td>{number(d?.metrics.sharpe_ratio)}</td>
                      <td>{String(d?.metrics.executed_orders ?? '—')}</td>
                      <td>
                        {money(
                          d?.metrics.total_commissions,
                          String(r.profile_snapshot.account_currency),
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        </>
      )}
    </>
  )
}
