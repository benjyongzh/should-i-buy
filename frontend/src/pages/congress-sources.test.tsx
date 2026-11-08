import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { CongressSources } from './CongressSources'
const { api } = vi.hoisted(() => ({ api: vi.fn() }))
vi.mock('../lib/api', () => ({ api }))
afterEach(() => {
  cleanup()
  api.mockReset()
})
function ledger(blockers: string[] = []) {
  return {
    id: 'ledger',
    kind: 'congress_ledger',
    content_hash: 'ledger-hash',
    data: {
      request: {
        name: 'SYNTHETIC scoped ledger',
        synthetic: true,
        first_name: 'Fixture',
        last_name: 'Filer',
        filing_start: '2022-03-01',
        filing_end: '2022-03-31',
        symbols: ['AAPL'],
        observations: [],
      },
      raw_source_id: 'raw',
      raw_source_hash: 'raw-hash',
      blockers,
      review_warning: 'Selected filing cohort only, not an all-Congress feed.',
      canonical_transactions: [{}],
      clock_audit: [
        {
          canonical_transaction_id: 'one',
          observed_at: '2022-10-23T14:43:00Z',
          disposition: 'older_filing_observed_late',
          selected_observation_id: 'amended',
          event_id: null,
        },
      ],
      source: { stream_id: 'HOUSE_FIXTURE', events: [{}] },
    },
    approvals: [],
  }
}
function mount() {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter>
        <CongressSources />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
function serve(saved: ReturnType<typeof ledger>) {
  api.mockImplementation(async (path: string) => {
    if (path.endsWith('/artifacts')) return []
    if (path.endsWith('/ledgers'))
      return [{ id: 'ledger', name: 'SYNTHETIC scoped ledger', blockers: saved.data.blockers }]
    return saved
  })
}
it('collects a specific document without substituting a missing public clock', async () => {
  const user = userEvent.setup()
  api.mockImplementation(async (path: string, method?: string, body?: unknown) => {
    if (path.endsWith('/house-documents')) {
      expect(body).toEqual({ year: 2022, document_id: '10000002', archive_capture: null })
      return { verified_public_observation: null, findings: ['No verified archival observation'] }
    }
    return []
  })
  mount()
  await user.type(screen.getByLabelText('House document ID'), '10000002')
  await user.click(screen.getByRole('button', { name: 'Acquire PDF and archive evidence' }))
  await screen.findByText(/No verified archival observation/)
  expect(api.mock.calls.filter((c) => c[1] === 'POST')).toHaveLength(1)
})
it('keeps approval disabled for unresolved clock blockers despite acknowledgements', async () => {
  const user = userEvent.setup()
  serve(ledger(['Missing verified public observation']))
  mount()
  await screen.findByRole('option', { name: /SYNTHETIC scoped ledger/ })
  await user.selectOptions(screen.getByLabelText('Inspect retained Congress ledger'), 'ledger')
  await screen.findByText('Approval blocked')
  for (const c of screen.getAllByRole('checkbox')) await user.click(c)
  await user.type(
    screen.getByLabelText('Congress source review note'),
    'SYNTHETIC human review cannot erase a missing observation clock.',
  )
  expect(screen.getByRole('button', { name: 'Approve bounded source revision' })).toBeDisabled()
  expect(api.mock.calls.filter((c) => c[1] === 'POST')).toHaveLength(0)
})
it('shows late-original suppression and requires all explicit bounded-review attestations', async () => {
  const user = userEvent.setup(),
    saved = ledger()
  serve(saved)
  api.mockImplementation(async (path: string, method?: string, body?: unknown) => {
    if (path.endsWith('/approve')) {
      expect(body).toMatchObject({
        acknowledge_conservative_observation_clocks: true,
        attest_inventory_and_all_selected_rows: true,
        attest_identity_taxonomy_and_amendments: true,
      })
      return { source: { id: 'reviewed' } }
    }
    if (path.endsWith('/artifacts')) return []
    if (path.endsWith('/ledgers'))
      return [{ id: 'ledger', name: 'SYNTHETIC scoped ledger', blockers: [] }]
    return saved
  })
  mount()
  await screen.findByRole('option', { name: /SYNTHETIC scoped ledger/ })
  await user.selectOptions(screen.getByLabelText('Inspect retained Congress ledger'), 'ledger')
  await screen.findByText(/older filing observed late/)
  expect(
    screen.getByText('SYNTHETIC demonstration source · explicitly selected'),
  ).toBeInTheDocument()
  const approve = screen.getByRole('button', { name: 'Approve bounded source revision' })
  expect(approve).toBeDisabled()
  for (const c of screen.getAllByRole('checkbox')) await user.click(c)
  await user.type(
    screen.getByLabelText('Congress source review note'),
    'SYNTHETIC explicitly reviewed selected-cohort source and observation limits.',
  )
  await user.click(approve)
  await waitFor(() => expect(api.mock.calls.filter((c) => c[1] === 'POST')).toHaveLength(1))
  expect(
    screen.getByText('Selected filing cohort only, not an all-Congress feed.'),
  ).toBeInTheDocument()
})
