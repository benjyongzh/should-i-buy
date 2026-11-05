import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import { ErrorBox, money, Panel, percent } from './ui'

interface Period {
  period: string
  start: string
  end: string
  sessions: number
  starting_equity: string
  ending_equity: string
  return: string | null
  benchmark_return: string | null
  max_drawdown: string
  executed_orders: number
  commissions: string
  contributions?: string
  pnl: string
}
export function PeriodPerformance({ runId, currency }: { runId: string; currency: string }) {
  const [frequency, setFrequency] = useState('year')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const report = useQuery({
    queryKey: ['periods', runId, frequency, start, end],
    queryFn: () =>
      api<{ periods: Period[] }>(
        `/research/runs/${runId}/periods?${new URLSearchParams({ frequency, ...(start ? { start } : {}), ...(end ? { end } : {}) })}`,
      ),
    staleTime: Infinity,
  })
  return (
    <Panel
      title="Performance through time"
      action={
        <select
          aria-label="Period grouping"
          value={frequency}
          onChange={(e) => setFrequency(e.target.value)}
        >
          <option value="year">Year</option>
          <option value="quarter">Quarter</option>
          <option value="month">Month</option>
        </select>
      }
    >
      <p>
        One continuous portfolio. Each period carries forward the preceding equity mark, positions
        and cash. Returns and drawdown exclude deposits; P&L subtracts each period's contributions.
        Drawdown is measured within each period.
      </p>
      <div className="form-grid">
        <label className="field">
          <span>Analyze from (optional)</span>
          <input
            aria-label="Analyze from"
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
          />
        </label>
        <label className="field">
          <span>Analyze through (optional)</span>
          <input
            aria-label="Analyze through"
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
          />
        </label>
      </div>
      <ErrorBox error={report.error} />
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Period</th>
              <th>Start equity</th>
              <th>End equity</th>
              <th>Contributions</th>
              <th>Investment P&L</th>
              <th>Return</th>
              <th>Benchmark</th>
              <th>Drawdown</th>
              <th>Orders</th>
              <th>Fees</th>
            </tr>
          </thead>
          <tbody>
            {(report.data?.periods || []).map((p) => (
              <tr key={p.period}>
                <td>
                  {p.period}
                  <small>
                    {p.start} → {p.end} · {p.sessions} sessions
                  </small>
                </td>
                <td>{money(p.starting_equity, currency)}</td>
                <td>{money(p.ending_equity, currency)}</td>
                <td>{money(p.contributions ?? '0', currency)}</td>
                <td>{money(p.pnl, currency)}</td>
                <td>{percent(p.return)}</td>
                <td>{percent(p.benchmark_return)}</td>
                <td>{percent(p.max_drawdown)}</td>
                <td>{p.executed_orders}</td>
                <td>{money(p.commissions, currency)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {report.isPending && <p>Loading period analysis…</p>}
      <small>
        Repeated full-history refinement is development research. Keep each published version and
        its change summary so improvements and regressions remain visible.
      </small>
    </Panel>
  )
}
