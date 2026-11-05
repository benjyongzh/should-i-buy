import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import type { CashBenchmark, Equity, Result, Run } from '../types'
import { describeCondition, sessionDate, timelineEvents } from '../lib/timeline'
import { PerformanceTimeline, type TimelineRun } from './PerformanceTimeline'
import type { ChartMarker, EquitySeries } from './EquityChart'

vi.mock('./EquityChart', () => ({
  EquityChart: ({
    series,
    markers,
    onSelectDate,
  }: {
    series: EquitySeries[]
    markers: ChartMarker[]
    onSelectDate: (date: string) => void
  }) => (
    <div>
      <output data-testid="chart-series">{JSON.stringify(series.map((s) => s.name))}</output>
      <output data-testid="chart-markers">{JSON.stringify(markers)}</output>
      <button onClick={() => onSelectDate('2019-01-03')}>Inspect chart January 3</button>
    </div>
  ),
}))
afterEach(cleanup)
it('offers retained intraday marks and places source evidence at availability rather than publication', async () => {
  const item = entry()
  item.result.intraday_equity = [
    { ...item.result.equity[0], timestamp: '2019-01-02T14:35:00Z' },
    { ...item.result.equity[0], equity: '10525', timestamp: '2019-01-02T15:00:00Z' },
  ]
  item.result.expression_catalog = {
    event: {
      type: 'event',
      stream_id: 'COMPANY_NEWS',
      categories: ['news'],
      scope: 'symbol',
      measure: 'count',
      lookback_minutes: 1440,
      access: 'public_only',
      actors: [],
      value_field: 'score',
    },
  }
  item.result.signals[0].timestamp = '2019-01-02T15:00:00Z'
  item.result.signals[0].evaluations = [
    {
      expression_id: 'event',
      clock: '2019-01-02T15:00:00Z',
      value: '1',
      events: [
        {
          event_id: 'article',
          published_at: '2019-01-02T13:00:00Z',
          available_at: '2019-01-02T14:50:00Z',
          category: 'news',
          title: 'SYNTHETIC original news',
          source_url: 'https://example.invalid/news',
        },
      ],
    },
  ]
  const user = userEvent.setup()
  render(<PerformanceTimeline entries={[item]} />)
  await user.selectOptions(screen.getByLabelText('Timeline resolution'), 'intraday')
  await user.selectOptions(screen.getByLabelText('Inspect valuation clock'), '2019-01-02T15:00:00Z')
  expect(screen.getByLabelText('Selected session account snapshot')).toHaveTextContent('10,525')
  expect(screen.getByTestId('chart-markers')).toHaveTextContent('2019-01-02T15:00:00Z')
  const source = timelineEvents(item.result).find((e) => e.kind === 'information')!
  expect(source.timestamp).toBe('2019-01-02T14:50:00Z')
  expect(screen.getByRole('link', { name: 'SYNTHETIC original news' })).toHaveAttribute(
    'href',
    'https://example.invalid/news',
  )
})

function entry(id = 'r1', name = 'Momentum · v1'): TimelineRun {
  const equity: Equity[] = ['2019-01-02', '2019-01-03'].map((date, i) => ({
    date,
    equity: i ? '10600' : '10500',
    cash: i ? '5500' : '10500',
    drawdown: 0,
    exposure: i ? '.48' : '0',
    unrealized_pnl: i ? '100' : '0',
    realized_pnl: '0',
  }))
  const run: Run = {
    id,
    strategy_version_id: 'v1',
    profile_id: 'p1',
    dataset_id: 'd1',
    experiment_id: 'e1',
    progress: 100,
    error: null,
    created_at: '2019-01-01T00:00:00Z',
    started_at: null,
    completed_at: null,
    status: 'completed',
    profile_snapshot: { starting_capital: '10000', account_currency: 'SGD', benchmark: 'SPY' },
    provenance: {
      dataset_hash: 'data',
      profile_hash: 'profile',
      engine_version: '1.4.0',
      strategy_hash: 'strategy',
      synthetic: true,
    },
  }
  const result: Result = {
    metrics: {},
    equity,
    benchmark: { metrics: {}, equity },
    trades: [],
    positions: {},
    warnings: ['SYNTHETIC fixture'],
    signals: [
      {
        timestamp: '2019-01-03T01:30:00Z',
        symbol: 'SPY',
        action: 'buy',
        condition_result: true,
        rule: { type: 'always', value: true },
      },
    ],
    orders: [
      {
        id: 1,
        symbol: 'SPY',
        side: 'buy',
        type: 'market',
        quantity: '10',
        submitted_at: '2019-01-03T01:30:00Z',
        executed_at: '2019-01-03T14:30:00Z',
        status: 'filled',
        execution_price: '100',
        fees: '2.50',
        reason: 'scheduled entry/rebalance',
        rejection_reason: null,
      },
      {
        id: 2,
        symbol: 'SPY',
        side: 'buy',
        type: 'market',
        quantity: '100',
        submitted_at: '2019-01-04T01:30:00Z',
        executed_at: null,
        status: 'rejected',
        execution_price: null,
        fees: '0',
        reason: 'declarative entry',
        rejection_reason: 'insufficient cash after costs',
      },
    ],
    ledger: [
      {
        kind: 'contribution',
        timestamp: '2019-01-02T14:30:00Z',
        cash_delta: '500',
        cash_after: '10500',
      },
      {
        kind: 'buy',
        timestamp: '2019-01-03T14:30:00+00:00',
        symbol: 'SPY',
        quantity: '10',
        cash_after: '5500',
      },
    ],
  }
  const cash: CashBenchmark = {
    run_id: id,
    name: 'Cash only',
    currency: 'SGD',
    synthetic: true,
    assumptions: 'Modeled zero interest',
    equity,
    metrics: { total_return: 0 },
  }
  return { run, name, result, cash }
}

it('keeps evening decisions on their market session and executions on their actual day', () => {
  expect(sessionDate('2019-01-03T01:30:00Z')).toBe('2019-01-02')
  expect(sessionDate('2019-07-04T00:30:00Z')).toBe('2019-07-03')
  expect(sessionDate('bad timestamp')).toBeUndefined()
  const e = entry()
  const before = structuredClone(e.result)
  const fills = timelineEvents(e.result)
  expect(fills.find((f) => f.kind === 'buy')).toMatchObject({
    date: '2019-01-03',
    reason: 'scheduled entry/rebalance',
  })
  expect(fills.some((f) => f.kind === 'rejected')).toBe(false)
  expect(e.result).toEqual(before)
  expect(
    describeCondition({
      type: 'compare',
      op: 'crosses_above',
      left: { type: 'indicator', name: 'sma', period: 20 },
      right: { type: 'indicator', name: 'sma', period: 50 },
    }),
  ).toBe('SMA(20, close) crosses above SMA(50, close)')
})

it('links chart dates to snapshots, fills and recorded rejection reasons without inventing rejection times', async () => {
  const user = userEvent.setup()
  render(<PerformanceTimeline entries={[entry()]} />)
  expect(screen.getByText('Always true — recorded result:', { exact: false })).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Inspect chart January 3' }))
  expect(
    within(screen.getByLabelText('Selected session account snapshot')).getByText('$10,600.00'),
  ).toBeInTheDocument()
  expect(
    within(screen.getByLabelText('Selected session account snapshot')).getByText('48.00%'),
  ).toBeInTheDocument()
  await user.click(screen.getByText('Buy 10 SPY'))
  expect(screen.getByText('scheduled entry/rebalance')).toBeVisible()
  expect(screen.getByText('Recorded outcome: insufficient cash after costs')).toBeInTheDocument()
  expect(screen.getByText(/Rejection\/cancellation time is not recorded/)).toBeInTheDocument()
  expect(
    screen.queryByText('Always true — recorded result:', { exact: false }),
  ).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Previous session' }))
  expect(screen.getByText('Account contribution')).toBeInTheDocument()
})

it('overlays versions and different strategies with deduplicated cash and SPY references', async () => {
  const user = userEvent.setup()
  render(
    <PerformanceTimeline
      entries={[entry(), entry('r2', 'Momentum · v2'), entry('r3', 'RSI · v1')]}
    />,
  )
  let series = JSON.parse(screen.getByTestId('chart-series').textContent!)
  expect(series).toEqual([
    'Momentum · v1',
    'Momentum · v2',
    'RSI · v1',
    'SPY buy & hold · S&P 500 proxy',
    'Cash only · zero interest',
  ])
  await user.click(screen.getByRole('checkbox', { name: 'Cash-only baseline' }))
  series = JSON.parse(screen.getByTestId('chart-series').textContent!)
  expect(series).not.toContain('Cash only · zero interest')
  await user.selectOptions(screen.getByLabelText('Audited strategy run'), 'r2')
  await user.click(
    screen.getByRole('checkbox', { name: 'Mark every decision for the audited run' }),
  )
  const markers = JSON.parse(screen.getByTestId('chart-markers').textContent!)
  expect(markers).toContainEqual({ date: '2019-01-02', seriesIndex: 1, kind: 'decision' })
})

it('keeps different assumptions separate and prevents overlaying unlike account currencies', () => {
  const a = entry(),
    b = entry('r2', 'Other')
  b.run = {
    ...b.run,
    profile_snapshot: { ...b.run.profile_snapshot, account_currency: 'USD' },
    provenance: { ...b.run.provenance, profile_hash: 'other' },
  }
  render(<PerformanceTimeline entries={[a, b]} />)
  expect(screen.getByText(/Account currencies differ/)).toBeInTheDocument()
  expect(JSON.parse(screen.getByTestId('chart-series').textContent!)).toEqual([
    'Momentum · v1',
    'SPY buy & hold · S&P 500 proxy',
    'Cash only · zero interest',
  ])
})

it('does not interpolate a valuation for a date missing from the stored curve', async () => {
  const user = userEvent.setup()
  render(<PerformanceTimeline entries={[entry()]} />)
  await user.clear(screen.getByLabelText('Inspect session'))
  await user.type(screen.getByLabelText('Inspect session'), '2019-01-05')
  expect(screen.getByText(/No recorded valuation exists for this date/)).toBeInTheDocument()
})
