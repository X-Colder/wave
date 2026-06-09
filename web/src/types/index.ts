export interface OverviewMetrics {
  total_return: number
  annual_return: number
  max_drawdown: number
  sharpe_ratio: number
  win_rate: number
  profit_loss_ratio: number
  total_trades: number
  avg_position: number
  buy_adjustments: number
  sell_adjustments: number
  total_realized_pnl: number
}

export interface EquityPoint {
  date: string
  equity: number
  drawdown: number
}

export interface MonthlyReturn {
  month: string
  return: number
}

export interface OverviewData {
  metrics: OverviewMetrics
  equity_curve: EquityPoint[]
  monthly_returns: MonthlyReturn[]
}

export interface PatternCell {
  f: number
  m: number
  a: number
  fd: number
  md: number
  ad: number
  count: number
  win_rate: number
  avg_return: number
  mfe_mae_ratio: number
  expected_value: number
  median_mfe: number
  median_mae: number
  signal_score: number
}

export interface PatternDetail {
  id: string
  label: string
  count: number
  win_rate: number
  avg_return: number
  mfe_distribution: number[]
  mae_distribution: number[]
}

export interface PatternsData {
  cells: PatternCell[]
  flow_stats?: Record<string, unknown>
}

export interface Trade {
  id: number
  time: string
  action: string
  price: number
  position_before: number
  position_after: number
  position_delta: number
  direction: string
  signal_score: number
  speed: number
  short_slope: number
  long_slope: number
  pnl: number
  pnl_type: string
  return_pct: number
  capital_after: number
  high_after: number | null
  high_after_pct: number | null
  ticks_to_high: number | null
}

export interface TradesStats {
  total_adjustments: number
  buy_count: number
  sell_count: number
  profitable_sells: number
  losing_sells: number
  total_realized_pnl: number
  direction_breakdown: Record<string, { count: number; pnl: number }>
}

export interface TradesData {
  stats: TradesStats
  trades: Trade[]
  total: number
  page: number
  size: number
}

export interface TickPoint {
  time: string
  price: number
  volume: number
}

export interface FeaturePoint {
  time: string
  short_slope: number
  long_slope: number
  direction: string
}

export interface Signal {
  time: string
  price: number
  direction: string
  action: string
  speed?: number
  position?: number
}

export interface IntradayData {
  date: string
  ticks: TickPoint[]
  features: FeaturePoint[]
  signals: Signal[]
}

export interface PageQuery {
  page: number
  size: number
}
