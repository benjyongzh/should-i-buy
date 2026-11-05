import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { api, useLab } from '../lib/api'
import { ErrorBox, Field, PageTitle, Panel, money } from '../components/ui'
import type { Profile, ProfileConfig } from '../types'

const groups: [string, [string, string, string?][]][] = [
  [
    'Capital & period',
    [
      ['starting_capital', 'Starting capital'],
      ['monthly_contribution', 'Monthly contribution (account currency)'],
      ['start_date', 'Start date', 'date'],
      ['end_date', 'End date', 'date'],
    ],
  ],
  [
    'Execution costs',
    [
      ['fixed_fee', 'Fixed fee per executed order'],
      ['commission_pct', 'Percentage commission (fraction)'],
      ['slippage', 'Slippage (fraction)'],
      ['spread', 'Bid-ask spread (fraction)'],
      ['fx_markup', 'FX markup (fraction)'],
    ],
  ],
  [
    'Portfolio constraints',
    [
      ['max_orders_per_day', 'Maximum orders per session'],
      ['max_exposure', 'Maximum exposure (fraction)'],
      ['min_notional', 'Minimum order notional'],
      ['min_holding_sessions', 'Minimum holding sessions'],
      ['max_positions', 'Maximum concurrent positions'],
      ['max_fx_age_days', 'Maximum FX age (days)'],
      ['risk_free_rate', 'Annual risk-free rate (fraction)'],
    ],
  ],
]
export function Profiles() {
  const lab = useLab()
  const defaults = useQuery({
    queryKey: ['profile-defaults'],
    queryFn: () => api<{ name: string; config: ProfileConfig }>('/backtest-profiles/defaults'),
  })
  const [id, setId] = useState('new')
  const [name, setName] = useState('')
  const [config, setConfig] = useState<ProfileConfig>({})
  const [saved, setSaved] = useState(false)
  const qc = useQueryClient()
  useEffect(() => {
    const p = id === 'new' ? defaults.data : lab.profiles.find((p) => p.id === id)
    if (p) {
      setName(p.name)
      setConfig(p.config)
      setSaved(false)
    }
  }, [id, defaults.data, lab.profiles])
  const save = useMutation({
    mutationFn: () =>
      api<Profile>(
        id === 'new' ? '/backtest-profiles' : `/backtest-profiles/${id}`,
        id === 'new' ? 'POST' : 'PATCH',
        { name, config },
      ),
    onSuccess: async (p) => {
      await qc.invalidateQueries({ queryKey: ['profiles'] })
      setId(p.id)
      setSaved(true)
    },
  })
  const clone = useMutation({
    mutationFn: () => api<Profile>(`/backtest-profiles/${id}/clone`, 'POST'),
    onSuccess: async (p) => {
      await qc.invalidateQueries({ queryKey: ['profiles'] })
      setId(p.id)
    },
  })
  function edit(k: string, value: string | boolean | string[]) {
    setConfig({ ...config, [k]: value })
    setSaved(false)
  }
  return (
    <>
      <PageTitle
        eyebrow="SHARED ASSUMPTIONS"
        title="A fair starting point."
        description="Financial conditions belong to the profile. Each run keeps its own immutable snapshot."
        action={
          <button
            className="button"
            onClick={() => {
              setId('new')
              if (defaults.data) {
                setName(defaults.data.name)
                setConfig(defaults.data.config)
              }
            }}
          >
            <Plus size={16} /> New profile
          </button>
        }
      />
      <ErrorBox error={save.error || clone.error || defaults.error} />
      {saved && (
        <div className="success">
          Profile saved. Existing runs retain their original assumptions.
        </div>
      )}
      <div className="profiles-layout">
        <aside className="profile-list">
          {lab.profiles.map((p) => (
            <button
              className={id === p.id ? 'profile-option active' : 'profile-option'}
              key={p.id}
              onClick={() => setId(p.id)}
            >
              <strong>{p.name}</strong>
              <small>
                {money(p.config.starting_capital, String(p.config.account_currency))} ·{' '}
                {money(p.config.fixed_fee, String(p.config.account_currency))} / order
              </small>
            </button>
          ))}
          {!lab.profiles.length && <p className="muted">Create your first reusable profile.</p>}
        </aside>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            save.mutate()
          }}
        >
          <Panel title={id === 'new' ? 'New backtest profile' : 'Edit backtest profile'}>
            <div className="form-grid">
              <Field label="Profile name">
                <input
                  required
                  maxLength={160}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>
              <Field label="Account currency">
                <select
                  value={String(config.account_currency || 'SGD')}
                  onChange={(e) => edit('account_currency', e.target.value)}
                >
                  <option>SGD</option>
                  <option>USD</option>
                </select>
              </Field>
              <Field label="Tradable symbols" hint="Comma-separated, e.g. SPY, AAPL">
                <input
                  required
                  value={Array.isArray(config.symbols) ? config.symbols.join(', ') : ''}
                  onChange={(e) =>
                    edit(
                      'symbols',
                      e.target.value
                        .toUpperCase()
                        .split(',')
                        .map((s) => s.trim()),
                    )
                  }
                />
              </Field>
              <Field label="Benchmark symbol">
                <input
                  required
                  value={String(config.benchmark || '')}
                  onChange={(e) => edit('benchmark', e.target.value.toUpperCase())}
                />
              </Field>
              <Field label="Research designation">
                <select
                  value={String(config.research_label || 'in_sample')}
                  onChange={(e) => edit('research_label', e.target.value)}
                >
                  <option value="in_sample">In-sample research</option>
                  <option value="holdout">Historical holdout</option>
                </select>
              </Field>
              <Field label="Execution interval">
                <select
                  value={String(config.timeframe || '1d')}
                  onChange={(e) => edit('timeframe', e.target.value)}
                >
                  {['1d', '1min', '5min', '15min', '30min', '60min'].map((t) => (
                    <option key={t}>{t}</option>
                  ))}
                </select>
              </Field>
              <Field label="Fractional shares">
                <select
                  value={String(config.fractional_shares || false)}
                  onChange={(e) => edit('fractional_shares', e.target.value === 'true')}
                >
                  <option value="false">Disabled — whole-share orders</option>
                  <option value="true">Enabled — 6 decimal places</option>
                </select>
              </Field>
            </div>
            {groups.map(([title, fields]) => (
              <div key={title}>
                <h3 className="subheading">{title}</h3>
                <div className="form-grid">
                  {fields.map(([k, label, type]) => (
                    <Field key={k} label={label}>
                      <input
                        required
                        type={type || 'number'}
                        step="any"
                        value={String(config[k] ?? (k === 'monthly_contribution' ? '0' : ''))}
                        onChange={(e) => edit(k, e.target.value)}
                      />
                    </Field>
                  ))}
                </div>
              </div>
            ))}
            <div className="notice">
              Monthly contributions arrive at the first XNYS session open of each calendar month; a
              midmonth start receives no retroactive deposit. Zero disables contributions.
              Strategies decide when to invest available cash. XNYS regular sessions · strictly
              later eligible interval open · long-only · no leverage. Intraday profiles require
              complete reviewed interval data. USD/SGD uses historically available rates. Fees and
              contributions are in account currency.
            </div>
            <div className="actions">
              <button className="button" disabled={save.isPending || !config.start_date}>
                Save profile
              </button>
              {id !== 'new' && (
                <button type="button" className="secondary" onClick={() => clone.mutate()}>
                  Clone profile
                </button>
              )}
            </div>
          </Panel>
        </form>
      </div>
    </>
  )
}
