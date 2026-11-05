import type { Condition, Numeric, Result, Run } from '../types'

const sessionFormat = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'America/New_York',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})
export function sessionDate(timestamp: string): string | undefined {
  const clock = new Date(timestamp)
  if (Number.isNaN(clock.getTime())) return undefined
  const parts = sessionFormat.formatToParts(clock)
  return ['year', 'month', 'day'].map((key) => parts.find((p) => p.type === key)?.value).join('-')
}

export function describeNumeric(value: Numeric): string {
  switch (value.type) {
    case 'constant':
      return String(value.value)
    case 'price':
      return value.field || 'close'
    case 'indicator':
      return `${value.name.toUpperCase()}(${value.period}, ${value.field || 'close'})`
    case 'macd':
      return `MACD ${value.component}(${value.fast_period}, ${value.slow_period}, ${value.signal_period})`
    case 'stochastic':
      return `Stochastic %${value.component.toUpperCase()}(${value.period}, ${value.smooth_k}, ${value.smooth_d})`
    case 'external':
      return `${value.series_id} (max age ${value.max_age_days} days)`
    case 'multiply':
      return `(${describeNumeric(value.left)} × ${describeNumeric(value.right)})`
    case 'arithmetic':
      return `(${describeNumeric(value.left)} ${value.op} ${describeNumeric(value.right)})`
    case 'market':
      return `${value.timeframe}: ${describeNumeric(value.expression)}`
    case 'calendar':
      return `Calendar ${value.field.replaceAll('_', ' ')}`
    case 'portfolio':
      return `Portfolio ${value.field.replaceAll('_', ' ')}`
    case 'corporate_action':
      return `Known ${value.kind} ${value.measure} (${value.window}, ${value.days} days)`
    case 'event':
      return `${value.stream_id} ${value.measure}(${value.value_field}, ${value.categories.join(' / ') || 'all declared categories'}, ${value.scope}, ${value.lookback_minutes} minutes, ${value.access}${value.actors.length ? ', ' + value.actors.join(' / ') : ''})`
  }
}

export function describeCondition(rule: Condition): string {
  if (rule.type === 'always') return rule.value ? 'Always true' : 'Always false'
  if (rule.type === 'not') return `NOT (${describeCondition(rule.condition)})`
  if ('conditions' in rule)
    return rule.conditions
      .map((c) => `(${describeCondition(c)})`)
      .join(rule.type === 'all' ? ' AND ' : ' OR ')
  const operators: Record<string, string> = {
    gt: '>',
    lt: '<',
    gte: '≥',
    lte: '≤',
    eq: '=',
    crosses_above: 'crosses above',
    crosses_below: 'crosses below',
  }
  return `${describeNumeric(rule.left)} ${operators[rule.op] || rule.op} ${describeNumeric(rule.right)}`
}

export interface TimelineEvent {
  id: string
  date: string
  timestamp: string
  kind: string
  title: string
  reason: string
  record: Record<string, unknown>
}

export function timelineEvents(result: Result): TimelineEvent[] {
  const executed = new Map(
    (result.orders || [])
      .filter((o) => o.status === 'filled' && o.executed_at)
      .map((o) => [`${o.symbol}:${o.side}:${new Date(o.executed_at!).getTime()}`, o]),
  )
  const events: TimelineEvent[] = (result.ledger || []).flatMap((event, i) => {
    const day = sessionDate(event.timestamp)
    if (!day) return []
    const order = executed.get(
      `${event.symbol}:${event.kind}:${new Date(event.timestamp).getTime()}`,
    )
    const titles: Record<string, string> = {
      buy: `Buy ${event.quantity} ${event.symbol}`,
      sell: `Sell ${event.quantity} ${event.symbol}`,
      contribution: 'Account contribution',
      split: `${event.symbol} split`,
      dividend_entitlement: `${event.symbol} dividend entitlement`,
      dividend_payment: `${event.symbol} dividend payment`,
    }
    return [
      {
        id: `ledger-${i}`,
        date: day,
        timestamp: event.timestamp,
        kind: event.kind,
        title: titles[event.kind] || event.kind,
        reason:
          order?.reason ||
          (event.kind === 'buy' || event.kind === 'sell'
            ? 'Execution recorded; no linked explanatory order retained.'
            : 'Recorded account event; see its original ledger fields.'),
        record: { ...event, ...(order ? { order } : {}) },
      },
    ]
  })
  for (const order of result.orders || []) {
    if (!order.resolved_at || !['rejected', 'cancelled'].includes(order.status)) continue
    const date = sessionDate(order.resolved_at)
    if (date)
      events.push({
        id: `outcome-${order.id}`,
        date,
        timestamp: order.resolved_at,
        kind: order.status,
        title: `${order.side} ${order.symbol} · ${order.status}`,
        reason: order.rejection_reason || order.reason,
        record: { ...order },
      })
  }
  const information = new Map<string, TimelineEvent>()
  for (const signal of result.signals || [])
    for (const evaluation of signal.evaluations || [])
      for (const event of evaluation.events || []) {
        const date = sessionDate(event.available_at)
        const expression = result.expression_catalog?.[evaluation.expression_id]
        const stream = expression?.type === 'event' ? expression.stream_id : 'source'
        const id = `information-${stream}-${event.event_id}-${event.available_at}`
        if (date && !information.has(id))
          information.set(id, {
            id,
            date,
            timestamp: event.available_at,
            kind: 'information',
            title: `Information available · ${event.title}`,
            reason:
              'Saved source evidence used by a recorded rule. Publication and availability can differ; the decision audit shows the actual rule outcome.',
            record: { ...event, stream_id: stream },
          })
      }
  return [...events, ...information.values()].sort(
    (a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime() || a.id.localeCompare(b.id),
  )
}

export function comparisonKey(run: Run): string {
  return [
    run.provenance.dataset_hash,
    run.provenance.profile_hash,
    run.provenance.engine_version,
    run.provenance.strategy_input_hash || '',
  ].join(':')
}

export function marketBenchmarkName(run: Run): string {
  const symbol = String(run.profile_snapshot.benchmark || 'Profile benchmark')
  return symbol === 'SPY' ? 'SPY buy & hold · S&P 500 proxy' : `${symbol} buy & hold`
}
