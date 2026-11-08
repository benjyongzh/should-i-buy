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
vi.mock('../lib/api', () => ({
  api: mock.api,
  useLab: () => mock.lab,
  useCashBenchmarks: () => [],
}))
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
it('reviews an LLM interpretation before draft acceptance and blocks unsupported proposals', async () => {
  const user = userEvent.setup()
  let blocked = false
  const saved = {
    id: 's1',
    name: 'Saved assistant draft',
    description: '',
    draft: defaultStrategy,
    draft_revision: 1,
  }
  mock.api.mockImplementation(async (path: string) => {
    if (path === '/llm/plan-strategy')
      return {
        id: 'proposal',
        config: blocked ? {} : defaultStrategy,
        metadata_json: {
          model: 'fixture',
          prompt_version: 'v3',
          blocked,
          interpretation: 'Buy only after one hour from exchange open',
          data_requirements: ['Reviewed intraday prices'],
          unsupported_requests: blocked ? ['Live execution is unavailable'] : [],
        },
      }
    if (path.endsWith('/versions')) return []
    return saved
  })
  wrap(
    <Routes>
      <Route path="/strategies/:id" element={<StrategyEditor />} />
    </Routes>,
    '/strategies/s1',
  )
  await screen.findByDisplayValue(saved.name)
  await user.click(screen.getByText('Single-request compatibility assistant'))
  await user.type(screen.getByLabelText('Strategy assistant prompt'), 'Buy an hour after opening')
  await user.click(screen.getByRole('button', { name: 'Propose changes' }))
  await screen.findByText('Reviewed intraday prices')
  const accept = screen.getByRole('button', { name: 'Accept into draft' })
  expect(accept).toBeDisabled()
  await user.click(screen.getByLabelText(/I reviewed the interpretation/))
  await user.click(accept)
  await waitFor(() =>
    expect(mock.api).toHaveBeenCalledWith('/llm/proposals/proposal/accept', 'POST'),
  )
  expect(mock.api.mock.calls.some((call) => String(call[0]).endsWith('/publish'))).toBe(false)
  blocked = true
  await user.click(screen.getByRole('button', { name: 'Propose changes' }))
  await screen.findByText('Live execution is unavailable')
  await user.click(screen.getByLabelText(/I reviewed the interpretation/))
  expect(screen.getByRole('button', { name: 'Accept into draft' })).toBeDisabled()
})
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
  const contribution = screen.getByLabelText('Monthly contribution (account currency)')
  await user.clear(contribution)
  await user.type(contribution, '500')
  await user.click(screen.getByRole('button', { name: 'Save profile' }))
  await waitFor(() =>
    expect(mock.api).toHaveBeenCalledWith(
      '/backtest-profiles',
      'POST',
      expect.objectContaining({
        config: expect.objectContaining({
          starting_capital: '12000',
          fixed_fee: '2.50',
          monthly_contribution: '500',
        }),
      }),
    ),
  )
})

it('saves DCA timing, cash sizing and partial exits as an unpublished draft', async () => {
  const user = userEvent.setup()
  mock.api.mockResolvedValue({
    id: 's1',
    name: 'Monthly DCA',
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
  await user.type(screen.getByRole('textbox', { name: 'Strategy name' }), 'Monthly DCA')
  await user.selectOptions(screen.getByLabelText('Sizing method'), 'cash_percent')
  await user.selectOptions(screen.getByLabelText('Entry decision schedule'), 'monthly')
  await user.selectOptions(screen.getByLabelText('Allow additions to held positions'), 'true')
  const fraction = screen.getByLabelText('Exit fraction')
  await user.clear(fraction)
  await user.type(fraction, '0.25')
  await user.click(screen.getByRole('button', { name: 'Save draft' }))
  await waitFor(() =>
    expect(mock.api).toHaveBeenCalledWith(
      '/strategies',
      'POST',
      expect.objectContaining({
        config: expect.objectContaining({
          sizing: { mode: 'cash_percent', value: 0.1 },
          trading: {
            entry_schedule: 'monthly',
            exit_schedule: 'daily',
            allow_additions: true,
            exit_fraction: '0.25',
          },
        }),
      }),
    ),
  )
  expect(mock.api.mock.calls.some(([path]) => String(path).endsWith('/publish'))).toBe(false)
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
it('pins only reviewed external revisions and acknowledges synthetic inputs even with historical prices', async () => {
  const user = userEvent.setup()
  mock.lab.strategies = [{ id: 's1', name: 'External fixture', archived: false }]
  mock.lab.versions = [{ id: 'v1', strategy_id: 's1', number: 1, config_hash: 'abc' }]
  mock.lab.profiles = [profile]
  mock.lab.datasets = [
    {
      id: 'd1',
      name: 'Price fixture',
      synthetic: false,
      content_hash: '12345678',
      metadata_json: { fx_observations: 1, coverage: {} },
    },
  ]
  mock.api.mockImplementation(async (path: string) =>
    path === '/research/context'
      ? [
          { id: 'raw', series_id: 'UNREVIEWED', research_only: true, content_hash: 'a'.repeat(64) },
          {
            id: 'approved',
            series_id: 'FEAR_GREED_US',
            research_only: false,
            synthetic: true,
            content_hash: 'b'.repeat(64),
          },
        ]
      : [{ id: 'r1', experiment_id: 'e1' }],
  )
  wrap(<NewBacktest />)
  await user.click(screen.getByRole('checkbox', { name: /Version 1/ }))
  await user.selectOptions(screen.getByLabelText('Backtest profile'), 'p1')
  await user.selectOptions(screen.getByLabelText('Dataset revision'), 'd1')
  expect(screen.queryByText('UNREVIEWED', { exact: false })).not.toBeInTheDocument()
  await user.click(await screen.findByRole('checkbox', { name: /FEAR_GREED_US/ }))
  expect(screen.getByRole('button', { name: 'Queue backtests' })).toBeDisabled()
  await user.click(screen.getByRole('checkbox', { name: /I understand/ }))
  await user.click(screen.getByRole('button', { name: 'Queue backtests' }))
  await waitFor(() =>
    expect(mock.api).toHaveBeenCalledWith(
      '/backtests',
      'POST',
      expect.objectContaining({ context_snapshot_ids: ['approved'], acknowledge_synthetic: true }),
    ),
  )
})

it('imports the selected Alpaca feed and explicit dividend attestation', async () => {
  const user = userEvent.setup()
  mock.api.mockResolvedValue({ name: 'Mock import', content_hash: 'abc123' })
  wrap(<MarketData />)
  expect(screen.getByLabelText('Alpaca feed')).toHaveValue('sip')
  await user.selectOptions(screen.getByLabelText('Alpaca feed'), 'iex')
  await user.click(
    screen.getAllByRole('checkbox', { name: 'Source attests complete dividend history' })[1],
  )
  await user.click(screen.getByRole('button', { name: 'Fetch historical bars' }))
  await waitFor(() =>
    expect(mock.api).toHaveBeenCalledWith(
      '/market-data/alpaca',
      'POST',
      expect.objectContaining({
        feed: 'iex',
        symbols: ['SPY'],
        start: '2018-01-01',
        end: '2022-12-31',
        dividends_complete: true,
        corporate_actions_reviewed: false,
      }),
    ),
  )
})
