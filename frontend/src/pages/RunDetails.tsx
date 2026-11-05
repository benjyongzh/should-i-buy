import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, useCashBenchmarks, useLab } from '../lib/api'
import { Badge, ErrorBox, money, number, PageTitle, Panel, percent, Stat } from '../components/ui'
import { EquityChart } from '../components/EquityChart'
import { PeriodPerformance } from '../components/PeriodPerformance'
import { PerformanceTimeline } from '../components/PerformanceTimeline'
import type { Result, Run } from '../types'

export function RunDetails() {
  const { id } = useParams()
  const lab = useLab()
  const qc = useQueryClient()
  const [filter, setFilter] = useState('')
  const [tab, setTab] = useState('orders')
  const [page, setPage] = useState(0)
  const run = useQuery({
    queryKey: ['run', id],
    queryFn: () => api<Run>(`/backtests/${id}`),
    refetchInterval: (q) =>
      ['queued', 'running'].includes(q.state.data?.status || 'queued') ? 1500 : false,
  })
  const result = useQuery({
    queryKey: ['result', id],
    queryFn: () => api<Result>(`/backtests/${id}/results`),
    enabled: run.data?.status === 'completed',
    staleTime: Infinity,
  })
  const cash = useCashBenchmarks(run.data?.status === 'completed' ? [run.data] : [])
  const cancel = useMutation({
    mutationFn: () => api(`/backtests/${id}/cancel`, 'POST'),
    onSuccess: () => qc.invalidateQueries(),
  })
  const r = run.data
  const data = result.data
  const m = data?.metrics
  const currency = String(r?.profile_snapshot.account_currency || 'SGD')
  const v = lab.versions.find((v) => v.id === r?.strategy_version_id)
  const name = lab.strategies.find((s) => s.id === v?.strategy_id)?.name || 'Backtest'
  const orders =
    data?.orders.filter((o) =>
      [o.symbol, o.side, o.status, o.type, o.reason, o.rejection_reason]
        .join(' ')
        .toLowerCase()
        .includes(filter.toLowerCase()),
    ) || []
  return (
    <>
      <PageTitle
        eyebrow="BACKTEST REPORT"
        title={`${name}${v ? ' · v' + v.number : ''}`}
        description={`Run ${id?.slice(0, 8)} · ${r?.profile_snapshot.start_date || ''} — ${r?.profile_snapshot.end_date || ''}`}
        action={r && <Badge value={r.status} />}
      />
      <ErrorBox error={run.error || result.error || cancel.error || cash[0]?.error} />
      {r && (
        <>
          {r.provenance.synthetic && (
            <div className="warning">
              SYNTHETIC DEMONSTRATION · These are simulated fixture results, not real historical
              investment performance.
            </div>
          )}
          {r.status === 'failed' && <ErrorBox error={r.error} />}{' '}
          {['queued', 'running'].includes(r.status) && (
            <Panel
              title={r.status === 'queued' ? 'Waiting for a worker' : 'Simulation in progress'}
            >
              <progress className="full" max={100} value={r.progress} />
              <p>{r.progress}% processed · Runs continue after you leave this page.</p>
              <button
                className="secondary"
                disabled={cancel.isPending}
                onClick={() => cancel.mutate()}
              >
                Cancel at next safe checkpoint
              </button>
            </Panel>
          )}
        </>
      )}
      {data && m && (
        <>
          <div className="stats-grid">
            <Stat
              label="Ending portfolio value"
              value={money(m.ending_equity, currency)}
              detail={`Start ${money(m.starting_equity, currency)}`}
            />
            <Stat
              label={m.return_method ? 'Net time-weighted return' : 'Net total return'}
              value={percent(m.total_return)}
              detail={`Benchmark ${percent(m.benchmark_total_return)}`}
            />
            <Stat
              label="Maximum drawdown"
              value={percent(m.max_drawdown)}
              detail={`${m.drawdown_duration_sessions} sessions longest drawdown`}
            />
            <Stat
              label="Sharpe ratio"
              value={number(m.sharpe_ratio)}
              detail="Daily returns · 252-session annualization"
            />
          </div>
          {r && (
            <PerformanceTimeline
              entries={[
                {
                  run: r,
                  name: `${name}${v ? ' · v' + v.number : ''} · ${r.id.slice(0, 8)}`,
                  result: data,
                  cash: cash[0]?.data,
                },
              ]}
            />
          )}
          {id && <PeriodPerformance runId={id} currency={currency} />}
          <div className="two-columns">
            <Panel title="Drawdown">
              <EquityChart drawdown series={[{ name: 'Strategy', equity: data.equity }]} />
            </Panel>
            <Panel title="Performance & costs">
              <div className="metric-list">
                {[
                  ['Completed exit tranches', m.completed_trades],
                  ['Investment P&L (deposits excluded)', money(m.absolute_pnl, currency)],
                  ...(m.return_method
                    ? [
                        ['Salary contributions', money(m.total_contributions, currency)],
                        ['Total contributed capital', money(m.total_contributed_capital, currency)],
                        ['Investor money-weighted return', percent(m.money_weighted_return)],
                      ]
                    : []),
                  ['Executed orders', m.executed_orders],
                  ['Win rate', percent(m.win_rate)],
                  ['Annualized return', percent(m.annualized_return)],
                  ['Annualized volatility', percent(m.annualized_volatility)],
                  ['Gross return (cost-free replay)', percent(m.gross_return)],
                  ['Cost add-back return', percent(m.cost_addback_return)],
                  ['Commissions', money(m.total_commissions, currency)],
                  ['Slippage & spread', money(m.total_slippage_and_spread, currency)],
                  ['FX costs', money(m.total_fx_costs, currency)],
                  ['Average market exposure', percent(m.market_exposure)],
                  ['Profit factor', number(m.profit_factor)],
                  ['Average holding sessions', number(m.average_holding_sessions)],
                ].map(([label, value]) => (
                  <div key={String(label)}>
                    <span>{label}</span>
                    <strong>{value as string}</strong>
                  </div>
                ))}
              </div>
              <small>
                Partial sales count as exit tranches using pooled average cost. For funded runs,
                return and drawdown exclude deposits; investor return needs at least 365 elapsed
                days. Cost add-back is unavailable for funded runs; gross return uses a separate
                replay.
              </small>
            </Panel>
          </div>
          <Panel
            title="Execution audit"
            action={
              <input
                className="compact-search"
                placeholder="Filter symbol, status, or reason"
                aria-label="Filter orders"
                value={filter}
                onChange={(e) => {
                  setFilter(e.target.value)
                  setPage(0)
                }}
              />
            }
          >
            <div className="segmented audit-tabs">
              {['orders', 'trades', 'signals', 'ledger'].map((t) => (
                <button
                  key={t}
                  className={tab === t ? 'selected' : ''}
                  onClick={() => {
                    setTab(t)
                    setPage(0)
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
            <div className="table-wrap">
              {tab === 'orders' ? (
                <table>
                  <thead>
                    <tr>
                      <th>Symbol / action</th>
                      <th>Submitted / executed</th>
                      <th>Quantity</th>
                      <th>Price USD</th>
                      <th>Fee {currency}</th>
                      <th>Status / reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.slice(page * 50, page * 50 + 50).map((o) => (
                      <tr key={o.id}>
                        <td>
                          <strong>{o.symbol}</strong>
                          <small>
                            {o.side} · {o.type}
                          </small>
                        </td>
                        <td>
                          {o.submitted_at.slice(0, 16)}
                          <small>{o.executed_at?.slice(0, 16) || 'Not executed'}</small>
                        </td>
                        <td>{o.quantity}</td>
                        <td>{o.execution_price ? Number(o.execution_price).toFixed(4) : '—'}</td>
                        <td>{money(o.fees, currency)}</td>
                        <td>
                          <Badge value={o.status} />
                          <small>{o.rejection_reason || o.reason}</small>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : tab === 'trades' ? (
                <table>
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Opened</th>
                      <th>Closed</th>
                      <th>Quantity</th>
                      <th>Realized P&L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.trades.slice(page * 50, page * 50 + 50).map((t, i) => (
                      <tr key={i}>
                        <td>{t.symbol}</td>
                        <td>{t.opened_at.slice(0, 10)}</td>
                        <td>{t.closed_at.slice(0, 10)}</td>
                        <td>{t.quantity}</td>
                        <td>{money(t.realized_pnl, currency)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : tab === 'signals' ? (
                <div className="signals">
                  {data.signals.slice(page * 50, page * 50 + 50).map((s, i) => (
                    <details key={i}>
                      <summary>
                        {s.timestamp.slice(0, 10)} · {s.symbol} · {s.action} ·{' '}
                        {s.condition_result === null
                          ? 'insufficient warm-up'
                          : String(s.condition_result)}
                      </summary>
                      <pre>{JSON.stringify(s.rule, null, 2)}</pre>
                      {s.exit_rule && (
                        <pre>
                          {JSON.stringify(
                            {
                              exit_rule: s.exit_rule,
                              exit_condition_result: s.exit_condition_result,
                              reason: s.reason,
                            },
                            null,
                            2,
                          )}
                        </pre>
                      )}
                      {s.external_inputs && <pre>{JSON.stringify(s.external_inputs, null, 2)}</pre>}
                    </details>
                  ))}
                </div>
              ) : (
                <pre>{JSON.stringify(data.ledger.slice(page * 50, page * 50 + 50), null, 2)}</pre>
              )}
            </div>
            <div className="pagination">
              <button className="secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>
                Previous
              </button>
              <small>Page {page + 1} · 50 records per page</small>
              <button
                className="secondary"
                disabled={
                  (tab === 'orders'
                    ? orders.length
                    : tab === 'trades'
                      ? data.trades.length
                      : tab === 'signals'
                        ? data.signals.length
                        : data.ledger.length) <=
                  (page + 1) * 50
                }
                onClick={() => setPage(page + 1)}
              >
                Next
              </button>
            </div>
          </Panel>
          <Panel title="Open positions at the final mark">
            <pre>{JSON.stringify(data.positions, null, 2)}</pre>
            <small>
              Open positions are marked to market. No fictional liquidation orders or fees are
              added.
            </small>
          </Panel>
          <Panel title="Methodology & reproducibility">
            {data.warnings.map((w, i) => (
              <p className="methodology" key={i}>
                {w}
              </p>
            ))}
            <details>
              <summary>Immutable assumptions and input hashes</summary>
              <pre>
                {JSON.stringify(
                  { profile: r?.profile_snapshot, provenance: r?.provenance },
                  null,
                  2,
                )}
              </pre>
            </details>
          </Panel>
        </>
      )}
    </>
  )
}
