import { useState } from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, it } from 'vitest'
import { AdvancedStrategyControls } from './AdvancedStrategyControls'
import { ExpressionEditor } from './RuleEditor'
import { defaultStrategy, type Numeric } from '../types'

afterEach(cleanup)
it('keeps legacy definitions unchanged until explicit timing, universe and sizing choices', async () => {
  function Harness() {
    const [config, setConfig] = useState(structuredClone(defaultStrategy))
    return (
      <>
        <AdvancedStrategyControls config={config} onChange={setConfig} />
        <output>{JSON.stringify(config)}</output>
      </>
    )
  }
  const user = userEvent.setup()
  render(<Harness />)
  const read = () => JSON.parse(screen.getByRole('status').textContent || '{}')
  expect(read()).toEqual(defaultStrategy)
  await user.click(screen.getByLabelText('Configure execution timing'))
  expect(read().execution_policy.entry_window.start_minutes_after_open).toBe(60)
  await user.selectOptions(screen.getByLabelText('Decision cadence'), 'event_or_bar')
  await user.click(screen.getByLabelText('Configure historical universe'))
  await user.type(screen.getByLabelText('prefer sectors (comma-separated)'), 'Technology')
  await user.click(screen.getByRole('button', { name: 'Add conditional sizing rule' }))
  await user.selectOptions(screen.getByLabelText('Sizing rule 1 mode'), 'cash_percent')
  expect(read().execution_policy.decision_cadence).toBe('event_or_bar')
  expect(read().universe.prefer_sectors).toEqual(['Technology'])
  expect(read().sizing_rules[0].sizing.mode).toBe('cash_percent')
  await user.click(screen.getByLabelText('Configure execution timing'))
  expect(read().execution_policy).toBeNull()
})
it('expresses public Congress information and mixed-timeframe rules without code', async () => {
  function Harness() {
    const [value, setValue] = useState<Numeric>({ type: 'constant', value: 0 })
    return (
      <>
        <ExpressionEditor value={value} onChange={setValue} />
        <output>{JSON.stringify(value)}</output>
      </>
    )
  }
  const user = userEvent.setup()
  render(<Harness />)
  await user.selectOptions(screen.getByLabelText('Expression type'), 'event')
  await user.clear(screen.getByLabelText('Event stream ID'))
  await user.type(screen.getByLabelText('Event stream ID'), 'CONGRESS_TRADES')
  await user.selectOptions(screen.getByLabelText('Event value field'), 'congress_amount_min')
  const value = JSON.parse(screen.getByRole('status').textContent || '{}')
  expect(value.stream_id).toBe('CONGRESS_TRADES')
  expect(value.access).toBe('public_only')
  expect(value.value_field).toBe('congress_amount_min')
  await user.selectOptions(screen.getByLabelText('Expression type'), 'market')
  await user.selectOptions(screen.getByLabelText('Operand timeframe'), 'daily')
  expect(JSON.parse(screen.getByRole('status').textContent || '{}')).toEqual({
    type: 'market',
    timeframe: 'daily',
    expression: { type: 'price', field: 'close' },
  })
})
