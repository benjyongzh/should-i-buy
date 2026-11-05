import type { StrategyConfig } from '../types'
import { ExpressionEditor, RuleEditor } from './RuleEditor'
import { Field } from './ui'

export function AdvancedStrategyControls({
  config,
  onChange,
}: {
  config: StrategyConfig
  onChange: (c: StrategyConfig) => void
}) {
  const execution = config.execution_policy,
    universe = config.universe
  const list = (s: string) =>
    s
      .split(',')
      .map((v) => v.trim())
      .filter(Boolean)
  return (
    <div>
      <h3>Timing and information</h3>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={!!execution}
          onChange={(e) =>
            onChange({
              ...config,
              execution_policy: e.target.checked
                ? {
                    decision_cadence: 'bar_close',
                    default_timeframe: 'intraday',
                    entry_window: { start_minutes_after_open: 60, end_minutes_before_close: 0 },
                    exit_window: { start_minutes_after_open: 0, end_minutes_before_close: 0 },
                    pending_expiry: 'session_close',
                  }
                : null,
            })
          }
        />{' '}
        Configure execution timing
      </label>
      {execution && (
        <div className="form-grid">
          <Field label="Decision cadence">
            <select
              value={execution.decision_cadence}
              onChange={(e) =>
                onChange({
                  ...config,
                  execution_policy: {
                    ...execution,
                    decision_cadence: e.target.value as typeof execution.decision_cadence,
                  },
                })
              }
            >
              <option value="daily_close">Daily close</option>
              <option value="bar_close">Completed interval</option>
              <option value="event_or_bar">Available event or completed interval</option>
            </select>
          </Field>
          <Field label="Default indicator timeframe">
            <select
              value={execution.default_timeframe}
              onChange={(e) =>
                onChange({
                  ...config,
                  execution_policy: {
                    ...execution,
                    default_timeframe: e.target.value as 'daily' | 'intraday',
                  },
                })
              }
            >
              <option value="daily">Daily</option>
              <option value="intraday">Intraday</option>
            </select>
          </Field>
          {(['entry_window', 'exit_window'] as const).map((window) => (
            <div key={window}>
              {(['start_minutes_after_open', 'end_minutes_before_close'] as const).map((key) => (
                <Field
                  key={key}
                  label={`${window.replace('_', ' ')} · ${key.replaceAll('_', ' ')}`}
                >
                  <input
                    type="number"
                    min={0}
                    max={389}
                    value={execution[window][key]}
                    onChange={(e) =>
                      onChange({
                        ...config,
                        execution_policy: {
                          ...execution,
                          [window]: { ...execution[window], [key]: Number(e.target.value) },
                        },
                      })
                    }
                  />
                </Field>
              ))}
            </div>
          ))}
          <Field label="Pending order expiry">
            <select
              value={execution.pending_expiry}
              onChange={(e) =>
                onChange({
                  ...config,
                  execution_policy: {
                    ...execution,
                    pending_expiry: e.target.value as typeof execution.pending_expiry,
                  },
                })
              }
            >
              <option value="session_close">Expire at session close</option>
              <option value="good_until_cancelled">Good until cancelled</option>
            </select>
          </Field>
        </div>
      )}
      <p className="muted">
        Timing windows require matching intraday price intervals in the profile. Orders execute at a
        strictly later eligible open; daily bars cannot represent a buy one hour after opening.
      </p>
      <h3>Historical selection and ranking</h3>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={!!universe}
          onChange={(e) =>
            onChange({
              ...config,
              universe: e.target.checked
                ? {
                    require_membership: true,
                    include_symbols: [],
                    exclude_symbols: [],
                    sectors: [],
                    exclude_sectors: [],
                    prefer_sectors: [],
                    filter: { type: 'always', value: true },
                    rank_by: null,
                    descending: true,
                    top_n: 5,
                    exit_when_ineligible: false,
                  }
                : null,
            })
          }
        />{' '}
        Configure historical universe
      </label>
      {universe && (
        <>
          <div className="form-grid">
            {(
              [
                'include_symbols',
                'exclude_symbols',
                'sectors',
                'exclude_sectors',
                'prefer_sectors',
              ] as const
            ).map((key) => (
              <Field key={key} label={`${key.replaceAll('_', ' ')} (comma-separated)`}>
                <input
                  value={universe[key].join(', ')}
                  onChange={(e) =>
                    onChange({ ...config, universe: { ...universe, [key]: list(e.target.value) } })
                  }
                />
              </Field>
            ))}
            <Field label="Select top N">
              <input
                type="number"
                min={1}
                max={50}
                value={universe.top_n}
                onChange={(e) =>
                  onChange({ ...config, universe: { ...universe, top_n: Number(e.target.value) } })
                }
              />
            </Field>
          </div>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={universe.require_membership}
              onChange={(e) =>
                onChange({
                  ...config,
                  universe: { ...universe, require_membership: e.target.checked },
                })
              }
            />{' '}
            Require historical membership / identity
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={universe.exit_when_ineligible}
              onChange={(e) =>
                onChange({
                  ...config,
                  universe: { ...universe, exit_when_ineligible: e.target.checked },
                })
              }
            />{' '}
            Request exit when no longer eligible
          </label>
          <h4>Eligibility condition</h4>
          <RuleEditor
            value={universe.filter}
            onChange={(filter) => onChange({ ...config, universe: { ...universe, filter } })}
          />
          <label className="checkbox">
            <input
              type="checkbox"
              checked={!!universe.rank_by}
              onChange={(e) =>
                onChange({
                  ...config,
                  universe: {
                    ...universe,
                    rank_by: e.target.checked
                      ? { type: 'indicator', name: 'momentum', period: 20, field: 'close' }
                      : null,
                  },
                })
              }
            />{' '}
            Rank eligible symbols by expression
          </label>
          {universe.rank_by && (
            <>
              <ExpressionEditor
                value={universe.rank_by}
                onChange={(rank_by) => onChange({ ...config, universe: { ...universe, rank_by } })}
              />
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={universe.descending}
                  onChange={(e) =>
                    onChange({ ...config, universe: { ...universe, descending: e.target.checked } })
                  }
                />{' '}
                Highest values first
              </label>
            </>
          )}
          <small>
            The profile bounds permitted symbols. Sectors and identities require reviewed historical
            states; current classifications cannot stand in for history.
          </small>
        </>
      )}
      <h3>Conditional trade sizes</h3>
      <p>
        First matching rule wins; the ordinary sizing value is the fallback. Profile cash and risk
        limits still apply.
      </p>
      {(config.sizing_rules || []).map((rule, i) => (
        <div className="nested-rule" key={i}>
          <Field label={`Sizing rule ${i + 1} label`}>
            <input
              value={rule.label}
              maxLength={120}
              onChange={(e) =>
                onChange({
                  ...config,
                  sizing_rules: config.sizing_rules!.map((r, j) =>
                    j === i ? { ...r, label: e.target.value } : r,
                  ),
                })
              }
            />
          </Field>
          <RuleEditor
            value={rule.when}
            onChange={(when) =>
              onChange({
                ...config,
                sizing_rules: config.sizing_rules!.map((r, j) => (j === i ? { ...r, when } : r)),
              })
            }
          />
          <div className="form-grid">
            <Field label={`Sizing rule ${i + 1} mode`}>
              <select
                value={rule.sizing.mode}
                onChange={(e) =>
                  onChange({
                    ...config,
                    sizing_rules: config.sizing_rules!.map((r, j) =>
                      j === i
                        ? {
                            ...r,
                            sizing: {
                              mode: e.target.value as typeof r.sizing.mode,
                              value: e.target.value === 'fixed_notional' ? 100 : 0.1,
                            },
                          }
                        : r,
                    ),
                  })
                }
              >
                {['equity_percent', 'fixed_notional', 'cash_percent', 'target_allocation'].map(
                  (mode) => (
                    <option key={mode}>{mode}</option>
                  ),
                )}
              </select>
            </Field>
            <Field label={`Sizing rule ${i + 1} value`}>
              <input
                type="number"
                step="any"
                value={rule.sizing.value}
                onChange={(e) =>
                  onChange({
                    ...config,
                    sizing_rules: config.sizing_rules!.map((r, j) =>
                      j === i ? { ...r, sizing: { ...r.sizing, value: e.target.value } } : r,
                    ),
                  })
                }
              />
            </Field>
          </div>
          <button
            type="button"
            className="link-button"
            onClick={() =>
              onChange({
                ...config,
                sizing_rules:
                  config.sizing_rules!.length === 1
                    ? null
                    : config.sizing_rules!.filter((_, j) => j !== i),
              })
            }
          >
            Remove sizing rule
          </button>
        </div>
      ))}
      <button
        type="button"
        className="secondary"
        disabled={(config.sizing_rules?.length || 0) >= 20}
        onClick={() =>
          onChange({
            ...config,
            sizing_rules: [
              ...(config.sizing_rules || []),
              {
                label: 'Conditional size',
                when: { type: 'always', value: true },
                sizing: { ...config.sizing },
              },
            ],
          })
        }
      >
        Add conditional sizing rule
      </button>
    </div>
  )
}
