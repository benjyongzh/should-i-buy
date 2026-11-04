import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import type { ReactNode } from 'react'
import { StrategyEditor } from './StrategyEditor'
import { Profiles } from './Profiles'
import { NewBacktest } from './Backtests'
import { MarketData } from './MarketData'
import { RunDetails } from './RunDetails'
import { RuleEditor } from '../components/RuleEditor'
import { useState } from 'react'
import { defaultStrategy } from '../types'
import type { Condition } from '../types'
const mock = vi.hoisted(() => ({
  api: vi.fn(),
  lab: {
    strategies: [] as unknown[],
    versions: [] as unknown[],
    profiles: [] as unknown[],
    datasets: [] as unknown[],
    runs: [],
    experiments: [],
    loading: false,
    error: null,
  },
}))
vi.mock('../lib/api', () => ({ api: mock.api, useLab: () => mock.lab }))
vi.mock('../components/EquityChart', () => ({
  EquityChart: () => <div aria-label="Equity chart fixture" />,
}))

const profile = {
  id: 'p1',
  name: 'Standard SGD Portfolio',
  config: {
    starting_capital: '10000',
    account_currency: 'SGD',
    fixed_fee: '2.50',
    slippage: '0.0005',
    start_date: '2019-01-01',
    end_date: '2022-12-31',
    symbols: ['SPY'],
    benchmark: 'SPY',
    research_label: 'in_sample',
    fractional_shares: false,
    max_orders_per_day: 10,
    max_exposure: '1',
    min_notional: '1',
    min_holding_sessions: 0,
    max_positions: 5,
    max_fx_age_days: 7,
    risk_free_rate: '0',
    commission_pct: '0',
    spread: '0',
    fx_markup: '0',
  },
}
function wrap(children: ReactNode, path = '/') {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
        })
      }
    >
      <MemoryRouter initialEntries={[path]}>{children}</MemoryRouter>
    </QueryClientProvider>,
  )
}
beforeEach(() => {
  mock.api.mockReset()
  Object.assign(mock.lab, { strategies: [], versions: [], profiles: [], datasets: [] })
  mock.api.mockResolvedValue([])
})
afterEach(cleanup)
it('displays persisted results and filters execution records', async () => {
  const user = userEvent.setup()
  const result = {
    metrics: {
      starting_equity: '10000',
      ending_equity: '10500',
      total_return: 0.05,
      max_drawdown: -0.02,
      sharpe_ratio: 1.2,
    },
    equity: [],
    benchmark: { equity: [] },
    trades: [],
    signals: [],
    ledger: [],
    positions: {},
    warnings: ['SYNTHETIC test fixture'],
    orders: [
      {
        id: 1,
        symbol: 'SPY',
        side: 'buy',
        type: 'market',
        quantity: '5',
        submitted_at: '2020-01-02T21:30:00Z',
        executed_at: '2020-01-03T14:30:00Z',
        status: 'filled',
        execution_price: '100',
        fees: '2.50',
        reason: 'declarative entry',
      },
      {
        id: 2,
        symbol: 'SPY',
        side: 'buy',
        type: 'market',
        quantity: '500',
        submitted_at: '2020-01-03T21:30:00Z',
        executed_at: null,
        status: 'rejected',
        execution_price: null,
        fees: '0',
        reason: 'entry',
        rejection_reason: 'insufficient cash',
      },
    ],
  }
  mock.api.mockImplementation(async (path: string) =>
    path.endsWith('/results')
      ? result
      : {
          id: 'r1',
          status: 'completed',
          profile_snapshot: profile.config,
          provenance: { synthetic: true },
        },
  )
  wrap(
    <Routes>
      <Route path="/backtests/:id" element={<RunDetails />} />
    </Routes>,
    '/backtests/r1',
  )
  expect(await screen.findByText('$10,500.00')).toBeInTheDocument()
  expect(screen.getByText('declarative entry')).toBeInTheDocument()
  await user.type(screen.getByRole('textbox', { name: 'Filter orders' }), 'rejected')
  expect(screen.queryByText('declarative entry')).not.toBeInTheDocument()
  expect(screen.getByText('insufficient cash')).toBeInTheDocument()
})
describe('Strategy authoring', () => {
  it('creates a draft with the declarative definition', async () => {
    const user = userEvent.setup()
    mock.api.mockResolvedValue({
      id: 's1',
      name: 'My strategy',
      description: '',
      draft: defaultStrategy,
      draft_revision: 1,
    })
    wrap(
      <Routes>
        <Route path="/strategies/:id" element={<StrategyEditor />} />
      </Routes>,
      '/strategies/new',
    )
    await user.type(screen.getByRole('textbox', { name: 'Strategy name' }), 'My strategy')
    await user.click(screen.getByRole('button', { name: 'Save draft' }))
    await waitFor(() =>
      expect(mock.api).toHaveBeenCalledWith(
        '/strategies',
        'POST',
        expect.objectContaining({ name: 'My strategy', config: defaultStrategy }),
      ),
    )
  })
  it('rejects a missing strategy name without saving', async () => {
    const user = userEvent.setup()
    wrap(
      <Routes>
        <Route path="/strategies/:id" element={<StrategyEditor />} />
      </Routes>,
      '/strategies/new',
    )
    await user.click(screen.getByRole('button', { name: 'Save draft' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Give the strategy a name')
    expect(mock.api).not.toHaveBeenCalled()
  })
  it('shows backend validation errors for JSON edits', async () => {
    const user = userEvent.setup()
    mock.api.mockRejectedValue(new Error('entry.op: unsupported operator'))
    wrap(
      <Routes>
        <Route path="/strategies/:id" element={<StrategyEditor />} />
      </Routes>,
      '/strategies/new',
    )
    await user.click(screen.getByRole('button', { name: 'JSON' }))
    await user.click(screen.getByRole('button', { name: 'Validate' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('unsupported operator')
  })
  it('publishes a saved immutable definition separately', async () => {
    const user = userEvent.setup()
    mock.api.mockImplementation(async (path: string) =>
      path.endsWith('/versions')
        ? []
        : path.includes('/publish')
          ? { id: 'v1' }
          : { id: 's1', name: 'Saved', description: '', draft: defaultStrategy, draft_revision: 1 },
    )
    wrap(
      <Routes>
        <Route path="/strategies/:id" element={<StrategyEditor />} />
      </Routes>,
      '/strategies/s1',
    )
    await screen.findByDisplayValue('Saved')
    await user.click(screen.getByRole('button', { name: 'Publish new version' }))
    await waitFor(() =>
      expect(mock.api).toHaveBeenCalledWith('/strategies/s1/publish', 'POST', {
        expected_revision: 1,
        change_summary: '',
      }),
    )
  })
  it('edits composable rule trees through controls', async () => {
    const user = userEvent.setup()
    function Harness() {
      const [c, setC] = useState<Condition>({ type: 'always', value: true })
      return (
        <>
          <RuleEditor value={c} onChange={setC} />
          <output>{JSON.stringify(c)}</output>
        </>
      )
    }
    wrap(<Harness />)
    await user.selectOptions(screen.getByLabelText('Condition'), 'all')
    await user.click(screen.getByRole('button', { name: '+ Add condition' }))
    expect(screen.getAllByLabelText('Comparison operator')).toHaveLength(2)
    await user.selectOptions(screen.getAllByLabelText('Comparison operator')[0], 'crosses_above')
    expect(screen.getByRole('status')).toHaveTextContent('crosses_above')
  })
})
it('saves editable shared financial assumptions', async () => {
  const user = userEvent.setup()
  mock.api.mockImplementation(async (path: string) =>
    path.endsWith('/defaults') ? profile : { ...profile, id: 'p2' },
  )
  wrap(<Profiles />)
  const capital = await screen.findByDisplayValue('10000')
  await user.clear(capital)
  await user.type(capital, '12000')
  await user.click(screen.getByRole('button', { name: 'Save profile' }))
  await waitFor(() =>
    expect(mock.api).toHaveBeenCalledWith(
      '/backtest-profiles',
      'POST',
      expect.objectContaining({
        config: expect.objectContaining({ starting_capital: '12000', fixed_fee: '2.50' }),
      }),
    ),
  )
})
it('requires explicit synthetic acknowledgement before scheduling', async () => {
  const user = userEvent.setup()
  mock.lab.strategies = [{ id: 's1', name: 'Buy hold', archived: false }]
  mock.lab.versions = [{ id: 'v1', strategy_id: 's1', number: 1, config_hash: 'abc' }]
  mock.lab.profiles = [profile]
  mock.lab.datasets = [
    {
      id: 'd1',
      name: 'SYNTHETIC',
      synthetic: true,
      content_hash: '12345678',
      metadata_json: {
        fx_observations: 100,
        coverage: { SPY: { start: '2019-01-01', end: '2022-12-31', missing_sessions: [] } },
      },
    },
  ]
  mock.api.mockResolvedValue([{ id: 'r1', experiment_id: 'e1' }])
  wrap(<NewBacktest />)
  await user.click(screen.getByRole('checkbox', { name: /Version 1/ }))
  await user.selectOptions(screen.getByLabelText('Backtest profile'), 'p1')
  await user.selectOptions(screen.getByLabelText('Dataset revision'), 'd1')
  expect(screen.getByRole('button', { name: 'Queue backtests' })).toBeDisabled()
  await user.click(screen.getByRole('checkbox', { name: /I understand/ }))
  await user.click(screen.getByRole('button', { name: 'Queue backtests' }))
  await waitFor(() =>
    expect(mock.api).toHaveBeenCalledWith(
      '/backtests',
      'POST',
      expect.objectContaining({
        strategy_version_ids: ['v1'],
        profile_id: 'p1',
        dataset_id: 'd1',
        acknowledge_synthetic: true,
      }),
    ),
  )
})
it('loads a labeled demonstration only on explicit request', async () => {
  const user = userEvent.setup()
  wrap(<MarketData />)
  expect(mock.api).not.toHaveBeenCalled()
  await user.click(screen.getByRole('button', { name: 'Load labeled synthetic dataset' }))
  await waitFor(() => expect(mock.api).toHaveBeenCalledWith('/market-data/demo', 'POST'))
})
