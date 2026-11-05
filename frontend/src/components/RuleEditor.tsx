import type { Condition, Numeric } from '../types'
import { Field } from './ui'

const constant: Numeric = { type: 'constant', value: 0 }
const compare: Condition = {
  type: 'compare',
  op: 'gt',
  left: { type: 'price', field: 'close' },
  right: { type: 'indicator', name: 'sma', period: 20, field: 'close' },
}
const names = ['sma', 'ema', 'rsi', 'momentum', 'avg_volume', 'rolling_high', 'rolling_low']
const advancedDefaults: Record<string, Numeric> = {
  market: { type: 'market', timeframe: 'daily', expression: { type: 'price', field: 'close' } },
  calendar: { type: 'calendar', field: 'minutes_after_open' },
  portfolio: { type: 'portfolio', field: 'cash' },
  corporate_action: {
    type: 'corporate_action',
    kind: 'dividend',
    window: 'effective_next',
    days: 7,
    measure: 'count',
  },
  event: {
    type: 'event',
    stream_id: 'COMPANY_NEWS',
    categories: [],
    scope: 'symbol',
    measure: 'count',
    lookback_minutes: 1440,
    access: 'public_only',
    actors: [],
    value_field: 'score',
  },
  arithmetic: { type: 'arithmetic', op: 'add', left: constant, right: constant },
}
export function ExpressionEditor({
  value,
  onChange,
}: {
  value: Numeric
  onChange: (n: Numeric) => void
}) {
  return (
    <div className="expression">
      <select
        aria-label="Expression type"
        value={value.type}
        onChange={(e) => {
          const t = e.target.value
          if (advancedDefaults[t]) {
            onChange(structuredClone(advancedDefaults[t]))
            return
          }
          onChange(
            t === 'constant'
              ? constant
              : t === 'price'
                ? { type: 'price', field: 'close' }
                : t === 'indicator'
                  ? { type: 'indicator', name: 'sma', period: 20, field: 'close' }
                  : t === 'macd'
                    ? {
                        type: 'macd',
                        fast_period: 12,
                        slow_period: 26,
                        signal_period: 9,
                        component: 'histogram',
                        field: 'close',
                      }
                    : t === 'stochastic'
                      ? { type: 'stochastic', period: 14, smooth_k: 3, smooth_d: 3, component: 'k' }
                      : t === 'external'
                        ? { type: 'external', series_id: 'DGS10', max_age_days: 7 }
                        : { type: 'multiply', left: constant, right: constant },
          )
        }}
      >
        <option value="price">Price / volume</option>
        <option value="indicator">Indicator</option>
        <option value="macd">MACD</option>
        <option value="stochastic">Stochastic</option>
        <option value="external">External series</option>
        <option value="constant">Constant</option>
        <option value="multiply">Multiply</option>
        {Object.keys(advancedDefaults).map((t) => (
          <option key={t} value={t}>
            {t.replace('_', ' ')}
          </option>
        ))}
      </select>
      {value.type === 'constant' && (
        <input
          aria-label="Constant value"
          type="number"
          step="any"
          value={value.value}
          onChange={(e) => onChange({ ...value, value: e.target.value })}
        />
      )}
      {(value.type === 'price' || value.type === 'indicator' || value.type === 'macd') && (
        <select
          aria-label="Price field"
          value={value.field || 'close'}
          onChange={(e) => onChange({ ...value, field: e.target.value })}
        >
          {(value.type === 'macd'
            ? ['close', 'open', 'high', 'low']
            : ['close', 'open', 'high', 'low', 'volume']
          ).map((f) => (
            <option key={f}>{f}</option>
          ))}
        </select>
      )}
      {value.type === 'macd' && (
        <>
          <select
            aria-label="MACD component"
            value={value.component}
            onChange={(e) =>
              onChange({ ...value, component: e.target.value as 'line' | 'signal' | 'histogram' })
            }
          >
            {['line', 'signal', 'histogram'].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
          {(['fast_period', 'slow_period', 'signal_period'] as const).map((key) => (
            <Field key={key} label={key.replace('_', ' ')}>
              <input
                aria-label={`MACD ${key}`}
                type="number"
                min={key === 'slow_period' ? 3 : 2}
                max={500}
                value={value[key]}
                onChange={(e) => onChange({ ...value, [key]: Number(e.target.value) })}
              />
            </Field>
          ))}
        </>
      )}
      {value.type === 'stochastic' && (
        <>
          <select
            aria-label="Stochastic component"
            value={value.component}
            onChange={(e) => onChange({ ...value, component: e.target.value as 'k' | 'd' })}
          >
            <option value="k">%K</option>
            <option value="d">%D</option>
          </select>
          {(['period', 'smooth_k', 'smooth_d'] as const).map((key) => (
            <Field key={key} label={key.replace('_', ' ')}>
              <input
                aria-label={`Stochastic ${key}`}
                type="number"
                min={key === 'period' ? 2 : 1}
                max={key === 'period' ? 500 : 100}
                value={value[key]}
                onChange={(e) => onChange({ ...value, [key]: Number(e.target.value) })}
              />
            </Field>
          ))}
        </>
      )}
      {value.type === 'external' && (
        <>
          <Field label="Series ID">
            <input
              aria-label="External series ID"
              pattern="[A-Z][A-Z0-9_]{0,31}"
              maxLength={32}
              value={value.series_id}
              onChange={(e) => onChange({ ...value, series_id: e.target.value })}
            />
          </Field>
          <Field label="Maximum age (days)">
            <input
              aria-label="Maximum observation age in days"
              type="number"
              min={1}
              max={366}
              value={value.max_age_days}
              onChange={(e) => onChange({ ...value, max_age_days: Number(e.target.value) })}
            />
          </Field>
          <small>
            Select a reviewed revision of this series when scheduling. Age runs from its observation
            date; missing or stale coverage blocks the run.
          </small>
        </>
      )}
      {value.type === 'indicator' && (
        <>
          <select
            aria-label="Indicator"
            value={value.name}
            onChange={(e) => onChange({ ...value, name: e.target.value })}
          >
            {names.map((n) => (
              <option key={n}>{n}</option>
            ))}
          </select>
          <input
            aria-label="Indicator period"
            type="number"
            min={2}
            max={500}
            value={value.period}
            onChange={(e) => onChange({ ...value, period: Number(e.target.value) })}
          />
        </>
      )}
      {(value.type === 'multiply' || value.type === 'arithmetic') && (
        <>
          <ExpressionEditor value={value.left} onChange={(left) => onChange({ ...value, left })} />
          {value.type === 'multiply' ? (
            <span>×</span>
          ) : (
            <select
              aria-label="Arithmetic operation"
              value={value.op}
              onChange={(e) => onChange({ ...value, op: e.target.value as typeof value.op })}
            >
              {['add', 'subtract', 'divide', 'min', 'max'].map((op) => (
                <option key={op}>{op}</option>
              ))}
            </select>
          )}
          <ExpressionEditor
            value={value.right}
            onChange={(right) => onChange({ ...value, right })}
          />
        </>
      )}
      {value.type === 'market' && (
        <>
          <Field label="Operand timeframe">
            <select
              value={value.timeframe}
              onChange={(e) =>
                onChange({ ...value, timeframe: e.target.value as 'daily' | 'intraday' })
              }
            >
              <option value="daily">Completed daily bars</option>
              <option value="intraday">Completed intraday bars</option>
            </select>
          </Field>
          <ExpressionEditor
            value={value.expression}
            onChange={(expression) => onChange({ ...value, expression })}
          />
        </>
      )}
      {(value.type === 'calendar' || value.type === 'portfolio') && (
        <Field label={`${value.type} field`}>
          <select
            value={value.field}
            onChange={(e) => onChange({ ...value, field: e.target.value } as Numeric)}
          >
            {(value.type === 'calendar'
              ? [
                  'minutes_after_open',
                  'minutes_before_close',
                  'weekday',
                  'day_of_month',
                  'month',
                  'year',
                  'session_of_month',
                ]
              : ['cash', 'equity', 'position_quantity', 'position_weight', 'holding_sessions']
            ).map((field) => (
              <option key={field}>{field}</option>
            ))}
          </select>
        </Field>
      )}
      {value.type === 'corporate_action' && (
        <>
          <Field label="Action kind">
            <select
              value={value.kind}
              onChange={(e) => onChange({ ...value, kind: e.target.value as typeof value.kind })}
            >
              <option value="dividend">Dividend</option>
              <option value="split">Split</option>
            </select>
          </Field>
          <Field label="Known action window">
            <select
              value={value.window}
              onChange={(e) =>
                onChange({ ...value, window: e.target.value as typeof value.window })
              }
            >
              {['announced_past', 'effective_next', 'effective_past'].map((w) => (
                <option key={w}>{w}</option>
              ))}
            </select>
          </Field>
          <Field label="Action days">
            <input
              type="number"
              min={0}
              max={366}
              value={value.days}
              onChange={(e) => onChange({ ...value, days: Number(e.target.value) })}
            />
          </Field>
          <Field label="Action measure">
            <select
              value={value.measure}
              onChange={(e) =>
                onChange({ ...value, measure: e.target.value as typeof value.measure })
              }
            >
              <option value="count">Count</option>
              <option value="sum_value">Sum of action values</option>
            </select>
          </Field>
        </>
      )}
      {value.type === 'event' && (
        <>
          <Field label="Event stream ID">
            <input
              value={value.stream_id}
              onChange={(e) => onChange({ ...value, stream_id: e.target.value.toUpperCase() })}
            />
          </Field>
          <Field label="Event categories / tags (comma-separated)">
            <input
              value={value.categories.join(', ')}
              onChange={(e) =>
                onChange({
                  ...value,
                  categories: e.target.value
                    .split(',')
                    .map((s) => s.trim())
                    .filter(Boolean),
                })
              }
            />
          </Field>
          <Field label="Event actors (comma-separated)">
            <input
              value={value.actors.join(', ')}
              onChange={(e) =>
                onChange({
                  ...value,
                  actors: e.target.value
                    .split(',')
                    .map((s) => s.trim())
                    .filter(Boolean),
                })
              }
            />
          </Field>
          <Field label="Event scope">
            <select
              value={value.scope}
              onChange={(e) => onChange({ ...value, scope: e.target.value as typeof value.scope })}
            >
              {['symbol', 'sector', 'global'].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </Field>
          <Field label="Event lookback (minutes)">
            <input
              type="number"
              min={1}
              max={527040}
              value={value.lookback_minutes}
              onChange={(e) => onChange({ ...value, lookback_minutes: Number(e.target.value) })}
            />
          </Field>
          <Field label="Event access">
            <select
              value={value.access}
              onChange={(e) =>
                onChange({ ...value, access: e.target.value as typeof value.access })
              }
            >
              <option value="public_only">Public records only</option>
              <option value="any_licensed">Include licensed information</option>
            </select>
          </Field>
          <Field label="Event measure">
            <select
              value={value.measure}
              onChange={(e) =>
                onChange({ ...value, measure: e.target.value as typeof value.measure })
              }
            >
              {['count', 'sum_score', 'latest_score'].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </Field>
          <Field label="Event value field">
            <select
              value={value.value_field}
              onChange={(e) =>
                onChange({ ...value, value_field: e.target.value as typeof value.value_field })
              }
            >
              {[
                'score',
                'analyst_target_after',
                'congress_amount_min',
                'congress_amount_max',
                'economic_actual',
                'economic_surprise',
              ].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </Field>
          <small>
            Only records available at the decision clock qualify. Congress trades use public
            disclosure time. Scores require their own availability evidence.
          </small>
        </>
      )}
    </div>
  )
}
export function RuleEditor({
  value,
  onChange,
  depth = 0,
}: {
  value: Condition
  onChange: (c: Condition) => void
  depth?: number
}) {
  return (
    <div className="rule">
      <Field label="Condition">
        <select
          value={value.type}
          onChange={(e) => {
            const type = e.target.value
            onChange(
              type === 'compare'
                ? structuredClone(compare)
                : type === 'always'
                  ? { type: 'always', value: true }
                  : type === 'not'
                    ? { type: 'not', condition: { type: 'always', value: true } }
                    : { type: type as 'all' | 'any', conditions: [structuredClone(compare)] },
            )
          }}
        >
          <option value="compare">Compare expressions</option>
          <option value="always">Constant signal</option>
          <option value="all">All conditions (AND)</option>
          <option value="any">Any condition (OR)</option>
          <option value="not">Negate (NOT)</option>
        </select>
      </Field>
      {value.type === 'always' && (
        <select
          aria-label="Constant signal"
          value={String(value.value)}
          onChange={(e) => onChange({ ...value, value: e.target.value === 'true' })}
        >
          <option value="true">True</option>
          <option value="false">False / hold</option>
        </select>
      )}
      {value.type === 'compare' && (
        <div className="comparison-rule">
          <ExpressionEditor value={value.left} onChange={(left) => onChange({ ...value, left })} />
          <select
            aria-label="Comparison operator"
            value={value.op}
            onChange={(e) => onChange({ ...value, op: e.target.value })}
          >
            {['gt', 'lt', 'gte', 'lte', 'eq', 'crosses_above', 'crosses_below'].map((op) => (
              <option key={op}>{op}</option>
            ))}
          </select>
          <ExpressionEditor
            value={value.right}
            onChange={(right) => onChange({ ...value, right })}
          />
        </div>
      )}
      {(value.type === 'all' || value.type === 'any') && (
        <>
          {value.conditions.map((c, i) => (
            <div key={i} className="nested-rule">
              <RuleEditor
                depth={depth + 1}
                value={c}
                onChange={(next) =>
                  onChange({
                    ...value,
                    conditions: value.conditions.map((old, j) => (i === j ? next : old)),
                  })
                }
              />
              {value.conditions.length > 1 && (
                <button
                  type="button"
                  className="link-button"
                  onClick={() =>
                    onChange({ ...value, conditions: value.conditions.filter((_, j) => j !== i) })
                  }
                >
                  Remove condition
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            className="secondary"
            disabled={value.conditions.length >= 10 || depth >= 5}
            onClick={() =>
              onChange({ ...value, conditions: [...value.conditions, structuredClone(compare)] })
            }
          >
            + Add condition
          </button>
        </>
      )}
      {value.type === 'not' && (
        <RuleEditor
          depth={depth + 1}
          value={value.condition}
          onChange={(condition) => onChange({ ...value, condition })}
        />
      )}
    </div>
  )
}
