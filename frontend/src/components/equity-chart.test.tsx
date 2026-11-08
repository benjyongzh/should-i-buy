import type { ReactNode, MouseEvent } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it, vi } from 'vitest'
import { EquityChart, type EquitySeries } from './EquityChart'

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <>{children}</>,
  LineChart: ({
    children,
    onClick,
  }: {
    children: ReactNode
    onClick: (state: { activeLabel: string }, event: MouseEvent) => void
  }) => (
    <div onClick={(event) => onClick({ activeLabel: '2020-01-03' }, event)}>
      <button>Inspect plotted session</button>
      {children}
    </div>
  ),
  Brush: ({
    startIndex,
    endIndex,
    onChange,
  }: {
    startIndex?: number
    endIndex?: number
    onChange: (range: { startIndex: number; endIndex: number }) => void
  }) => (
    <div className="recharts-brush">
      <output aria-label="Visible chart range">
        {startIndex === undefined ? 'full' : `${startIndex}:${endIndex}`}
      </output>
      <button onClick={() => onChange({ startIndex: 0, endIndex: 1 })}>Zoom history</button>
    </div>
  ),
  CartesianGrid: () => null,
  Legend: () => null,
  Line: () => null,
  ReferenceLine: () => null,
  Tooltip: () => null,
  XAxis: () => null,
  YAxis: () => null,
}))
afterEach(cleanup)
function history(year = '2020'): EquitySeries[] {
  return [
    {
      name: 'SYNTHETIC history',
      equity: ['02', '03', '06'].map((day) => ({
        date: `${year}-01-${day}`,
        equity: '10500',
        performance_equity: '10000',
        cash: '10500',
        exposure: '0',
        unrealized_pnl: '0',
        realized_pnl: '0',
        drawdown: 0,
      })),
    },
  ]
}

it('keeps the zoom when inspecting a session or switching the financial measure', async () => {
  const onSelectDate = vi.fn()
  const view = render(<EquityChart series={history()} zoom onSelectDate={onSelectDate} />)
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Zoom history' }))
  expect(screen.getByLabelText('Visible chart range')).toHaveTextContent('0:1')
  expect(onSelectDate).not.toHaveBeenCalled()
  await user.click(screen.getByRole('button', { name: 'Inspect plotted session' }))
  expect(onSelectDate).toHaveBeenCalledWith('2020-01-03')
  view.rerender(
    <EquityChart series={history()} zoom selectedDate="2020-01-03" onSelectDate={onSelectDate} />,
  )
  expect(screen.getByLabelText('Visible chart range')).toHaveTextContent('0:1')
  await user.selectOptions(screen.getByLabelText('Chart measure'), 'performance')
  expect(screen.getByLabelText('Visible chart range')).toHaveTextContent('0:1')
})

it('resets the zoom when the selected history has different observation dates', async () => {
  const view = render(<EquityChart series={history()} zoom />)
  await userEvent.setup().click(screen.getByRole('button', { name: 'Zoom history' }))
  expect(screen.getByLabelText('Visible chart range')).toHaveTextContent('0:1')
  view.rerender(<EquityChart series={history('2021')} zoom />)
  expect(screen.getByLabelText('Visible chart range')).toHaveTextContent('full')
})
