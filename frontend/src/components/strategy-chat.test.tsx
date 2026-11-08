import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrategyChat } from './StrategyChat'
import { defaultStrategy } from '../types'
import type { Strategy } from '../types'
import type { StreamEvent } from '../lib/stream'

const mock = vi.hoisted(() => ({ api: vi.fn(), stream: vi.fn() }))
vi.mock('../lib/api', () => ({ api: mock.api }))
vi.mock('../lib/stream', () => ({ streamEvents: mock.stream }))
const context = {
  context_hash: 'fixture-hash',
  evidence_cutoff: '2025-01-01T00:00:00Z',
  retrieval: 'Selected local revisions only; no remote search.',
  evidence: [],
  model: 'fixture-model',
  history_turn_ids: [],
}
const strategy = {
  id: 's1',
  name: 'SYNTHETIC',
  draft: defaultStrategy,
  draft_revision: 1,
} as Strategy
const answer = {
  message: 'What should small mean?',
  outcome: 'clarify',
  questions: [{ question: 'What should small mean?', choices: ['SGD500', '10% available cash'] }],
  estimates: [],
  assumptions: [],
  data_requirements: [],
  unsupported_requests: [],
}
const turn = {
  id: 't1',
  user_text: 'Use small positions',
  status: 'completed',
  partial_text: answer.message,
  reply_json: answer,
  context_json: context,
  source_revision: 1,
  proposal_id: null,
  error: null,
}
beforeEach(() => {
  mock.api.mockReset()
  mock.stream.mockReset()
  mock.api.mockResolvedValue([])
})
afterEach(cleanup)
function show(onProposal = vi.fn()) {
  render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <StrategyChat strategy={strategy} onProposal={onProposal} />
    </QueryClientProvider>,
  )
  return onProposal
}

it('asks a clarification, shows source activity, and lets the user compose an answer without autoaccepting', async () => {
  const user = userEvent.setup()
  const onProposal = show()
  mock.stream.mockImplementation(
    async (_: string, __: unknown, receive: (event: StreamEvent) => void) => {
      receive({ type: 'context', data: { context } })
      receive({ type: 'delta', data: { text: answer.message } })
      mock.api.mockImplementation(async (path: string) => (path.endsWith('/turns') ? [turn] : []))
      receive({ type: 'complete', data: { turn, proposal: null, stale: false } })
    },
  )
  await user.type(screen.getByLabelText('Strategy conversation message'), 'Use small positions')
  await user.click(screen.getByRole('button', { name: 'Send message' }))
  await screen.findByRole('button', { name: '10% available cash' })
  expect(onProposal).not.toHaveBeenCalled()
  expect(screen.getAllByText(/No market data or research results supplied/).length).toBeGreaterThan(
    0,
  )
  await user.click(screen.getByRole('button', { name: '10% available cash' }))
  expect(screen.getByLabelText('Strategy conversation message')).toHaveValue(
    'What should small mean?: 10% available cash',
  )
  expect(mock.stream).toHaveBeenCalledTimes(1)
})

it('shows text before stream completion and can stop without producing a proposal', async () => {
  const user = userEvent.setup()
  const onProposal = show()
  mock.stream.mockImplementation(
    async (_: string, __: unknown, receive: (event: StreamEvent) => void, signal: AbortSignal) => {
      receive({ type: 'context', data: { context } })
      receive({ type: 'delta', data: { text: 'Progressive partial reply' } })
      await new Promise((_, reject) =>
        signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError'))),
      )
    },
  )
  await user.type(screen.getByLabelText('Strategy conversation message'), 'Make it safer')
  await user.click(screen.getByRole('button', { name: 'Send message' }))
  expect(await screen.findByLabelText('Streaming assistant reply')).toHaveTextContent(
    'Progressive partial reply',
  )
  await user.click(screen.getByRole('button', { name: 'Stop reply' }))
  await waitFor(() =>
    expect(screen.getByRole('alert')).toHaveTextContent('Partial text is unvalidated'),
  )
  expect(onProposal).not.toHaveBeenCalled()
})

it('renders estimates as research with their method, uncertainty and selected evidence', async () => {
  mock.api.mockImplementation(async (path: string) =>
    path.endsWith('/turns')
      ? [
          {
            ...turn,
            reply_json: {
              ...answer,
              outcome: 'discuss',
              questions: [],
              estimates: [
                {
                  estimate: 'A conditional gain is plausible.',
                  horizon: 'Next month',
                  method: 'Scenario from selected history',
                  uncertainty: 'High; not calibrated',
                  evidence_ids: ['source1'],
                },
              ],
            },
            context_json: {
              ...context,
              evidence: [
                {
                  id: 'source1',
                  name: 'SYNTHETIC selected source',
                  kind: 'accounting_dataset',
                  content_hash: 'hash',
                  reviewed: false,
                  synthetic: true,
                  source_url: null,
                  availability_policy: 'SYNTHETIC test only',
                  summary: {},
                },
              ],
            },
          },
        ]
      : [],
  )
  show()
  expect(await screen.findByText('Estimate · research only')).toBeInTheDocument()
  expect(screen.getByText('Uncertainty: High; not calibrated')).toBeInTheDocument()
  expect(screen.getByText('Evidence: SYNTHETIC selected source')).toBeInTheDocument()
})

it('follows streamed replies until the user scrolls back to audit earlier messages', async () => {
  const user = userEvent.setup()
  let deliver: (event: StreamEvent) => void = () => {}
  mock.stream.mockImplementation(
    async (_: string, __: unknown, receive: (event: StreamEvent) => void, signal: AbortSignal) => {
      deliver = receive
      await new Promise((_, reject) =>
        signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError'))),
      )
    },
  )
  show()
  const log = screen.getByRole('log', { name: 'Strategy conversation' })
  Object.defineProperties(log, {
    scrollHeight: { value: 1000, configurable: true },
    clientHeight: { value: 500, configurable: true },
  })
  await user.type(screen.getByLabelText('Strategy conversation message'), 'Clarify risk')
  await user.click(screen.getByRole('button', { name: 'Send message' }))
  await act(async () => deliver({ type: 'delta', data: { text: 'First streamed text' } }))
  expect(log.scrollTop).toBe(1000)
  log.scrollTop = 0
  fireEvent.scroll(log)
  await act(async () => deliver({ type: 'delta', data: { text: ' plus more text' } }))
  expect(log.scrollTop).toBe(0)
  await user.click(screen.getByRole('button', { name: 'Stop reply' }))
})
