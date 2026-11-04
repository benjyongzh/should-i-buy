export type Numeric =
  | { type: 'constant'; value: string | number }
  | { type: 'price'; field?: string }
  | { type: 'indicator'; name: string; period: number; field?: string }
  | { type: 'multiply'; left: Numeric; right: Numeric }
export type Condition =
  | { type: 'always'; value: boolean }
  | { type: 'compare'; op: string; left: Numeric; right: Numeric }
  | { type: 'all' | 'any'; conditions: Condition[] }
  | { type: 'not'; condition: Condition }
export interface StrategyConfig {
  schema_version: 1
  entry: Condition
  exit: Condition
  sizing: { mode: 'equity_percent' | 'fixed_notional'; value: string | number }
  risk: {
    max_allocation: string | number
    max_positions: number
    stop_loss: string | number | null
    take_profit: string | number | null
  }
}
export interface Strategy {
  id: string
  name: string
  description: string
  archived: boolean
  draft: StrategyConfig
  draft_revision: number
  created_at: string
  parent_version_id: string | null
}
export interface Version {
  id: string
  strategy_id: string
  number: number
  config: StrategyConfig
  config_hash: string
  change_summary: string
  created_at: string
}
export type ProfileConfig = Record<string, string | number | boolean | string[]>
export interface Profile {
  id: string
  name: string
  config: ProfileConfig
}
export interface Dataset {
  id: string
  name: string
  provider: string
  synthetic: boolean
  content_hash: string
  metadata_json: {
    coverage: Record<
      string,
      { start: string; end: string; bars: number; missing_sessions: string[] }
    >
    fx_observations: number
    actions: number
    dividends_complete: boolean
    availability_policy: string
  }
}
export interface Run {
  id: string
  strategy_version_id: string
  profile_id: string
  dataset_id: string
  experiment_id: string
  status: string
  progress: number
  error: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
  profile_snapshot: ProfileConfig
  provenance: {
    synthetic: boolean
    dataset_hash: string
    profile_hash: string
    strategy_hash: string
    engine_version: string
  }
}
export interface Equity {
  date: string
  equity: string
  cash: string
  drawdown: number
  exposure: string
  unrealized_pnl: string
  realized_pnl: string
}
export interface Order {
  id: number
  symbol: string
  side: string
  type: string
  quantity: string
  submitted_at: string
  executed_at: string | null
  status: string
  execution_price: string | null
  fees: string
  reason: string
  rejection_reason: string | null
}
export interface Trade {
  symbol: string
  quantity: string
  opened_at: string
  closed_at: string
  realized_pnl: string
  holding_sessions: number
}
export interface Result {
  metrics: Record<string, number | string | null | number[]>
  equity: Equity[]
  orders: Order[]
  trades: Trade[]
  warnings: string[]
  signals: {
    timestamp: string
    symbol: string
    action: string
    rule: Condition
    condition_result: boolean | null
  }[]
  benchmark: { metrics: Record<string, number | string | null>; equity: Equity[] }
  positions: Record<string, { quantity: string; cost_basis: string }>
  ledger: Record<string, string>[]
}
export interface Experiment {
  id: string
  name: string
  dataset_id: string
  created_at: string
}
export const defaultStrategy: StrategyConfig = {
  schema_version: 1,
  entry: { type: 'always', value: true },
  exit: { type: 'always', value: false },
  sizing: { mode: 'equity_percent', value: '0.1' },
  risk: { max_allocation: '1', max_positions: 5, stop_loss: null, take_profit: null },
}
export function crossover(fast = 20, slow = 50): StrategyConfig {
  return {
    ...structuredClone(defaultStrategy),
    entry: {
      type: 'compare',
      op: 'crosses_above',
      left: { type: 'indicator', name: 'sma', period: fast },
      right: { type: 'indicator', name: 'sma', period: slow },
    },
    exit: {
      type: 'compare',
      op: 'crosses_below',
      left: { type: 'indicator', name: 'sma', period: fast },
      right: { type: 'indicator', name: 'sma', period: slow },
    },
  }
}
export function rsi(): StrategyConfig {
  return {
    ...structuredClone(defaultStrategy),
    entry: {
      type: 'compare',
      op: 'lt',
      left: { type: 'indicator', name: 'rsi', period: 14 },
      right: { type: 'constant', value: 30 },
    },
    exit: {
      type: 'compare',
      op: 'gt',
      left: { type: 'indicator', name: 'rsi', period: 14 },
      right: { type: 'constant', value: 65 },
    },
  }
}
