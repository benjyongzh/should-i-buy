import { useMemo, useState } from 'react'
import type { CashBenchmark, Result, Run } from '../types'
import {
  comparisonKey,
  describeCondition,
  describeNumeric,
  marketBenchmarkName,
  sessionDate,
  timelineEvents,
} from '../lib/timeline'
import { EquityChart, type ChartMarker, type EquitySeries } from './EquityChart'
import { Field, money, Panel, percent } from './ui'

export interface TimelineRun {
  run: Run
  name: string
  result: Result
  cash?: CashBenchmark
}

const eventTime = (clock: string) =>
  new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(new Date(clock))

export function PerformanceTimeline({ entries }: { entries: TimelineRun[] }) {
  const [focusId, setFocusId] = useState('')
  const [date, setDate] = useState<string | null>(null)
  const [showCash, setShowCash] = useState(true)
  const [showMarket, setShowMarket] = useState(true)
  const [showDecisions, setShowDecisions] = useState(false)
  const [granularity, setGranularity] = useState('daily')
  const [timestamp, setTimestamp] = useState('')
  const intraday =
    granularity === 'intraday' && entries.every((e) => !!e.result.intraday_equity?.length)
  const curve = (result: Result) => (intraday ? result.intraday_equity! : result.equity)
  const focus = entries.find((e) => e.run.id === focusId) || entries[0]
  const timelines = useMemo(
    () => new Map(entries.map((e) => [e.run.id, timelineEvents(e.result)])),
    [entries],
  )
  const events = focus ? timelines.get(focus.run.id) || [] : []
  const dates = focus?.result.equity.map((r) => r.date) || []
  const selectedDate = date ?? dates[0] ?? ''
  const sessionMarks = focus ? curve(focus.result).filter((r) => r.date === selectedDate) : []
  const selected = intraday
    ? sessionMarks.find((r) => r.timestamp === timestamp) || sessionMarks[0]
    : sessionMarks[0]
  const currency = String(focus?.run.profile_snapshot.account_currency || 'SGD')
  const sameCurrency =
    new Set(entries.map((e) => e.run.profile_snapshot.account_currency)).size <= 1
  const visible = sameCurrency ? entries : focus ? [focus] : []
  const series: EquitySeries[] = visible.map((e) => ({ name: e.name, equity: curve(e.result) }))
  const references = new Set<string>()
  for (const entry of visible) {
    const key = comparisonKey(entry.run)
    if (references.has(key)) continue
    references.add(key)
    const suffix =
      new Set(visible.map((e) => comparisonKey(e.run))).size > 1
        ? ` · ${entry.run.id.slice(0, 8)} assumptions`
        : ''
    const benchmark = intraday
      ? entry.result.benchmark?.intraday_equity
      : entry.result.benchmark?.equity
    const cash = intraday ? entry.cash?.intraday_equity : entry.cash?.equity
    if (showMarket && benchmark)
      series.push({
        name: marketBenchmarkName(entry.run) + suffix,
        equity: benchmark,
        baseline: true,
      })
    if (showCash && Array.isArray(cash))
      series.push({
        name: 'Cash only · zero interest' + suffix,
        equity: cash,
        baseline: true,
      })
  }
  function markAt(entry: TimelineRun, clock: string, date: string): string {
    if (!intraday) return date
    const rows = curve(entry.result),
      target = Date.parse(clock)
    let low = 0,
      high = rows.length
    while (low < high) {
      const mid = (low + high) >>> 1
      if (Date.parse(rows[mid].timestamp!) < target) low = mid + 1
      else high = mid
    }
    return rows[low]?.timestamp || ''
  }
  const markers: ChartMarker[] = visible.flatMap((entry, index) =>
    (timelines.get(entry.run.id) || []).map((e) => ({
      date: markAt(entry, e.timestamp, e.date),
      seriesIndex: index,
      kind: e.kind,
    })),
  )
  if (showDecisions && focus) {
    const index = visible.findIndex((e) => e.run.id === focus.run.id)
    for (const signal of focus.result.signals || []) {
      const day = sessionDate(signal.timestamp)
      if (day && index >= 0)
        markers.push({
          date: markAt(focus, signal.timestamp, day),
          seriesIndex: index,
          kind: 'decision',
        })
    }
  }
  const dayEvents = events.filter((e) => e.date === selectedDate)
  const signals = (focus?.result.signals || []).filter(
    (s) => sessionDate(s.timestamp) === selectedDate,
  )
  const submissions = (focus?.result.orders || []).filter(
    (o) => sessionDate(o.submitted_at) === selectedDate,
  )

  return (
    <Panel title="Account value & decision timeline">
      {!entries.length ? (
        <p>Loading completed results…</p>
      ) : (
        <div className="performance-timeline">
          <div className="timeline-controls">
            {entries.every((e) => !!e.result.intraday_equity?.length) && (
              <Field label="Timeline resolution">
                <select
                  aria-label="Timeline resolution"
                  value={granularity}
                  onChange={(e) => setGranularity(e.target.value)}
                >
                  <option value="daily">Daily closing marks</option>
                  <option value="intraday">Retained intraday valuation clocks</option>
                </select>
              </Field>
            )}
            <label className="checkbox">
              <input
                type="checkbox"
                checked={showMarket}
                onChange={(e) => setShowMarket(e.target.checked)}
              />{' '}
              Buy-and-hold benchmark
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={showCash}
                onChange={(e) => setShowCash(e.target.checked)}
              />{' '}
              Cash-only baseline
            </label>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={showDecisions}
                onChange={(e) => setShowDecisions(e.target.checked)}
              />{' '}
              Mark every decision for the audited run
            </label>
          </div>
          {!sameCurrency && (
            <p className="warning">
              Account currencies differ. The chart shows the audited run and its baselines; choose a
              common currency to overlay strategies.
            </p>
          )}
          <EquityChart
            series={series}
            markers={markers}
            timeKey={intraday ? 'timestamp' : 'date'}
            selectedDate={intraday ? selected?.timestamp : selectedDate}
            onSelectDate={(key) => {
              if (intraday) {
                setDate(sessionDate(key) || null)
                setTimestamp(key)
              } else setDate(key)
            }}
            zoom
          />
          <p className="timeline-key">
            <span>● Buy</span>
            <span>● Sell</span>
            <span>● Contribution / corporate action</span>
            <span>● Decision</span>
          </p>
          <p className="muted">
            Click a chart date or choose a session below. Drag the range handles to zoom. Markers
            use{' '}
            {intraday
              ? 'the first retained valuation at or after the event'
              : 'the session’s closing account value'}
            , rather than the execution price. All audit times below use New York time.
          </p>
          <div className="form-grid">
            {entries.length > 1 && (
              <Field label="Audited strategy run">
                <select
                  aria-label="Audited strategy run"
                  value={focus?.run.id || ''}
                  onChange={(e) => {
                    setFocusId(e.target.value)
                    setDate(null)
                  }}
                >
                  {entries.map((e) => (
                    <option key={e.run.id} value={e.run.id}>
                      {e.name}
                    </option>
                  ))}
                </select>
              </Field>
            )}
            <Field label="Inspect session">
              <input
                type="date"
                min={dates[0]}
                max={dates.at(-1)}
                value={selectedDate}
                onChange={(e) => setDate(e.target.value)}
              />
            </Field>
            {intraday && (
              <Field label="Inspect valuation clock">
                <select
                  aria-label="Inspect valuation clock"
                  value={selected?.timestamp || ''}
                  onChange={(e) => setTimestamp(e.target.value)}
                >
                  {sessionMarks.map((mark) => (
                    <option key={mark.timestamp} value={mark.timestamp}>
                      {eventTime(mark.timestamp!)}
                    </option>
                  ))}
                </select>
              </Field>
            )}
            <div className="actions">
              <button
                type="button"
                className="secondary"
                disabled={dates.indexOf(selectedDate) <= 0}
                onClick={() => setDate(dates[dates.indexOf(selectedDate) - 1])}
              >
                Previous session
              </button>
              <button
                type="button"
                className="secondary"
                disabled={
                  dates.indexOf(selectedDate) < 0 || dates.indexOf(selectedDate) >= dates.length - 1
                }
                onClick={() => setDate(dates[dates.indexOf(selectedDate) + 1])}
              >
                Next session
              </button>
            </div>
          </div>
          {selected ? (
            <>
              <div className="timeline-snapshot" aria-label="Selected session account snapshot">
                <div>
                  <small>Session</small>
                  <strong>{selected.date}</strong>
                  {intraday && selected.timestamp && <small>{eventTime(selected.timestamp)}</small>}
                </div>
                <div>
                  <small>Account value</small>
                  <strong>{money(selected.equity, currency)}</strong>
                </div>
                <div>
                  <small>Available cash</small>
                  <strong>{money(selected.cash, currency)}</strong>
                </div>
                <div>
                  <small>Exposure</small>
                  <strong>{percent(selected.exposure)}</strong>
                </div>
                <div>
                  <small>Drawdown</small>
                  <strong>{percent(selected.drawdown)}</strong>
                </div>
              </div>
              <h3 className="subheading">Executions & account events · {selectedDate}</h3>
              {dayEvents.length ? (
                <div className="timeline-events">
                  {dayEvents.slice(0, 100).map((event) => (
                    <details key={event.id}>
                      <summary>
                        <time>{eventTime(event.timestamp)}</time> · <strong>{event.title}</strong>
                      </summary>
                      <p>{event.reason}</p>
                      <pre>{JSON.stringify(event.record, null, 2)}</pre>
                    </details>
                  ))}
                </div>
              ) : (
                <p>No executions or account events were recorded for this session.</p>
              )}
              <h3 className="subheading">Decisions & order submissions · {selectedDate}</h3>
              {!!focus?.result.universe_decisions?.length && (
                <details>
                  <summary>Historical selection & ranking</summary>
                  <pre>
                    {JSON.stringify(
                      focus.result.universe_decisions
                        .filter((row) => sessionDate(row.timestamp) === selectedDate)
                        .slice(0, 100),
                      null,
                      2,
                    )}
                  </pre>
                </details>
              )}
              {signals.length ? (
                signals.slice(0, 100).map((signal, i) => (
                  <details key={`signal-${i}`}>
                    <summary>
                      {eventTime(signal.timestamp)} · {signal.symbol} · {signal.action} signal
                    </summary>
                    <p>
                      {describeCondition(signal.rule)} — recorded result:{' '}
                      <strong>
                        {signal.condition_result === null
                          ? 'unknown'
                          : String(signal.condition_result)}
                      </strong>
                    </p>
                    {signal.exit_rule && (
                      <p>
                        Exit: {describeCondition(signal.exit_rule)} — recorded result:{' '}
                        {signal.exit_condition_result === null
                          ? 'unknown'
                          : String(signal.exit_condition_result)}
                      </p>
                    )}
                    {signal.reason && <p>{signal.reason}</p>}
                    {signal.sizing_rule && <p>Sizing rule: {signal.sizing_rule}</p>}
                    {signal.selected !== undefined && (
                      <p>Selected for entry: {String(signal.selected)}</p>
                    )}
                    {signal.evaluations?.map((evaluation, j) => (
                      <div key={j}>
                        <strong>
                          {focus?.result.expression_catalog?.[evaluation.expression_id]
                            ? describeNumeric(
                                focus.result.expression_catalog[evaluation.expression_id],
                              )
                            : evaluation.expression_id}
                        </strong>
                        <p>
                          Recorded value: {evaluation.value ?? 'unknown'} ·{' '}
                          {eventTime(evaluation.clock)}
                          {evaluation.completed_bars !== undefined
                            ? ` · ${evaluation.completed_bars} completed bars`
                            : ''}
                        </p>
                        {evaluation.events?.map((event) => (
                          <p key={`${event.event_id}-${event.available_at}`}>
                            <a href={event.source_url} target="_blank" rel="noreferrer">
                              {event.title}
                            </a>{' '}
                            · published {eventTime(event.published_at)} · available{' '}
                            {eventTime(event.available_at)}
                          </p>
                        ))}
                      </div>
                    ))}
                    {signal.external_inputs && (
                      <pre>{JSON.stringify(signal.external_inputs, null, 2)}</pre>
                    )}
                  </details>
                ))
              ) : (
                <p>No decision record exists for this session.</p>
              )}
              {submissions.slice(0, 100).map((order) => (
                <details key={`order-${order.id}`}>
                  <summary>
                    {eventTime(order.submitted_at)} · {order.side} {order.quantity} {order.symbol}{' '}
                    requested · {order.status}
                  </summary>
                  <p>{order.reason}</p>
                  {order.rejection_reason && <p>Recorded outcome: {order.rejection_reason}</p>}
                  <p>
                    {order.executed_at
                      ? `Executed ${eventTime(order.executed_at)}.`
                      : order.resolved_at
                        ? `Resolved ${eventTime(order.resolved_at)}.`
                        : 'No execution timestamp retained. Rejection/cancellation time is not recorded; this entry is placed at submission time.'}
                  </p>
                  <pre>{JSON.stringify(order, null, 2)}</pre>
                </details>
              ))}
              {Math.max(dayEvents.length, signals.length, submissions.length) > 100 && (
                <p>
                  Showing the first 100 records of each kind. The execution audit retains all
                  records.
                </p>
              )}
            </>
          ) : (
            <p>No recorded valuation exists for this date. Select an available trading session.</p>
          )}
          <small>
            Reasons come from saved rules and audit records. Older runs may not retain indicator
            values or a more detailed explanation. Cash is a modeled zero-interest baseline in
            account currency using the same recorded contributions. Buy-and-hold uses the profile
            benchmark, costs and funding policy saved with that run.
          </small>
        </div>
      )}
    </Panel>
  )
}
