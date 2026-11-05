import { useState } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it } from 'vitest'
import type { Numeric } from '../types'
import { ExpressionEditor } from './RuleEditor'

afterEach(cleanup)
function Harness() {
  const [value, setValue] = useState<Numeric>({ type: 'price', field: 'close' })
  return (
    <>
      <ExpressionEditor value={value} onChange={setValue} />
      <output data-testid="json">{JSON.stringify(value)}</output>
    </>
  )
}
it('edits MACD, stochastic and external series as declarative operands', async () => {
  const user = userEvent.setup()
  render(<Harness />)
  const read = () => JSON.parse(screen.getByTestId('json').textContent || '{}')
  await user.selectOptions(screen.getByLabelText('Expression type'), 'macd')
  await user.selectOptions(screen.getByLabelText('MACD component'), 'signal')
  await user.clear(screen.getByLabelText('MACD fast_period'))
  await user.type(screen.getByLabelText('MACD fast_period'), '10')
  expect(read()).toEqual({
    type: 'macd',
    fast_period: 10,
    slow_period: 26,
    signal_period: 9,
    component: 'signal',
    field: 'close',
  })
  await user.selectOptions(screen.getByLabelText('Expression type'), 'stochastic')
  await user.selectOptions(screen.getByLabelText('Stochastic component'), 'd')
  expect(read()).toEqual({
    type: 'stochastic',
    period: 14,
    smooth_k: 3,
    smooth_d: 3,
    component: 'd',
  })
  await user.selectOptions(screen.getByLabelText('Expression type'), 'external')
  await user.clear(screen.getByLabelText('External series ID'))
  await user.type(screen.getByLabelText('External series ID'), 'FEAR_GREED_US')
  expect(read()).toEqual({ type: 'external', series_id: 'FEAR_GREED_US', max_age_days: 7 })
})
