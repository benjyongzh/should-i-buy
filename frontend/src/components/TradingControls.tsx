import type { StrategyConfig } from '../types'
import { Field } from './ui'

export const defaultTrading: NonNullable<StrategyConfig['trading']> = {
  entry_schedule: 'daily',
  exit_schedule: 'daily',
  allow_additions: false,
  exit_fraction: '1',
}

export function TradingControls({
  config,
  onChange,
}: {
  config: StrategyConfig
  onChange: (c: StrategyConfig) => void
}) {
  const policy = config.trading
  return (
    <>
      <h3 className="subheading">Trade timing & repeated investment</h3>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={!!policy}
          onChange={(e) => {
            const next = { ...config }
            if (e.target.checked) next.trading = { ...defaultTrading }
            else {
              delete next.trading
              if (['cash_percent', 'target_allocation'].includes(next.sizing.mode))
                next.sizing = { mode: 'equity_percent', value: '.1' }
            }
            onChange(next)
          }}
        />{' '}
        Enable timing, repeated entries and partial exits
      </label>
      {!policy && (
        <p className="muted">
          One entry while flat and full rule exits. Enable controls to configure DCA or rebalancing.
        </p>
      )}
      {policy && (
        <div className="form-grid">
          <Field label="Entry decision schedule">
            <select
              value={policy.entry_schedule}
              onChange={(e) =>
                onChange({
                  ...config,
                  trading: {
                    ...policy,
                    entry_schedule: e.target.value as typeof policy.entry_schedule,
                  },
                })
              }
            >
              <option value="daily">Every trading session</option>
              <option value="weekly">First session of each week</option>
              <option value="monthly">First session of each month</option>
              <option value="once">Once, retry until first buy fills</option>
            </select>
          </Field>
          <Field label="Exit decision schedule">
            <select
              value={policy.exit_schedule}
              onChange={(e) =>
                onChange({
                  ...config,
                  trading: {
                    ...policy,
                    exit_schedule: e.target.value as typeof policy.exit_schedule,
                  },
                })
              }
            >
              <option value="daily">Every trading session</option>
              <option value="weekly">First session of each week</option>
              <option value="monthly">First session of each month</option>
            </select>
          </Field>
          <Field label="Allow additions to held positions">
            <select
              value={String(policy.allow_additions)}
              onChange={(e) =>
                onChange({
                  ...config,
                  trading: { ...policy, allow_additions: e.target.value === 'true' },
                })
              }
            >
              <option value="false">Disabled</option>
              <option value="true">Enabled — repeated buys / DCA</option>
            </select>
          </Field>
          <Field label="Exit fraction" hint="1 sells all; 0.25 sells 25% of the current holding">
            <input
              aria-label="Exit fraction"
              type="number"
              min="0.000001"
              max="1"
              step="any"
              value={policy.exit_fraction}
              onChange={(e) =>
                onChange({ ...config, trading: { ...policy, exit_fraction: e.target.value } })
              }
            />
          </Field>
        </div>
      )}
      {policy && (
        <p className="muted">
          Schedules select close decisions; orders fill at the following open. Monthly DCA normally
          fills on the second trading session. Exit rules take priority. Profile salary deposits do
          not force a buy.
        </p>
      )}
    </>
  )
}
