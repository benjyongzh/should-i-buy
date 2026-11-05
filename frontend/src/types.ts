export type Numeric =
  | { type: 'constant'; value: string | number }
  | { type: 'price'; field?: string }
  | { type: 'indicator'; name: string; period: number; field?: string }
  | {
      type: 'macd'
      fast_period: number
      slow_period: number
      signal_period: number
      component: 'line' | 'signal' | 'histogram'
      field?: string
    }
  | { type: 'stochastic'; period: number; smooth_k: number; smooth_d: number; component: 'k' | 'd' }
  | { type: 'external'; series_id: string; max_age_days: number }
  | { type: 'multiply'; left: Numeric; right: Numeric }
  | {
      type: 'arithmetic'
      op: 'add' | 'subtract' | 'divide' | 'min' | 'max'
      left: Numeric
      right: Numeric
    }
  | { type: 'market'; timeframe: 'daily' | 'intraday'; expression: Numeric }
  | {
      type: 'calendar'
      field:
        | 'minutes_after_open'
        | 'minutes_before_close'
        | 'weekday'
        | 'day_of_month'
        | 'month'
        | 'year'
        | 'session_of_month'
    }
  | {
      type: 'portfolio'
      field: 'cash' | 'equity' | 'position_quantity' | 'position_weight' | 'holding_sessions'
    }
  | {
      type: 'corporate_action'
      kind: 'split' | 'dividend'
      window: 'announced_past' | 'effective_next' | 'effective_past'
      days: number
      measure: 'count' | 'sum_value'
    }
  | {
      type: 'event'
      stream_id: string
      categories: string[]
      scope: 'global' | 'symbol' | 'sector'
      measure: 'count' | 'sum_score' | 'latest_score'
      lookback_minutes: number
      access: 'public_only' | 'any_licensed'
      actors: string[]
      value_field:
        | 'score'
        | 'analyst_target_after'
        | 'congress_amount_min'
        | 'congress_amount_max'
        | 'economic_actual'
        | 'economic_surprise'
    }
export type Condition =
  | { type: 'always'; value: boolean }
  | { type: 'compare'; op: string; left: Numeric; right: Numeric }
  | { type: 'all' | 'any'; conditions: Condition[] }
  | { type: 'not'; condition: Condition }
export interface StrategyConfig {
  schema_version: 1
  entry: Condition
  exit: Condition
  sizing: {
    mode: 'equity_percent' | 'fixed_notional' | 'cash_percent' | 'target_allocation'
    value: string | number
  }
  trading?: {
    entry_schedule: 'daily' | 'weekly' | 'monthly' | 'once'
    exit_schedule: 'daily' | 'weekly' | 'monthly'
    allow_additions: boolean
    exit_fraction: string | number
  } | null
  execution_policy?: {
    decision_cadence: 'daily_close' | 'bar_close' | 'event_or_bar'
    default_timeframe: 'daily' | 'intraday'
    entry_window: { start_minutes_after_open: number; end_minutes_before_close: number }
    exit_window: { start_minutes_after_open: number; end_minutes_before_close: number }
    pending_expiry: 'session_close' | 'good_until_cancelled'
  } | null
  universe?: {
    require_membership: boolean
    include_symbols: string[]
    exclude_symbols: string[]
    sectors: string[]
    exclude_sectors: string[]
    prefer_sectors: string[]
    filter: Condition
    rank_by: Numeric | null
    descending: boolean
    top_n: number
    exit_when_ineligible: boolean
  } | null
  sizing_rules?: { when: Condition; sizing: StrategyConfig['sizing']; label: string }[] | null
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
    corporate_actions_reviewed?: boolean
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
    external_input_hash?: string
    strategy_input_hash?: string
    strategy_inputs?: {
      snapshot_id: string
      kind: string
      content_hash: string
      synthetic: boolean
    }[]
    external_inputs?: {
      snapshot_id: string
      series_id: string
      content_hash: string
      synthetic: boolean
    }[]
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
  performance_equity?: string
  external_flow?: string
  timestamp?: string
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
  resolved_at?: string | null
}
export interface CashBenchmark {
  run_id: string
  name: string
  currency: string
  synthetic: boolean
  assumptions: string
  equity: Equity[]
  intraday_equity?: Equity[]
  metrics: Record<string, number | string | null>
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
  universe_decisions?: {
    timestamp: string
    selected: string[]
    candidates: {
      symbol: string
      sector: string | null
      state_available_at: string | null
      filter_result: boolean | null
      rank: string | null
      eligible: boolean
      selected: boolean
    }[]
  }[]
  metrics: Record<string, number | string | null | number[]>
  equity: Equity[]
  intraday_equity?: Equity[]
  expression_catalog?: Record<string, Numeric>
  orders: Order[]
  trades: Trade[]
  warnings: string[]
  signals: {
    timestamp: string
    symbol: string
    action: string
    rule: Condition
    condition_result: boolean | null
    exit_condition_result?: boolean | null
    exit_rule?: Condition
    reason?: string
    selected?: boolean
    sizing_rule?: string
    evaluations?: {
      expression_id: string
      clock: string
      value: string | null
      timeframe?: string
      completed_bars?: number
      last_bar_available_at?: string | null
      events?: {
        event_id: string
        published_at: string
        available_at: string
        category: string
        title: string
        source_url: string
        details?: Record<string, unknown> | null
      }[]
    }[]
    external_inputs?: Record<string, unknown>
  }[]
  benchmark: {
    metrics: Record<string, number | string | null>
    equity: Equity[]
    intraday_equity?: Equity[]
  }
  positions: Record<string, { quantity: string; cost_basis: string }>
  ledger: Record<string, string>[]
}
export interface StrategyInputRevision {
  id: string
  name: string
  kind: 'intraday' | 'universe' | 'events'
  source: string
  source_url: string
  content_hash: string
  synthetic: boolean
  reviewed: boolean
  complete: boolean
  row_count: number
  coverage_start: string
  coverage_end: string
  availability_policy: string
  category_catalog: string[]
  symbols: string[]
  stream_id: string | null
  bar_minutes: number | null
  parent_id: string | null
  parent_hash: string | null
  review_note: string
  access_coverage: 'public_only' | 'any_licensed'
}
export interface StrategyCapabilities {
  engine_version: string
  configured: Record<'alpaca' | 'fred' | 'llm' | 'benzinga', boolean>
  features: string[]
  data_notes: string[]
  limits: Record<string, number>
}
export interface Experiment {
  id: string
  name: string
  dataset_id: string
  created_at: string
}
export interface ContextSnapshot {
  id: string
  series_id: string
  name: string
  content_hash: string
  source: string
  observation_count: number
  missing_omitted: number
  availability_policy: string
  requested_start: string
  requested_end: string
  units: string
  research_only?: boolean
  synthetic?: boolean
  source_snapshot_id?: string
  review_note?: string
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
