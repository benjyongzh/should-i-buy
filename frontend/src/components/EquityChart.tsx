import { useState } from 'react'
import {
  CartesianGrid,
  Brush,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  ReferenceDot,
  ReferenceLine,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Equity } from '../types'
const colors = ['#167665', '#b77935', '#6167bd', '#c45064', '#2794a7']
export interface EquitySeries {
  name: string
  equity: Equity[]
  baseline?: boolean
}
export interface ChartMarker {
  date: string
  seriesIndex: number
  kind: string
}
export function EquityChart({
  series,
  drawdown = false,
  markers = [],
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
  const funded = series.some((s) => s.equity.some((r) => r.performance_equity !== undefined))
  const dates = new Map<string, Record<string, string | number>>()
  series.forEach((s, i) =>
    s.equity.forEach((r) => {
      const key = timeKey === 'timestamp' ? r.timestamp : r.date
      if (!key) return
      const row = dates.get(key) || { date: key }
      row['s' + i] = drawdown
        ? r.drawdown * 100
        : Number(performance ? (r.performance_equity ?? r.equity) : r.equity)
      dates.set(key, row)
    }),
  )
  const rows = [...dates.values()].sort((a, b) => String(a.date).localeCompare(String(b.date)))
  let minimum = Infinity,
    maximum = -Infinity
  for (const row of rows)
    for (const [key, value] of Object.entries(row))
      if (key !== 'date' && typeof value === 'number' && Number.isFinite(value)) {
        minimum = Math.min(minimum, value)
        maximum = Math.max(maximum, value)
      }
  const preciseAxis = maximum - minimum < 1000
  const uniqueMarkers = [
    ...new Map(markers.map((m) => [`${m.date}:${m.seriesIndex}:${m.kind}`, m])).values(),
  ]
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
            onClick={(state) => {
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
            {uniqueMarkers.map((marker) => {
              const value = dates.get(marker.date)?.['s' + marker.seriesIndex]
              if (typeof value !== 'number') return null
              return (
                <ReferenceDot
                  key={`${marker.date}:${marker.seriesIndex}:${marker.kind}`}
                  x={marker.date}
                  y={value}
                  r={marker.kind === 'decision' ? 2 : 4}
                  fill={
                    marker.kind === 'buy'
                      ? '#167665'
                      : marker.kind === 'sell'
                        ? '#c45064'
                        : marker.kind === 'decision'
                          ? '#6167bd'
                          : '#b77935'
                  }
                  stroke="#fff"
                  ifOverflow="hidden"
                />
              )
            })}
            {zoom && rows.length > 1 && (
              <Brush dataKey="date" height={24} travellerWidth={8} stroke="#69746e" />
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
