import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { Compare } from './Compare'

const mock = vi.hoisted(() => ({ hashes: ['same', 'different'] }))
vi.mock('../lib/api', () => ({
  useLab: () => ({
    runs: mock.hashes.map((hash, i) => ({
      id: `r${i}`,
      status: 'completed',
      experiment_id: 'e1',
      strategy_version_id: `v${i}`,
      profile_snapshot: { account_currency: 'SGD' },
      provenance: {
        dataset_hash: 'same',
        profile_hash: 'same',
        engine_version: '1.3.0',
        external_input_hash: hash,
        synthetic: false,
      },
    })),
    versions: [],
    strategies: [],
    experiments: [],
  }),
  useResults: () => [0, 1].map(() => ({ data: { metrics: {}, equity: [] } })),
  useCashBenchmarks: () => [0, 1].map(() => ({ data: undefined })),
}))
vi.mock('../components/EquityChart', () => ({ EquityChart: () => null }))
afterEach(cleanup)
it.each([true, false])(
  'checks external manifest equality for comparison (different=%s)',
  (different) => {
    mock.hashes = ['same', different ? 'different' : 'same']
    render(
      <MemoryRouter initialEntries={['/compare?experiment=e1']}>
        <Compare />
      </MemoryRouter>,
    )
    if (different)
      expect(
        screen.getByText(
          /different profile settings, dataset revisions, engine versions or external inputs/,
        ),
      ).toBeInTheDocument()
    else
      expect(
        screen.queryByText(
          /different profile settings, dataset revisions, engine versions or external inputs/,
        ),
      ).not.toBeInTheDocument()
  },
)
