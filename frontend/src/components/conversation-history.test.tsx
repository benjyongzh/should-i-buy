import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConversationHistory } from './ConversationHistory'

const mock = vi.hoisted(() => ({ api: vi.fn() }))
vi.mock('../lib/api', () => ({ api: mock.api }))
afterEach(() => {
  cleanup()
  mock.api.mockReset()
})
const turn = (id: number) => ({
  id: String(id),
  sequence: id,
  created_at: '2020-01-01T00:00:00Z',
  status: 'completed',
  user_text: 'SYNTHETIC intent ' + id,
  partial_text: '',
  reply_json: {
    message: 'SYNTHETIC response ' + id,
    questions: [{ question: 'Which budget?', choices: ['321SGD', '500SGD'] }],
  },
  error: null,
  proposal_id: 'proposal-' + id,
  context_json: {},
})
function show(version?: { id: string; number: number }) {
  const close = vi.fn()
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <ConversationHistory strategyId="s1" version={version} onClose={close} />
    </QueryClientProvider>,
  )
  return close
}

it('reads a version transcript with pagination and export but no editing or acceptance controls', async () => {
  const user = userEvent.setup()
  mock.api.mockImplementation(async (path: string) => ({
    conversation_id: 's1',
    version_id: 'v1',
    through_sequence: 2,
    snapshot_hash: 'frozen-hash',
    origin: 'publication',
    published_at: '2020-01-02T00:00:00Z',
    accepted_chat_turn_id: '1',
    turns: [turn(path.endsWith('after=0') ? 1 : 2)],
    has_more: path.endsWith('after=0'),
    next_after: path.endsWith('after=0') ? 1 : null,
  }))
  const close = show({ id: 'v1', number: 1 })
  await screen.findByText('SYNTHETIC intent 1')
  expect(
    screen.getByRole('dialog', { name: 'Conversation through version 1 · read only' }),
  ).toBeInTheDocument()
  expect(screen.getByText('frozen-hash')).toBeInTheDocument()
  expect(screen.getByText('This proposal supplied the published draft.')).toBeInTheDocument()
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  expect(
    screen.queryByRole('button', { name: /Send message|Accept into draft|321SGD/ }),
  ).not.toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Export complete snapshot and hash' })).toHaveAttribute(
    'href',
    '/api/llm/strategies/s1/versions/v1/conversation/export',
  )
  await user.click(screen.getByRole('button', { name: 'Load more messages' }))
  await screen.findByText('SYNTHETIC intent 2')
  expect(mock.api.mock.calls.map((c) => c[0])).toEqual([
    '/llm/strategies/s1/versions/v1/conversation?after=0',
    '/llm/strategies/s1/versions/v1/conversation?after=1',
  ])
  expect(mock.api.mock.calls.every((c) => c.length === 1)).toBe(true)
  await user.click(screen.getByRole('button', { name: 'Close history' }))
  expect(close).toHaveBeenCalledTimes(1)
})

it('anchors complete-conversation pagination to the boundary first opened', async () => {
  const user = userEvent.setup()
  mock.api.mockImplementation(async (path: string) => ({
    conversation_id: 's1',
    version_id: null,
    through_sequence: 122,
    snapshot_hash: null,
    origin: 'current_conversation_read_only_view',
    turns: [turn(path.includes('after=0') ? 1 : 51)],
    has_more: path.includes('after=0'),
    next_after: path.includes('after=0') ? 50 : null,
  }))
  show()
  await screen.findByText('SYNTHETIC intent 1')
  await user.click(screen.getByRole('button', { name: 'Load more messages' }))
  await screen.findByText('SYNTHETIC intent 51')
  await waitFor(() =>
    expect(mock.api).toHaveBeenCalledWith('/llm/strategies/s1/history?after=50&through=122'),
  )
  expect(
    screen.queryByRole('link', { name: 'Export complete snapshot and hash' }),
  ).not.toBeInTheDocument()
})
