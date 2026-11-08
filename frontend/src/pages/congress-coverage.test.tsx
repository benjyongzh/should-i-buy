import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { CongressCoverage } from './CongressCoverage'
const { api } = vi.hoisted(() => ({ api: vi.fn() }))
vi.mock('../lib/api', () => ({ api }))
afterEach(() => {
  cleanup()
  api.mockReset()
})
const job = {
  id: 'job',
  status: 'queued',
  phase: 'documents',
  error: null,
  request_payload: { start_year: 2018, end_year: 2025, chambers: ['house', 'senate'] },
  state: {
    house_inventories: { '2018': { ptr_reports: 2 } },
    senate_access: { state: 'blocked_access', http_status: 403 },
  },
  total_discovered: 2,
  documents_downloaded: 1,
  verified_archive_bounds: 0,
  qualification: 'Missing posting clocks and row review remain blockers.',
  counts: [],
}
function mount(path = '/congress/coverage') {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter initialEntries={[path]}>
        <CongressCoverage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
function read(path: string) {
  if (path.endsWith('/collections')) return [job]
  if (path.includes('/items?')) return { items: [], has_more: false }
  if (path.endsWith('/senate-imports')) return []
  return job
}
it('starts the all-filer multi-year scope with boundary indexes without publishing a strategy', async () => {
  const user = userEvent.setup()
  api.mockImplementation(async (path: string, method?: string, body?: unknown) => {
    if (method === 'POST') {
      expect(path).toBe('/research/congress/collections')
      expect(body).toMatchObject({
        start_year: 2018,
        end_year: 2025,
        chambers: ['house', 'senate'],
        supporting_years: [2017, 2026],
        lookup_archives: true,
        acknowledge_personal_noncommercial_use: true,
      })
      expect(body).not.toHaveProperty('symbols')
      return job
    }
    return read(path)
  })
  mount()
  await user.click(screen.getByRole('button', { name: 'Start full-scope acquisition' }))
  await screen.findByText('Full-period strategy eligibility: not qualified')
  expect(api.mock.calls.filter((c) => c[1] === 'POST')).toHaveLength(1)
})
it('shows denied Senate access and refuses to label acquired PDFs qualified', async () => {
  api.mockImplementation(async (path: string) => read(path))
  mount('/congress/coverage?collection=job')
  await screen.findByText('Full-period strategy eligibility: not qualified')
  expect(screen.getByText(/Senate server access: blocked_access 403/)).toBeInTheDocument()
  expect(
    screen.getByText('Missing posting clocks and row review remain blockers.'),
  ).toBeInTheDocument()
  expect(
    screen.getByRole('progressbar', { name: 'Congress acquisition progress' }),
  ).toHaveAttribute('value', '1')
  expect(
    screen.getByRole('link', { name: 'Download the reviewed browser exporter' }),
  ).toHaveAttribute('href', '/senate-browser-export.js')
})
it('imports browser capture only as unreviewed Senate evidence', async () => {
  const user = userEvent.setup(),
    packet = { export_id: 'SYNTHETIC-export', part_number: 1, total_parts: 1 }
  api.mockImplementation(async (path: string, method?: string, body?: unknown) => {
    if (method === 'POST') {
      expect(path).toBe('/research/congress/senate-imports')
      expect(body).toEqual(packet)
      return { id: 'capture' }
    }
    return read(path)
  })
  mount()
  await user.click(screen.getByLabelText('Senate browser export JSON'))
  await user.paste(JSON.stringify(packet))
  await user.click(
    screen.getByRole('button', { name: 'Import Senate capture as unreviewed evidence' }),
  )
  await waitFor(() => expect(api.mock.calls.filter((c) => c[1] === 'POST')).toHaveLength(1))
  expect(api.mock.calls.some((c) => c[0].includes('/approve'))).toBe(false)
})
