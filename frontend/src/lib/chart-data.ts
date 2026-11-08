import type { Equity } from '../types'

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

export function chartData(
  series: EquitySeries[],
  markers: ChartMarker[],
  timeKey: 'date' | 'timestamp',
  drawdown: boolean,
  performance: boolean,
) {
  const dates = new Map<string, Record<string, string | number>>()
  series.forEach((item, index) =>
    item.equity.forEach((point) => {
      const key = timeKey === 'timestamp' ? point.timestamp : point.date
      if (!key) return
      const row = dates.get(key) || { date: key }
      row['s' + index] = drawdown
        ? point.drawdown * 100
        : Number(performance ? (point.performance_equity ?? point.equity) : point.equity)
      dates.set(key, row)
    }),
  )
  const groups = new Map<string, { key: string; kind: string }>()
  // One point-only line per series/kind keeps all marks without a separately
  // registered Recharts ReferenceDot for every decision in a long history.
  for (const marker of markers) {
    const row = dates.get(marker.date)
    const value = row?.['s' + marker.seriesIndex]
    if (!row || typeof value !== 'number' || !Number.isFinite(value)) continue
    const key = `m${marker.seriesIndex}:${marker.kind}`
    row[key] = value
    groups.set(key, { key, kind: marker.kind })
  }
  return {
    dates,
    rows: [...dates.values()].sort((a, b) => String(a.date).localeCompare(String(b.date))),
    markerGroups: [...groups.values()],
  }
}
