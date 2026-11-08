import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, expect, it, vi } from 'vitest'
import { StrategySources } from './StrategySources'
const { api } = vi.hoisted(() => ({ api: vi.fn() }))
vi.mock('../lib/api', () => ({ api }))
afterEach(() => {
  cleanup()
  api.mockReset()
})
it('requires explicit source review and complete coverage while hiding future news', async () => {
  const raw = {
    id: 'raw',
    name: 'SYNTHETIC news source',
    kind: 'events',
    stream_id: 'COMPANY_NEWS',
    content_hash: 'a'.repeat(64),
    synthetic: true,
    reviewed: false,
    complete: false,
    symbols: ['SPY'],
    category_catalog: ['news'],
    row_count: 1,
    access_coverage: 'public_only',
    availability_policy: 'SYNTHETIC test source clocks',
    coverage_start: '2020-01-01T00:00:00Z',
    coverage_end: '2020-02-01T00:00:00Z',
  }
  const approved = { ...raw, id: 'reviewed', reviewed: true, complete: true, parent_id: 'raw' }
  let rows = [raw]
  api.mockImplementation(async (path: string, method?: string, body?: unknown) => {
    if (path === '/strategy-inputs') return rows
    if (path === '/strategy-capabilities')
      return { configured: { alpaca: true, fred: true, llm: true, benzinga: false } }
    if (path.endsWith('/export'))
      return {
        data: {
          kind: 'events',
          bars: [],
          states: [],
          events: [
            {
              event_id: 'one',
              access: 'public',
              title: 'Future source text',
              published_at: '2020-01-02T15:00:00Z',
              available_at: '2020-01-02T17:00:00Z',
            },
          ],
        },
      }
    if (path === '/strategy-inputs/raw/approve') {
      expect(method).toBe('POST')
      expect(body).toMatchObject({
        acknowledge_publication_policy: true,
        attest_complete_coverage: true,
      })
      rows = [approved, raw]
      return approved
    }
    throw new Error(path)
  })
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <StrategySources />
    </QueryClientProvider>,
  )
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: raw.name }))
  await screen.findByLabelText('Source review note')
  await screen.findByText(/"title": "Future source text"/)
  await user.type(screen.getByLabelText('Historical cutoff UTC'), '2020-01-02T16:00')
  expect(screen.queryByText(/"title": "Future source text"/)).not.toBeInTheDocument()
  await user.type(
    screen.getByLabelText('Source review note'),
    'SYNTHETIC fixture, original clocks and declared coverage explicitly checked.',
  )
  const button = screen.getByRole('button', { name: 'Create reviewed eligible revision' })
  expect(button).toBeDisabled()
  await user.click(screen.getByLabelText(/I reviewed original publication/))
  expect(button).toBeDisabled()
  await user.click(screen.getByLabelText(/I attest the declared symbol/))
  await user.click(button)
  await waitFor(() => expect(screen.getByText(/Reviewed immutable revision/)).toBeInTheDocument())
  expect(rows).toHaveLength(2)
})

it.each(['intraday', 'universe'] as const)(
  'renders %s records from a complete exported payload',
  async (kind) => {
    const source = {
      id: kind,
      kind,
      name: `SYNTHETIC ${kind}`,
      content_hash: 'a'.repeat(64),
      synthetic: true,
      reviewed: false,
      complete: false,
      symbols: ['SPY'],
      category_catalog: [],
      row_count: 1,
      access_coverage: 'public_only',
      availability_policy: 'SYNTHETIC source',
      coverage_start: '2020-01-01T00:00:00Z',
      coverage_end: '2020-02-01T00:00:00Z',
    }
    const record = { symbol: 'SPY', available_at: '2020-01-02T15:00:00Z' }
    api.mockImplementation(async (path: string) => {
      if (path === '/strategy-inputs') return [source]
      if (path === '/strategy-capabilities') return { configured: {} }
      if (path.endsWith('/export'))
        return {
          data: {
            kind,
            bars: kind === 'intraday' ? [record] : [],
            states: kind === 'universe' ? [record] : [],
            events: [],
          },
        }
      throw new Error(path)
    })
    render(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <StrategySources />
      </QueryClientProvider>,
    )
    await userEvent.setup().click(await screen.findByRole('button', { name: source.name }))
    await screen.findByText(/"symbol": "SPY"/)
    expect(screen.getByText(/1 available records/)).toBeInTheDocument()
  },
)
