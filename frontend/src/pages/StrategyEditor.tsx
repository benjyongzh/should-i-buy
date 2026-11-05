import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Check, Save, Sparkles } from 'lucide-react'
import { api } from '../lib/api'
import { Badge, ErrorBox, Field, PageTitle, Panel } from '../components/ui'
import { RuleEditor } from '../components/RuleEditor'
import { AdvancedStrategyControls } from '../components/AdvancedStrategyControls'
import { TradingControls, defaultTrading } from '../components/TradingControls'
import { crossover, defaultStrategy, rsi } from '../types'
import type { Strategy, StrategyConfig, Version } from '../types'

const formSchema = z.object({
  name: z.string().min(1, 'Give the strategy a name').max(160),
  description: z.string().max(5000),
})
interface Proposal {
  id: string
  config: StrategyConfig
  metadata_json: {
    model: string
    prompt_version: string
    blocked?: boolean
    interpretation?: string
    assumptions?: string[]
    data_requirements?: string[]
    unsupported_requests?: string[]
    capabilities?: unknown
  }
}
export function StrategyEditor() {
  const { id } = useParams()
  const isNew = id === 'new'
  const navigate = useNavigate()
  const qc = useQueryClient()
  const strategy = useQuery({
    queryKey: ['strategy', id],
    queryFn: () => api<Strategy>(`/strategies/${id}`),
    enabled: !isNew,
  })
  const versions = useQuery({
    queryKey: ['strategy-versions', id],
    queryFn: () => api<Version[]>(`/strategies/${id}/versions`),
    enabled: !isNew,
  })
  const [config, setConfig] = useState<StrategyConfig>(structuredClone(defaultStrategy))
  const [text, setText] = useState(JSON.stringify(defaultStrategy, null, 2))
  const [mode, setMode] = useState('visual')
  const [message, setMessage] = useState('')
  const [localError, setLocalError] = useState<unknown>(null)
  const [summary, setSummary] = useState('')
  const [prompt, setPrompt] = useState('')
  const [proposal, setProposal] = useState<Proposal | null>(null)
  const [reviewedProposal, setReviewedProposal] = useState(false)
  const [diff, setDiff] = useState<string[]>([])
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({ resolver: zodResolver(formSchema), defaultValues: { name: '', description: '' } })
  function update(next: StrategyConfig) {
    setConfig(next)
    setText(JSON.stringify(next, null, 2))
    setMessage('')
  }
  useEffect(() => {
    if (strategy.data) {
      reset({ name: strategy.data.name, description: strategy.data.description })
      update(strategy.data.draft)
    }
  }, [strategy.data, reset])
  const operation = useMutation({
    mutationFn: async (task: string) => {
      setLocalError(null)
      setMessage('')
      if (task === 'visual') {
        const v = await api<{ config: StrategyConfig }>(
          '/strategy-definitions/validate',
          'POST',
          JSON.parse(text),
        )
        update(v.config)
        setMode('visual')
        return
      }
      if (task === 'validate') {
        await api('/strategy-definitions/validate', 'POST', JSON.parse(text))
        setMessage('Configuration is valid.')
        return
      }
      if (task === 'publish') {
        if (!strategy.data) throw new Error('Save the draft first')
        const values = JSON.parse(text)
        if (JSON.stringify(values) !== JSON.stringify(strategy.data.draft))
          throw new Error('Save your changes before publishing')
        await api(`/strategies/${id}/publish`, 'POST', {
          expected_revision: strategy.data.draft_revision,
          change_summary: summary,
        })
        setMessage('Published an immutable version.')
        await qc.invalidateQueries()
        return
      }
      if (task === 'propose') {
        if (!strategy.data) throw new Error('Save a draft before using the assistant')
        const p = await api<Proposal>('/llm/plan-strategy', 'POST', { strategy_id: id, prompt })
        setProposal(p)
        setReviewedProposal(false)
        return
      }
      if (task === 'accept') {
        if (!reviewedProposal || proposal?.metadata_json.blocked)
          throw new Error('Review a supported interpretation before accepting')
        await api(`/llm/proposals/${proposal!.id}/accept`, 'POST')
        setProposal(null)
        await qc.invalidateQueries()
        setMessage('Proposal accepted into the draft. Review it before publishing.')
        return
      }
    },
    onError: setLocalError,
  })
  const save = useMutation({
    mutationFn: async (values: { name: string; description: string }) => {
      const payload = { ...values, config: JSON.parse(text) }
      return isNew
        ? api<Strategy>('/strategies', 'POST', payload)
        : api<Strategy>(`/strategies/${id}`, 'PATCH', {
            ...payload,
            expected_revision: strategy.data?.draft_revision,
          })
    },
    onSuccess: async (s) => {
      qc.setQueryData(['strategy', s.id], s)
      await qc.invalidateQueries()
      setMessage('Working draft saved.')
      if (isNew) navigate(`/strategies/${s.id}`, { replace: true })
    },
  })
  const restore = useMutation({
    mutationFn: (versionId: string) => api(`/strategy-versions/${versionId}/clone`, 'POST'),
    onSuccess: async () => {
      await qc.invalidateQueries()
      setMessage('Version copied to your working draft.')
    },
  })
  const error = localError || save.error || strategy.error || restore.error
  return (
    <>
      <PageTitle
        eyebrow="STRATEGY WORKBENCH"
        title={isNew ? 'Define your hypothesis.' : strategy.data?.name || 'Loading strategy…'}
        description="Configure the rules. Validate the definition. Publish when you are ready."
        action={
          !isNew && (
            <Badge
              value={
                strategy.data?.archived
                  ? 'archived'
                  : `draft r${strategy.data?.draft_revision || 1}`
              }
            />
          )
        }
      />
      <ErrorBox error={error} />
      {message && (
        <div className="success" role="status">
          <Check size={17} />
          {message}
        </div>
      )}
      <form onSubmit={handleSubmit((v) => save.mutate(v))}>
        <div className="editor-layout">
          <div>
            <Panel title="Strategy identity">
              <div className="form-grid">
                <Field label="Strategy name">
                  <input {...register('name')} placeholder="e.g. Momentum crossover" />
                  {errors.name && (
                    <small role="alert" className="invalid">
                      {errors.name.message}
                    </small>
                  )}
                </Field>
                <Field label="Description">
                  <input
                    {...register('description')}
                    placeholder="What is this strategy testing?"
                  />
                </Field>
              </div>
            </Panel>
            <Panel
              title="Trading rules"
              action={
                <div className="segmented">
                  <button
                    type="button"
                    className={mode === 'visual' ? 'selected' : ''}
                    onClick={() => operation.mutate('visual')}
                  >
                    Visual
                  </button>
                  <button
                    type="button"
                    className={mode === 'json' ? 'selected' : ''}
                    onClick={() => setMode('json')}
                  >
                    JSON
                  </button>
                </div>
              }
            >
              <div className="template-row">
                <span className="muted">Start with</span>
                {[
                  ['Buy & hold', defaultStrategy],
                  ['MA crossover', crossover()],
                  ['RSI reversal', rsi()],
                ].map(([name, c]) => (
                  <button
                    type="button"
                    key={String(name)}
                    className="chip"
                    onClick={() => update(structuredClone(c as StrategyConfig))}
                  >
                    {String(name)}
                  </button>
                ))}
              </div>
              {mode === 'json' ? (
                <textarea
                  className="code-editor"
                  aria-label="Strategy JSON"
                  spellCheck={false}
                  value={text}
                  onChange={(e) => {
                    setText(e.target.value)
                    setMessage('')
                  }}
                />
              ) : (
                <>
                  <div className="rule-heading">
                    <span className="signal-dot buy" />
                    <h3>Entry condition</h3>
                    <small>Buy or rebalance when the entry rule and schedule permit</small>
                  </div>
                  <RuleEditor
                    value={config.entry}
                    onChange={(entry) => update({ ...config, entry })}
                  />
                  <div className="rule-heading">
                    <span className="signal-dot sell" />
                    <h3>Exit condition</h3>
                    <small>
                      Sell the configured fraction when the exit rule and schedule permit
                    </small>
                  </div>
                  <RuleEditor
                    value={config.exit}
                    onChange={(exit) => update({ ...config, exit })}
                  />
                  <TradingControls config={config} onChange={update} />
                  <h3 className="subheading">Position sizing & risk</h3>
                  <div className="form-grid">
                    <Field label="Sizing method">
                      <select
                        value={config.sizing.mode}
                        onChange={(e) =>
                          update({
                            ...config,
                            ...(['cash_percent', 'target_allocation'].includes(e.target.value) &&
                            !config.trading
                              ? { trading: { ...defaultTrading } }
                              : {}),
                            sizing: {
                              ...config.sizing,
                              mode: e.target.value as StrategyConfig['sizing']['mode'],
                              value:
                                e.target.value === 'fixed_notional'
                                  ? config.sizing.value
                                  : Math.min(1, Number(config.sizing.value)),
                            },
                          })
                        }
                      >
                        <option value="equity_percent">Fraction of portfolio equity</option>
                        <option value="fixed_notional">Fixed account-currency notional</option>
                        <option value="cash_percent">Fraction of available cash</option>
                        <option value="target_allocation">Target allocation — buy or trim</option>
                      </select>
                    </Field>
                    <Field
                      label="Sizing value"
                      hint="Fractions: 0.10 means 10%. Fixed notional is an order budget including costs."
                    >
                      <input
                        type="number"
                        step="any"
                        value={config.sizing.value}
                        onChange={(e) =>
                          update({ ...config, sizing: { ...config.sizing, value: e.target.value } })
                        }
                      />
                    </Field>
                    <Field label="Maximum asset allocation (fraction)">
                      <input
                        type="number"
                        min="0"
                        max="1"
                        step="0.01"
                        value={config.risk.max_allocation}
                        onChange={(e) =>
                          update({
                            ...config,
                            risk: { ...config.risk, max_allocation: e.target.value },
                          })
                        }
                      />
                    </Field>
                    <Field label="Maximum positions">
                      <input
                        type="number"
                        min={1}
                        max={100}
                        value={config.risk.max_positions}
                        onChange={(e) =>
                          update({
                            ...config,
                            risk: { ...config.risk, max_positions: Number(e.target.value) },
                          })
                        }
                      />
                    </Field>
                    {(['stop_loss', 'take_profit'] as const).map((k) => (
                      <Field
                        key={k}
                        label={
                          k === 'stop_loss'
                            ? 'Stop loss (fraction, optional)'
                            : 'Take profit (fraction, optional)'
                        }
                        hint="0.03 means 3%; leave blank to disable"
                      >
                        <input
                          type="number"
                          min={0}
                          max={1}
                          step="0.01"
                          value={config.risk[k] ?? ''}
                          onChange={(e) =>
                            update({
                              ...config,
                              risk: {
                                ...config.risk,
                                [k]: e.target.value === '' ? null : e.target.value,
                              },
                            })
                          }
                        />
                      </Field>
                    ))}
                  </div>
                  <AdvancedStrategyControls config={config} onChange={update} />
                </>
              )}
              <div className="notice">
                Signals use completed observations available at the decision clock. Orders wait for
                a strictly later eligible open. Intraday timing needs intraday data. Stop-first
                protection is conservative when an interval's price path is ambiguous.
              </div>
            </Panel>
            <div className="sticky-actions">
              <button
                type="button"
                className="secondary"
                disabled={operation.isPending}
                onClick={() => operation.mutate('validate')}
              >
                <Check size={16} /> Validate
              </button>
              <button className="button" type="submit" disabled={save.isPending}>
                <Save size={16} />
                {save.isPending ? 'Saving…' : 'Save draft'}
              </button>
              {!isNew && (
                <button
                  type="button"
                  className="secondary"
                  disabled={operation.isPending}
                  onClick={() => operation.mutate('publish')}
                >
                  Publish new version
                </button>
              )}
            </div>
          </div>
          <aside>
            <Panel title="Publish a version">
              <p className="muted">
                A published version is a permanent research input. Future edits stay in the draft.
              </p>
              <Field label="Change summary">
                <textarea
                  value={summary}
                  onChange={(e) => setSummary(e.target.value)}
                  placeholder="Why are these rules changing?"
                />
              </Field>
            </Panel>
            <Panel title="Version history">
              {versions.data?.length ? (
                <>
                  <div className="version-list">
                    {versions.data.map((v) => (
                      <div key={v.id}>
                        <strong>Version {v.number}</strong>
                        <small>
                          {new Date(v.created_at).toLocaleDateString()} ·{' '}
                          {v.config_hash.slice(0, 8)}
                        </small>
                        <p>{v.change_summary || 'Published definition'}</p>
                        <button
                          type="button"
                          className="link-button"
                          onClick={() => restore.mutate(v.id)}
                        >
                          Use as draft
                        </button>
                        <label className="checkbox">
                          <input
                            type="checkbox"
                            checked={diff.includes(v.id)}
                            onChange={(e) =>
                              setDiff(
                                e.target.checked
                                  ? [...diff.slice(-1), v.id]
                                  : diff.filter((x) => x !== v.id),
                              )
                            }
                          />{' '}
                          Compare definition
                        </label>
                      </div>
                    ))}
                  </div>
                  {diff.length === 2 && (
                    <div className="version-diff">
                      {diff.map((vid) => (
                        <pre key={vid}>
                          {JSON.stringify(versions.data.find((v) => v.id === vid)?.config, null, 2)}
                        </pre>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <p className="muted">Your first published version will appear here.</p>
              )}
            </Panel>
            <Panel title="Strategy assistant" action={<Sparkles size={17} />}>
              <p className="muted">
                Describe a change to your saved draft. Review the proposed JSON before accepting it.
              </p>
              <textarea
                aria-label="Strategy assistant prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Only enter when RSI is below 65…"
              />
              <button
                type="button"
                className="secondary full"
                disabled={isNew || !prompt || operation.isPending}
                onClick={() => operation.mutate('propose')}
              >
                {operation.isPending ? 'Working…' : 'Propose changes'}
              </button>
              {isNew && <small>Save the draft to enable the assistant.</small>}
              {proposal && (
                <div className="proposal">
                  <Badge value="proposal" />
                  <small>
                    {proposal.metadata_json.model} · {proposal.metadata_json.prompt_version}
                  </small>
                  <p>{proposal.metadata_json.interpretation}</p>
                  {(['assumptions', 'data_requirements', 'unsupported_requests'] as const).map(
                    (key) =>
                      proposal.metadata_json[key]?.length ? (
                        <div key={key}>
                          <strong>{key.replaceAll('_', ' ')}</strong>
                          <ul>
                            {proposal.metadata_json[key]!.map((value, i) => (
                              <li key={i}>{value}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null,
                  )}
                  {proposal.metadata_json.blocked && (
                    <p role="alert" className="warning">
                      This request contains unsupported requirements and cannot be accepted. Revise
                      the request.
                    </p>
                  )}
                  <details open>
                    <summary>Current → proposed definition</summary>
                    <pre>
                      {JSON.stringify(
                        { current: strategy.data?.draft, proposed: proposal.config },
                        null,
                        2,
                      )}
                    </pre>
                  </details>
                  <label className="checkbox">
                    <input
                      type="checkbox"
                      checked={reviewedProposal}
                      onChange={(e) => setReviewedProposal(e.target.checked)}
                    />{' '}
                    I reviewed the interpretation, data requirements and proposed rules.
                  </label>
                  <button
                    type="button"
                    className="button"
                    disabled={!reviewedProposal || !!proposal.metadata_json.blocked}
                    onClick={() => operation.mutate('accept')}
                  >
                    Accept into draft
                  </button>
                  <button type="button" className="link-button" onClick={() => setProposal(null)}>
                    Reject
                  </button>
                </div>
              )}
            </Panel>
          </aside>
        </div>
      </form>
    </>
  )
}
