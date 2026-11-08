import { useMemo, useState } from 'react'
import {
  CartesianGrid,
  Brush,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { chartData, type ChartMarker, type EquitySeries } from '../lib/chart-data'
export type { ChartMarker, EquitySeries } from '../lib/chart-data'
const colors = ['#167665', '#b77935', '#6167bd', '#c45064', '#2794a7']
const noMarkers: ChartMarker[] = []
export function EquityChart({
  series,
  drawdown = false,
  markers = noMarkers,
  selectedDate,
  onSelectDate,
  zoom = false,
  timeKey = 'date',
}: {
  series: EquitySeries[]
  drawdown?: boolean
  markers?: ChartMarker[]
  selectedDate?: string
  onSelectDate?: (date: string) => void
  zoom?: boolean
  timeKey?: 'date' | 'timestamp'
}) {
  const [performance, setPerformance] = useState(false)
  const [range, setRange] = useState<{
    domain: string
    startIndex: number
    endIndex: number
  } | null>(null)
  const funded = series.some((s) => s.equity.some((r) => r.performance_equity !== undefined))
  const { dates, rows, markerGroups } = useMemo(
    () => chartData(series, markers, timeKey, drawdown, performance),
    [series, markers, timeKey, drawdown, performance],
  )
  const domain = JSON.stringify(rows.map((row) => row.date))
  const selection = range?.domain === domain ? range : null
  let minimum = Infinity,
    maximum = -Infinity
  for (const row of rows)
    for (const [key, value] of Object.entries(row))
      if (key !== 'date' && typeof value === 'number' && Number.isFinite(value)) {
        minimum = Math.min(minimum, value)
        maximum = Math.max(maximum, value)
      }
  const preciseAxis = maximum - minimum < 1000
  return (
    <>
      {funded && !drawdown && (
        <label className="field">
          <span>Chart measure</span>
          <select
            aria-label="Chart measure"
            value={performance ? 'performance' : 'balance'}
            onChange={(e) => setPerformance(e.target.value === 'performance')}
          >
            <option value="balance">Account balance including deposits</option>
            <option value="performance">Time-weighted performance, deposits excluded</option>
          </select>
          <small>
            Performance is scaled to initial capital. Account balance includes salary deposits.
          </small>
        </label>
      )}
      <div
        className="chart"
        role="img"
        aria-label={
          drawdown
            ? 'Portfolio drawdown chart'
            : performance
              ? 'Time-weighted performance comparison chart'
              : 'Portfolio equity comparison chart'
        }
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={rows}
            margin={{ top: 12, right: 24, bottom: 4, left: 4 }}
            onClick={(state, event) => {
              const target = event?.target
              if (target instanceof Element && target.closest('.recharts-brush')) return
              if (typeof state.activeLabel === 'string' && dates.has(state.activeLabel))
                onSelectDate?.(state.activeLabel)
            }}
          >
            <CartesianGrid stroke="#e8ece9" vertical={false} />
            <XAxis
              dataKey="date"
              minTickGap={55}
              tick={{ fontSize: 11 }}
              tickFormatter={(v) =>
                timeKey === 'date'
                  ? String(v).slice(0, 7)
                  : new Intl.DateTimeFormat('en-US', {
                      timeZone: 'America/New_York',
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    }).format(new Date(String(v)))
              }
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              width={preciseAxis && !drawdown ? 84 : 60}
              tick={{ fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) =>
                drawdown
                  ? `${v}%`
                  : new Intl.NumberFormat('en', {
                      notation: preciseAxis ? 'standard' : 'compact',
                      maximumFractionDigits: 2,
                    }).format(v)
              }
              domain={drawdown ? ['auto', 0] : ['auto', 'auto']}
            />
            <Tooltip
              formatter={(v) =>
                drawdown
                  ? `${Number(v).toFixed(2)}%`
                  : Number(v).toLocaleString('en-SG', { maximumFractionDigits: 2 })
              }
            />
            <Legend iconType="plainline" />
            {selectedDate && dates.has(selectedDate) && (
              <ReferenceLine x={selectedDate} stroke="#69746e" strokeDasharray="3 3" />
            )}
            {markerGroups.map((marker) => (
              <Line
                key={marker.key}
                dataKey={marker.key}
                stroke="none"
                dot={{
                  r: marker.kind === 'decision' ? 2 : 4,
                  fill:
                    marker.kind === 'buy'
                      ? '#167665'
                      : marker.kind === 'sell'
                        ? '#c45064'
                        : marker.kind === 'decision'
                          ? '#6167bd'
                          : '#b77935',
                  stroke: '#fff',
                }}
                activeDot={false}
                legendType="none"
                tooltipType="none"
                isAnimationActive={false}
                connectNulls={false}
              />
            ))}
            {zoom && rows.length > 1 && (
              <Brush
                dataKey="date"
                height={24}
                travellerWidth={8}
                stroke="#69746e"
                startIndex={selection?.startIndex}
                endIndex={selection?.endIndex}
                onChange={({ startIndex, endIndex }) => {
                  if (typeof startIndex === 'number' && typeof endIndex === 'number')
                    setRange({ domain, startIndex, endIndex })
                }}
              />
            )}
            {series.map((s, i) => (
              <Line
                key={i}
                name={s.name}
                dataKey={'s' + i}
                stroke={colors[i % colors.length]}
                strokeWidth={2}
                strokeDasharray={s.baseline ? '5 4' : undefined}
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}
