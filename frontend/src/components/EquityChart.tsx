import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Equity } from '../types'
const colors = ['#167665', '#b77935', '#6167bd', '#c45064', '#2794a7']
export function EquityChart({
  series,
  drawdown = false,
}: {
  series: { name: string; equity: Equity[] }[]
  drawdown?: boolean
}) {
  const dates = new Map<string, Record<string, string | number>>()
  series.forEach((s, i) =>
    s.equity.forEach((r) => {
      const row = dates.get(r.date) || { date: r.date }
      row['s' + i] = drawdown ? r.drawdown * 100 : Number(r.equity)
      dates.set(r.date, row)
    }),
  )
  const rows = [...dates.values()].sort((a, b) => String(a.date).localeCompare(String(b.date)))
  return (
    <div
      className="chart"
      role="img"
      aria-label={drawdown ? 'Portfolio drawdown chart' : 'Portfolio equity comparison chart'}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 12, right: 24, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="#e8ece9" vertical={false} />
          <XAxis
            dataKey="date"
            minTickGap={55}
            tick={{ fontSize: 11 }}
            tickFormatter={(v) => String(v).slice(0, 7)}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) =>
              drawdown ? `${v}%` : new Intl.NumberFormat('en', { notation: 'compact' }).format(v)
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
          {series.map((s, i) => (
            <Line
              key={i}
              name={s.name}
              dataKey={'s' + i}
              stroke={colors[i % colors.length]}
              strokeWidth={2}
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
