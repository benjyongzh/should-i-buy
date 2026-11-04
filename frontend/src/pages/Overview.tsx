import { ArrowRight, ArrowUpRight, Database, Plus } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useLab, useResults } from '../lib/api'
import { Badge, Empty, money, PageTitle, Panel, percent, Stat } from '../components/ui'
import { EquityChart } from '../components/EquityChart'

export function Overview() {
  const lab = useLab()
  const done = lab.runs.filter((r) => r.status === 'completed').slice(0, 4)
  const results = useResults(done)
  const label = (id: string) => {
    const v = lab.versions.find((v) => v.id === id)
    return `${lab.strategies.find((s) => s.id === v?.strategy_id)?.name || 'Strategy'} · v${v?.number || '?'}`
  }
  return (
    <>
      <PageTitle
        eyebrow="RESEARCH WORKSPACE"
        title="Your next idea starts here."
        description="Build a hypothesis. Test it through time. Understand the trade-offs."
        action={
          <Link className="button" to="/backtests/new">
            <Plus size={16} /> New backtest
          </Link>
        }
      />
      <div className="stats-grid">
        <Stat
          label="Strategies"
          value={lab.strategies.filter((s) => !s.archived).length}
          detail={`${lab.versions.length} immutable published versions`}
        />
        <Stat
          label="Completed backtests"
          value={lab.runs.filter((r) => r.status === 'completed').length}
          detail={`${lab.runs.filter((r) => r.status === 'running' || r.status === 'queued').length} active in the worker queue`}
        />
        <Stat
          label="Market datasets"
          value={lab.datasets.length}
          detail={`${lab.datasets.filter((d) => !d.synthetic).length} historical · ${lab.datasets.filter((d) => d.synthetic).length} synthetic`}
        />
        <Stat
          label="Experiments"
          value={lab.experiments.length}
          detail="Independent portfolios. Shared assumptions."
        />
      </div>
      <div className="overview-grid">
        {done.some((r) => r.provenance.synthetic) && (
          <div className="warning synthetic-overview">
            Displayed curves include SYNTHETIC demonstration data. These results do not represent
            real historical investment performance.
          </div>
        )}
        <Panel
          title="Recent portfolio curves"
          action={
            <Link className="text-link" to="/compare">
              Compare runs <ArrowUpRight size={14} />
            </Link>
          }
        >
          {done.length ? (
            <EquityChart
              series={done.flatMap((r, i) =>
                results[i]?.data
                  ? [{ name: label(r.strategy_version_id), equity: results[i].data!.equity }]
                  : [],
              )}
            />
          ) : (
            <Empty
              title="A clean slate for your research"
              text="Your first completed backtest will appear here. Import a dataset, publish a strategy, and choose your assumptions."
              to="/data"
              label="Set up market data"
            />
          )}
        </Panel>
        <section className="research-card">
          <p className="eyebrow">THE LAB METHOD</p>
          <div className="orbit">
            <span>t →</span>
          </div>
          <h2>One session at a time.</h2>
          <p>
            Decisions use only information available at the simulated clock. Orders wait until the
            next market open.
          </p>
          <div className="research-foot">
            <span className="dot" /> Point-in-time data isolation
          </div>
        </section>
      </div>
      <div className="two-columns">
        <Panel
          title="Recent backtests"
          action={
            <Link className="text-link" to="/backtests">
              View all <ArrowRight size={14} />
            </Link>
          }
        >
          {lab.runs.length ? (
            <div className="list">
              {lab.runs.slice(0, 5).map((r) => (
                <Link to={`/backtests/${r.id}`} className="list-row" key={r.id}>
                  <div>
                    <strong>{label(r.strategy_version_id)}</strong>
                    <small>
                      {r.profile_snapshot.start_date} — {r.profile_snapshot.end_date}
                    </small>
                  </div>
                  <Badge value={r.status} />
                </Link>
              ))}
            </div>
          ) : (
            <p className="panel-empty">No runs yet. Results will come from your simulations.</p>
          )}
        </Panel>
        <Panel title="Research checklist">
          <Link className="check-row" to="/data">
            <span className={lab.datasets.length ? 'step complete' : 'step'}>01</span>
            <div>
              <strong>Choose your evidence</strong>
              <small>Import raw candles and historically available FX.</small>
            </div>
            <Database size={18} />
          </Link>
          <Link className="check-row" to="/strategies/new">
            <span className={lab.versions.length ? 'step complete' : 'step'}>02</span>
            <div>
              <strong>Define a repeatable strategy</strong>
              <small>Configure rules and publish an immutable version.</small>
            </div>
            <ArrowUpRight size={18} />
          </Link>
          <Link className="check-row" to="/profiles">
            <span className={lab.profiles.length ? 'step complete' : 'step'}>03</span>
            <div>
              <strong>Keep the comparison fair</strong>
              <small>Use shared capital, costs, dates, and market data.</small>
            </div>
            <ArrowUpRight size={18} />
          </Link>
        </Panel>
      </div>
      {results.some((q) => q.data) && (
        <Panel title="Latest completed results">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Strategy</th>
                  <th>Ending equity</th>
                  <th>Net return</th>
                  <th>Max drawdown</th>
                  <th>Data</th>
                </tr>
              </thead>
              <tbody>
                {done.map((r, i) => (
                  <tr key={r.id}>
                    <td>
                      <Link to={`/backtests/${r.id}`}>{label(r.strategy_version_id)}</Link>
                    </td>
                    <td>
                      {money(
                        results[i]?.data?.metrics.ending_equity,
                        String(r.profile_snapshot.account_currency),
                      )}
                    </td>
                    <td>{percent(results[i]?.data?.metrics.total_return)}</td>
                    <td>{percent(results[i]?.data?.metrics.max_drawdown)}</td>
                    <td>
                      <Badge value={r.provenance.synthetic ? 'synthetic' : 'historical'} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
      {lab.runs.some((r) => r.status === 'failed') && (
        <Panel title="Runs requiring attention">
          {lab.runs
            .filter((r) => r.status === 'failed')
            .slice(0, 3)
            .map((r) => (
              <Link className="list-row" to={`/backtests/${r.id}`} key={r.id}>
                <span>
                  {label(r.strategy_version_id)}
                  <small>{r.error}</small>
                </span>
                <Badge value="failed" />
              </Link>
            ))}
        </Panel>
      )}
    </>
  )
}
