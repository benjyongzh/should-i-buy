import { expect, it } from 'vitest'
import { chartData, type EquitySeries } from './chart-data'

const account = { exposure: '0', unrealized_pnl: '0', realized_pnl: '0' }

it('retains every decision in a full-length history alongside distinct fills', () => {
  const equity = Array.from({ length: 2011 }, (_, i) => ({
    ...account,
    date: new Date(Date.UTC(2018, 0, 1 + i)).toISOString().slice(0, 10),
    equity: String(10000 + i),
    cash: '100',
    drawdown: 0,
  }))
  const markers = equity.map((point) => ({ date: point.date, seriesIndex: 0, kind: 'decision' }))
  markers.push({ date: equity[400].date, seriesIndex: 0, kind: 'buy' })
  const prepared = chartData(
    [{ name: 'SYNTHETIC full history', equity }],
    markers,
    'date',
    false,
    false,
  )
  expect(prepared.rows).toHaveLength(2011)
  expect(prepared.markerGroups).toHaveLength(2)
  for (let i = 0; i < equity.length; i++) {
    expect(prepared.rows[i]['m0:decision']).toBe(Number(equity[i].equity))
    expect(prepared.rows[i].s0).toBe(Number(equity[i].equity))
  }
  expect(prepared.rows[400]['m0:buy']).toBe(10400)
})

it('keeps annotations on their own strategy and plotted financial measure', () => {
  const series: EquitySeries[] = [
    {
      name: 'SYNTHETIC funded',
      equity: [
        {
          ...account,
          date: '2020-01-02',
          equity: '10500',
          performance_equity: '10000',
          cash: '0',
          drawdown: -0.1,
        },
      ],
    },
    {
      name: 'SYNTHETIC other',
      equity: [{ ...account, date: '2020-01-02', equity: '20000', cash: '0', drawdown: -0.2 }],
    },
  ]
  const marks = [0, 1].map((seriesIndex) => ({ date: '2020-01-02', seriesIndex, kind: 'buy' }))
  expect(chartData(series, marks, 'date', false, false).rows[0]['m0:buy']).toBe(10500)
  expect(chartData(series, marks, 'date', false, true).rows[0]).toMatchObject({
    'm0:buy': 10000,
    'm1:buy': 20000,
  })
  expect(chartData(series, marks, 'date', true, false).rows[0]).toMatchObject({
    'm0:buy': -10,
    'm1:buy': -20,
  })
})

it('ignores nonexistent observations and consolidates duplicate marks without changing values', () => {
  const series: EquitySeries[] = [
    {
      name: 'SYNTHETIC',
      equity: [{ ...account, date: '2020-01-02', equity: '10000', cash: '10000', drawdown: 0 }],
    },
  ]
  const mark = { date: '2020-01-02', seriesIndex: 0, kind: 'decision' }
  const data = chartData(
    series,
    [mark, mark, { ...mark, date: '2030-01-01' }, { ...mark, seriesIndex: 9 }],
    'date',
    false,
    false,
  )
  expect(data.rows).toEqual([{ date: '2020-01-02', s0: 10000, 'm0:decision': 10000 }])
  expect(data.markerGroups).toEqual([{ key: 'm0:decision', kind: 'decision' }])
})

it('retains distinct intraday observations on the same session', () => {
  const series: EquitySeries[] = [
    {
      name: 'SYNTHETIC',
      equity: [
        {
          ...account,
          date: '2020-01-02',
          timestamp: '2020-01-02T15:00:00Z',
          equity: '10010',
          cash: '0',
          drawdown: 0,
        },
        {
          ...account,
          date: '2020-01-02',
          timestamp: '2020-01-02T14:35:00Z',
          equity: '10000',
          cash: '0',
          drawdown: 0,
        },
      ],
    },
  ]
  const data = chartData(
    series,
    [{ date: '2020-01-02T15:00:00Z', seriesIndex: 0, kind: 'buy' }],
    'timestamp',
    false,
    false,
  )
  expect(data.rows.map((r) => r.date)).toEqual(['2020-01-02T14:35:00Z', '2020-01-02T15:00:00Z'])
  expect(data.rows[0]['m0:buy']).toBeUndefined()
  expect(data.rows[1]['m0:buy']).toBe(10010)
})
