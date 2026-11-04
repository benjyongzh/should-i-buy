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
          onChange(
            t === 'constant'
              ? constant
              : t === 'price'
                ? { type: 'price', field: 'close' }
                : t === 'indicator'
                  ? { type: 'indicator', name: 'sma', period: 20, field: 'close' }
                  : { type: 'multiply', left: constant, right: constant },
          )
        }}
      >
        <option value="price">Price / volume</option>
        <option value="indicator">Indicator</option>
        <option value="constant">Constant</option>
        <option value="multiply">Multiply</option>
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
      {(value.type === 'price' || value.type === 'indicator') && (
        <select
          aria-label="Price field"
          value={value.field || 'close'}
          onChange={(e) => onChange({ ...value, field: e.target.value })}
        >
          {['close', 'open', 'high', 'low', 'volume'].map((f) => (
            <option key={f}>{f}</option>
          ))}
        </select>
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
      {value.type === 'multiply' && (
        <>
          <ExpressionEditor value={value.left} onChange={(left) => onChange({ ...value, left })} />
          <span>×</span>
          <ExpressionEditor
            value={value.right}
            onChange={(right) => onChange({ ...value, right })}
          />
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
