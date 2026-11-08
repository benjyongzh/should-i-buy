import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { ResearchJournal } from './ResearchJournal'
const { api, useLab } = vi.hoisted(() => ({ api: vi.fn(), useLab: vi.fn() }))
vi.mock('../lib/api', () => ({ api, useLab }))
afterEach(() => {
  cleanup()
  api.mockReset()
  useLab.mockReset()
})
function fixture() {
  return {
    id: 'study',
    strategy_id: 'strategy',
    parent_id: null,
    created_at: '2026-11-08T00:00:00Z',
    content_hash: 'plan-hash',
    state: 'open',
    payload: {
      question: 'Does smaller sizing reduce drawdown?',
      hypothesis: 'Expect lower drawdown and lower returns.',
      planned_change: 'Halve cash sizing.',
      evaluation_criteria: 'Evaluate all years and all attempts.',
      mode: 'prospective',
      baseline: { id: 'baseline', strategy_version_id: 'v1', metrics: { ending_equity: '12000' } },
      baseline_config: { sizing: 1 },
      controls: { engine_version: '2.0.0' },
      profile_snapshot: { starting_cash: '10000' },
      provenance: { synthetic: false },
      conversation_through_sequence: 3,
      warning: 'Repeated historical evaluation is in-sample research.',
    },
    events: [
      {
        id: 'candidate-event',
        created_at: '2026-11-08T01:00:00Z',
        kind: 'candidate',
        content_hash: 'candidate-hash',
        payload: {
          strategy_version_id: 'v2',
          number: 2,
          config_hash: 'config-hash',
          config: { sizing: 0.5 },
        },
      },
    ],
    attempts: [
      {
        id: 'candidate-run',
        status: 'completed',
        error: null,
        result_hash: 'result-hash',
        metrics: { ending_equity: '11000' },
        metric_deltas: { ending_equity: '-1000', max_drawdown: '-0.1', executed_orders: '0' },
      },
      {
        id: 'failed-run',
        status: 'failed',
        error: 'SYNTHETIC failure retained',
        result_hash: null,
        metrics: null,
        metric_deltas: {},
      },
    ],
  }
}
function mount(path = '/research') {
  useLab.mockReturnValue({
    runs: [
      {
        id: 'baseline',
        status: 'completed',
        strategy_version_id: 'v1',
        profile_snapshot: { start_date: '2018-01-01', end_date: '2025-12-31' },
      },
    ],
    strategies: [{ id: 'strategy', name: 'SYNTHETIC test' }],
    versions: [
      { id: 'v1', strategy_id: 'strategy' },
      { id: 'v2', strategy_id: 'strategy', number: 2 },
    ],
    error: null,
  })
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter initialEntries={[path]}>
        <ResearchJournal />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
it('registers a hypothesis with an explicit retrospective label without publishing a strategy', async () => {
  const user = userEvent.setup()
  const study = fixture()
  api.mockImplementation(async (path: string, method?: string, body?: unknown) => {
    if (path === '/research/studies' && method === 'POST') {
      expect(body).toMatchObject({
        baseline_run_id: 'baseline',
        mode: 'retrospective',
        question: 'Test a lower entry threshold',
        hypothesis: 'It may reduce trades and risk.',
        planned_change: 'Change entry threshold to 25.',
        evaluation_criteria: 'Compare all years and outcomes.',
      })
      return study
    }
    if (path === '/research/studies') return []
    return study
  })
  mount()
  await user.selectOptions(screen.getByLabelText('Completed baseline run'), 'baseline')
  await user.selectOptions(screen.getByLabelText('Registration mode'), 'retrospective')
  for (const [label, value] of [
    ['Research question', 'Test a lower entry threshold'],
    ['Hypothesis', 'It may reduce trades and risk.'],
    ['Planned rule change', 'Change entry threshold to 25.'],
    ['Evaluation criteria', 'Compare all years and outcomes.'],
  ])
    await user.type(screen.getByLabelText(label), value)
  await user.click(screen.getByRole('button', { name: 'Register immutable plan' }))
  await screen.findByText('PROSPECTIVE · open')
  expect(api.mock.calls.filter((c) => c[1] === 'POST')).toHaveLength(1)
})
it('shows losing and failed outcomes and records a mixed immutable conclusion', async () => {
  const user = userEvent.setup()
  const study = fixture()
  api.mockImplementation(async (path: string, method?: string, body?: unknown) => {
    if (path.endsWith('/conclusion')) {
      expect(body).toMatchObject({
        assessment: 'mixed',
        summary: 'Lower return but lower drawdown; failed attempt retained.',
      })
      return { ...study, state: 'concluded' }
    }
    if (path === '/research/studies') return [study]
    return study
  })
  mount('/research?study=study')
  await screen.findByText('SYNTHETIC failure retained')
  expect(screen.getByText('-1000')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: /Compare account timelines/ })).toHaveAttribute(
    'href',
    '/compare?runs=baseline,candidate-run',
  )
  expect(screen.getByRole('link', { name: 'Continue the strategy conversation' })).toHaveAttribute(
    'href',
    '/strategies/strategy',
  )
  await user.selectOptions(screen.getByLabelText('Assessment'), 'mixed')
  await user.type(
    screen.getByLabelText('Conclusion and trade-offs'),
    'Lower return but lower drawdown; failed attempt retained.',
  )
  await user.click(screen.getByRole('button', { name: 'Record immutable conclusion' }))
  await waitFor(() =>
    expect(
      screen.queryByRole('button', { name: 'Schedule candidate attempt' }),
    ).not.toBeInTheDocument(),
  )
})
it('requires synthetic acknowledgement and surfaces scheduling errors', async () => {
  const user = userEvent.setup()
  const study = fixture()
  study.payload.provenance.synthetic = true
  api.mockImplementation(async (path: string, method?: string, body?: unknown) => {
    if (path.endsWith('/schedule')) {
      expect(body).toMatchObject({ acknowledge_synthetic: true })
      throw new Error('Frozen profile changed; restore it first')
    }
    if (path === '/research/studies') return [study]
    return study
  })
  mount('/research?study=study')
  const schedule = await screen.findByRole('button', { name: 'Schedule candidate attempt' })
  expect(schedule).toBeDisabled()
  await user.click(screen.getByRole('checkbox', { name: /explicitly acknowledge synthetic/ }))
  await user.click(schedule)
  await screen.findByText('Frozen profile changed; restore it first')
  await user.click(schedule)
  await waitFor(() => expect(api.mock.calls.filter((c) => c[1] === 'POST')).toHaveLength(2))
  const posted = api.mock.calls.filter((c) => c[1] === 'POST')
  expect(posted[0][2].request_id).toBe(posted[1][2].request_id)
})
