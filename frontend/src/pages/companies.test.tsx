import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { Companies } from './Companies'

const { api } = vi.hoisted(() => ({ api: vi.fn() }))
vi.mock('../lib/api', () => ({ api }))
afterEach(() => {
  cleanup()
  api.mockReset()
})
const job = {
  id: 'intake',
  status: 'awaiting_review',
  error: null,
  cancel_requested: false,
  request_payload: {
    symbol: 'NVDA',
    benchmark: 'SPY',
    start: '2024-04-01',
    end: '2024-07-31',
    warmup_days: 90,
  },
}
function detail() {
  return {
    ...job,
    artifacts: [],
    packages: [] as unknown[],
    report: {
      content_hash: 'a'.repeat(64),
      payload: {
        identity: { name: 'SYNTHETIC test issuer', cik: '0000000001', exchange: 'Nasdaq' },
        capabilities: {
          daily_accounting: { state: 'needs_review', reason: 'Issuer review required.' },
          sec_filings: { state: 'needs_review', reason: 'Filing clock review required.' },
          historical_sectors: {
            state: 'blocked',
            reason: 'Historical classification archive missing.',
          },
        },
        findings: [],
        policies: ['SYNTHETIC test information-clock limitation.'],
        action_proposals: [],
      },
    },
  }
}
function mount() {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>
        <Companies />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
function config(path: string) {
  if (path === '/company-intakes/configuration')
    return { configured: { sec_contact: true, alpaca: true }, note: 'Collection is not approval.' }
  throw new Error(path)
}

it.each([
  ['nvda', 'SPY', '2018-01-01', '2025-12-31', 730],
  ['cvs', 'QQQ', '2020-01-06', '2020-02-14', 30],
  ['brk.b', 'DIA', '2019-01-02', '2021-12-31', 365],
] as const)(
  'submits selected %s dates, benchmark and warm-up with capability blockers',
  async (symbol, benchmark, start, end, warmup) => {
    const selected = {
      ...job,
      status: 'queued',
      request_payload: {
        ...job.request_payload,
        symbol: symbol.toUpperCase(),
        benchmark,
        start,
        end,
        warmup_days: warmup,
      },
    }
    api.mockImplementation(async (path: string, method?: string, body?: unknown) => {
      if (path === '/company-intakes' && method === 'POST') {
        expect(body).toMatchObject({
          symbol: symbol.toUpperCase(),
          benchmark,
          start,
          end,
          warmup_days: warmup,
          capabilities: ['daily_accounting', 'sec_filings', 'historical_sectors'],
        })
        expect((body as { idempotency_key: string }).idempotency_key).toHaveLength(36)
        return selected
      }
      if (path === '/company-intakes') return []
      if (path === '/company-intakes/intake') return { ...detail(), ...selected, report: null }
      return config(path)
    })
    mount()
    const user = userEvent.setup()
    await user.clear(screen.getByLabelText('Ticker'))
    await user.type(screen.getByLabelText('Ticker'), symbol)
    await user.clear(screen.getByLabelText('Benchmark'))
    await user.type(screen.getByLabelText('Benchmark'), benchmark)
    await user.clear(screen.getByLabelText('Start date'))
    await user.type(screen.getByLabelText('Start date'), start)
    await user.clear(screen.getByLabelText('End date'))
    await user.type(screen.getByLabelText('End date'), end)
    await user.clear(screen.getByLabelText('Warm-up calendar days'))
    await user.type(screen.getByLabelText('Warm-up calendar days'), String(warmup))
    await user.click(screen.getByLabelText(/Historical sectors — collector pending/))
    await user.click(screen.getByRole('button', { name: 'Collect evidence' }))
    await screen.findByRole('button', { name: 'Cancel collection' })
    expect(
      screen.getByRole('heading', { name: `${symbol.toUpperCase()} evidence review` }),
    ).toBeInTheDocument()
    expect(screen.getByText(/A collection report does not make data eligible/)).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Create immutable reviewed package' }),
    ).not.toBeInTheDocument()
  },
)

it('requires explicit policy, identity and coverage review and never approves unsupported capabilities', async () => {
  const data = detail()
  api.mockImplementation(async (path: string, method?: string, body?: unknown) => {
    if (path === '/company-intakes') return [job]
    if (path === '/company-intakes/intake') return data
    if (path === '/company-intakes/intake/approve') {
      expect(method).toBe('POST')
      expect(body).toMatchObject({
        expected_report_hash: 'a'.repeat(64),
        approve_capabilities: ['daily_accounting'],
        acknowledge_policies: true,
        attest_historical_identity: true,
        attest_action_coverage: true,
        actions: [],
      })
      data.packages = [
        {
          id: 'package',
          content_hash: 'b'.repeat(64),
          payload: {
            ready_capabilities: ['daily_accounting'],
            dataset: { id: 'reviewed-dataset' },
            strategy_inputs: [],
          },
        },
      ]
      return data.packages[0]
    }
    return config(path)
  })
  mount()
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /NVDA · 2024/ }))
  const button = await screen.findByRole('button', { name: 'Create immutable reviewed package' })
  expect(button).toBeDisabled()
  expect(screen.getByLabelText('Approve Historical sectors')).toBeDisabled()
  await user.click(screen.getByLabelText('Approve Daily prices, FX and corporate actions'))
  await user.click(screen.getByLabelText(/I reviewed and accept every/))
  await user.click(screen.getByLabelText(/I checked historical ticker/))
  await user.type(
    screen.getByLabelText('Review note'),
    'SYNTHETIC explicit review of source scope and issuer evidence.',
  )
  expect(button).toBeDisabled()
  await user.click(screen.getByLabelText(/I checked complete split/))
  await user.click(button)
  await screen.findByText(/Reviewed package package/)
  expect(screen.getByText(/Other requested capabilities retain their blockers/)).toBeInTheDocument()
  expect(screen.getByText(/Run-specific readiness still checks/)).toBeInTheDocument()
  await waitFor(() =>
    expect(screen.getByText('Historical classification archive missing.')).toBeInTheDocument(),
  )
})

it('surfaces collection failures and offers retry as a separate attempt', async () => {
  const failed = {
    ...detail(),
    report: null,
    status: 'failed',
    error: 'Source access rejected; no substitution.',
  }
  api.mockImplementation(async (path: string) => {
    if (path === '/company-intakes') return [failed]
    if (path === '/company-intakes/intake') return failed
    if (path === '/company-intakes/intake/retry') return { ...job, id: 'retry', status: 'queued' }
    if (path === '/company-intakes/retry')
      return { ...failed, id: 'retry', status: 'queued', error: null }
    return config(path)
  })
  mount()
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: /NVDA · 2024/ }))
  await screen.findByText('Source access rejected; no substitution.')
  await user.click(screen.getByRole('button', { name: 'Retry as a new collection' }))
  await screen.findByRole('button', { name: 'Cancel collection' })
})
