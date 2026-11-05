import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ContextData } from './ContextData'
import { PeriodPerformance } from '../components/PeriodPerformance'

const mock = vi.hoisted(() => ({ api: vi.fn() }))
vi.mock('../lib/api', () => ({ api: mock.api }))
vi.mock('recharts', () => ({
  ResponsiveContainer: () => <div>Context chart</div>,
  LineChart: () => null,
  CartesianGrid: () => null,
  Line: () => null,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
}))
beforeEach(() => {
  mock.api.mockReset()
})
afterEach(cleanup)
function wrap(component: React.ReactNode) {
  render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
        })
      }
    >
      {component}
    </QueryClientProvider>,
  )
}
it('fetches a selected context source for the full research period and inspects its retained policy', async () => {
  const user = userEvent.setup()
  const snapshot = {
    id: 'c1',
    series_id: 'VIX',
    name: 'Cboe VIX close',
    units: 'index points',
    requested_start: '2018-01-01',
    requested_end: '2025-12-31',
    observation_count: 2012,
    missing_omitted: 0,
    content_hash: 'abc123',
    source: 'Cboe',
    availability_policy: 'Original availability unknown; retrospective context only.',
  }
  let stored = false
  mock.api.mockImplementation(async (path: string) => {
    if (path.endsWith('/catalog'))
      return [{ series_id: 'VIX', name: 'Cboe VIX close', units: 'index points' }]
    if (path.endsWith('/fetch')) {
      stored = true
      return snapshot
    }
    if (path.endsWith('/export')) return { data: { observations: [] } }
    return stored ? [snapshot] : []
  })
  wrap(<ContextData />)
  expect(await screen.findByText('Public Cboe download; no key needed.')).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Fetch context snapshot' }))
  await waitFor(() =>
    expect(mock.api).toHaveBeenCalledWith('/research/context/fetch', 'POST', {
      series_id: 'VIX',
      start: '2018-01-01',
      end: '2025-12-31',
    }),
  )
  expect(await screen.findByText(snapshot.availability_policy)).toBeInTheDocument()
  expect(screen.getByText(/Only explicitly reviewed revisions/)).toBeInTheDocument()
})
it('imports a synthetic timestamped source and requires explicit review before a new eligible revision', async () => {
  const user = userEvent.setup()
  const source = {
    id: 'raw',
    series_id: 'FEAR_GREED_US',
    name: 'Synthetic fixture',
    units: 'index 0–100',
    requested_start: '2020-01-02',
    requested_end: '2020-01-02',
    observation_count: 1,
    missing_omitted: 0,
    content_hash: 'a'.repeat(64),
    source: 'Fixture',
    availability_policy: 'Explicit synthetic publication clocks.',
    research_only: true,
    synthetic: true,
  }
  const eligible = { ...source, id: 'eligible', research_only: false, source_snapshot_id: 'raw' }
  const rows: unknown[] = []
  mock.api.mockImplementation(async (path: string) => {
    if (path.endsWith('/catalog'))
      return [{ series_id: 'FEAR_GREED_US', name: 'US Fear & Greed', manual_only: true }]
    if (path.endsWith('/import-csv')) {
      rows.push(source)
      return source
    }
    if (path.endsWith('/approve')) {
      rows.push(eligible)
      return eligible
    }
    if (path.endsWith('/export')) return { data: { observations: [] } }
    return [...rows]
  })
  wrap(<ContextData />)
  await screen.findByRole('option', { name: 'US Fear & Greed' })
  await user.type(screen.getByLabelText('Source name'), 'SYNTHETIC fixture')
  await user.type(screen.getByLabelText('Source URL'), 'https://example.test/fixture')
  await user.type(
    screen.getByLabelText('Publication availability policy'),
    source.availability_policy,
  )
  const csv = 'observation_date,available_at,value\n2020-01-02,2020-01-02T22:00:00Z,20'
  await user.type(screen.getByLabelText('Observation CSV', { exact: false }), csv)
  await user.click(screen.getByRole('checkbox', { name: /explicitly synthetic/ }))
  await user.click(screen.getByRole('button', { name: 'Import viewing-only snapshot' }))
  await waitFor(() =>
    expect(mock.api).toHaveBeenCalledWith(
      '/research/context/import-csv',
      'POST',
      expect.objectContaining({
        series_id: 'FEAR_GREED_US',
        observations_csv: csv,
        synthetic: true,
      }),
    ),
  )
  const approve = await screen.findByRole('button', { name: 'Create strategy-eligible revision' })
  expect(approve).toBeDisabled()
  expect(mock.api.mock.calls.some(([path]) => path.endsWith('/approve'))).toBe(false)
  await user.type(
    screen.getByLabelText('Source review note'),
    'Reviewed SYNTHETIC fixture publication clocks and coverage.',
  )
  expect(approve).toBeDisabled()
  await user.click(screen.getByRole('checkbox', { name: /reviewed and acknowledge/ }))
  await user.click(approve)
  await waitFor(() =>
    expect(mock.api).toHaveBeenCalledWith('/research/context/raw/approve', 'POST', {
      acknowledge_publication_policy: true,
      review_note: 'Reviewed SYNTHETIC fixture publication clocks and coverage.',
    }),
  )
  expect(await screen.findByText(/Strategy-eligible revision. Source: raw/)).toBeInTheDocument()
})
it('changes continuous period grouping without scheduling or rerunning a simulation', async () => {
  const user = userEvent.setup()
  mock.api.mockResolvedValue({
    periods: [
      {
        period: '2020',
        start: '2020-01-02',
        end: '2020-12-31',
        sessions: 253,
        starting_equity: '11000',
        ending_equity: '12100',
        return: '0.1',
        benchmark_return: '0.05',
        max_drawdown: '-0.2',
        executed_orders: 2,
        commissions: '5.00',
      },
    ],
  })
  wrap(<PeriodPerformance runId="r1" currency="SGD" />)
  expect(await screen.findByText('$12,100.00')).toBeInTheDocument()
  expect(screen.getByText(/One continuous portfolio/)).toBeInTheDocument()
  await user.selectOptions(screen.getByRole('combobox', { name: 'Period grouping' }), 'quarter')
  await waitFor(() =>
    expect(mock.api).toHaveBeenCalledWith('/research/runs/r1/periods?frequency=quarter'),
  )
  expect(mock.api.mock.calls.every((call) => call.length === 1)).toBe(true)
})
