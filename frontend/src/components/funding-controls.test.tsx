import { useState } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { TradingControls } from './TradingControls'
import { EquityChart } from './EquityChart'
import { defaultStrategy, type StrategyConfig } from '../types'

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: ({
    data,
    onClick,
  }: {
    data: unknown
    onClick: (state: { activeLabel: string }) => void
  }) => (
    <>
      <output>{JSON.stringify(data)}</output>
      <button onClick={() => onClick({ activeLabel: '2020-02-03' })}>Select chart date</button>
      <button onClick={() => onClick({ activeLabel: 'missing' })}>Select missing date</button>
    </>
  ),
  CartesianGrid: () => null,
  Brush: () => null,
  ReferenceDot: () => null,
  ReferenceLine: () => null,
  Legend: () => null,
  Line: () => null,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
}))
afterEach(cleanup)

it('retains a legacy definition until controls are explicitly enabled and can restore legacy sizing', async () => {
  const user = userEvent.setup()
  function Harness() {
    const [config, setConfig] = useState<StrategyConfig>(structuredClone(defaultStrategy))
    return (
      <>
        <TradingControls config={config} onChange={setConfig} />
        <pre data-testid="config">{JSON.stringify(config)}</pre>
      </>
    )
  }
  render(<Harness />)
  expect(JSON.parse(screen.getByTestId('config').textContent!).trading).toBeUndefined()
  await user.click(screen.getByRole('checkbox'))
  await user.selectOptions(screen.getByLabelText('Entry decision schedule'), 'once')
  expect(JSON.parse(screen.getByTestId('config').textContent!).trading.entry_schedule).toBe('once')
  await user.click(screen.getByRole('checkbox'))
  expect(JSON.parse(screen.getByTestId('config').textContent!)).toEqual(defaultStrategy)
})

it('connects chart selection to a recorded session and ignores an unknown chart date', async () => {
  const user = userEvent.setup()
  const select = vi.fn()
  render(
    <EquityChart
      series={[
        {
          name: 'Account',
          equity: [
            {
              date: '2020-02-03',
              equity: '10000',
              cash: '10000',
              exposure: '0',
              drawdown: 0,
              realized_pnl: '0',
              unrealized_pnl: '0',
            },
          ],
        },
      ]}
      onSelectDate={select}
    />,
  )
  await user.click(screen.getByRole('button', { name: 'Select chart date' }))
  await user.click(screen.getByRole('button', { name: 'Select missing date' }))
  expect(select).toHaveBeenCalledExactlyOnceWith('2020-02-03')
})

it('distinguishes funded account balances from deposit-neutral performance in charts', async () => {
  const user = userEvent.setup()
  render(
    <EquityChart
      series={[
        {
          name: 'Funded',
          equity: [
            {
              date: '2020-02-03',
              equity: '15000',
              performance_equity: '10000',
              drawdown: 0,
              cash: '15000',
              exposure: '0',
              realized_pnl: '0',
              unrealized_pnl: '0',
            },
          ],
        },
      ]}
    />,
  )
  expect(screen.getByRole('status')).toHaveTextContent('15000')
  await user.selectOptions(screen.getByLabelText('Chart measure'), 'performance')
  expect(screen.getByRole('status')).toHaveTextContent('10000')
  expect(screen.getByRole('status')).not.toHaveTextContent('15000')
  expect(screen.getByRole('img')).toHaveAccessibleName('Time-weighted performance comparison chart')
})
