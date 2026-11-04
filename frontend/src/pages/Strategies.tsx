import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, useLab } from '../lib/api'
import { Badge, Empty, ErrorBox, PageTitle } from '../components/ui'
import type { Strategy } from '../types'

export function Strategies() {
  const lab = useLab()
  const [search, setSearch] = useState('')
  const [archived, setArchived] = useState(false)
  const qc = useQueryClient()
  const action = useMutation({
    mutationFn: ({ id, verb }: { id: string; verb: string }) =>
      api<Strategy>(`/strategies/${id}/${verb}`, 'POST'),
    onSuccess: () => qc.invalidateQueries(),
  })
  const rows = lab.strategies.filter(
    (s) => (archived || !s.archived) && s.name.toLowerCase().includes(search.toLowerCase()),
  )
  return (
    <>
      <PageTitle
        eyebrow="STRATEGY LIBRARY"
        title="Ideas, with a version history."
        description="Every published definition stays immutable. Keep exploring in your working draft."
        action={
          <Link className="button" to="/strategies/new">
            <Plus size={16} /> Create strategy
          </Link>
        }
      />
      <ErrorBox error={action.error} />
      <div className="toolbar">
        <label className="search">
          <Search size={17} />
          <input
            placeholder="Search strategies"
            aria-label="Search strategies"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={archived}
            onChange={(e) => setArchived(e.target.checked)}
          />{' '}
          Include archived
        </label>
        <span className="muted">{rows.length} strategies</span>
      </div>
      {rows.length ? (
        <div className="strategy-grid">
          {rows.map((s) => {
            const versions = lab.versions.filter((v) => v.strategy_id === s.id)
            return (
              <article className="strategy-card" key={s.id}>
                <div className="card-top">
                  <span className="strategy-icon">ƒ</span>
                  <Badge
                    value={s.archived ? 'archived' : versions.length ? 'published' : 'draft'}
                  />
                </div>
                <Link to={`/strategies/${s.id}`}>
                  <h2>{s.name}</h2>
                </Link>
                <p>
                  {s.description || 'A declarative daily strategy, ready for your next hypothesis.'}
                </p>
                <div className="strategy-meta">
                  <span>{versions.length} versions</span>
                  <span>Draft r{s.draft_revision}</span>
                </div>
                <div className="card-actions">
                  <Link className="text-link" to={`/strategies/${s.id}`}>
                    Edit strategy ↗
                  </Link>
                  <button
                    className="link-button"
                    disabled={action.isPending}
                    onClick={() => action.mutate({ id: s.id, verb: 'clone' })}
                  >
                    Clone
                  </button>
                  <button
                    className="link-button"
                    disabled={action.isPending}
                    onClick={() =>
                      action.mutate({ id: s.id, verb: s.archived ? 'restore' : 'archive' })
                    }
                  >
                    {s.archived ? 'Restore' : 'Archive'}
                  </button>
                </div>
              </article>
            )
          })}
        </div>
      ) : (
        <Empty
          title="Turn an idea into a testable rule"
          text="Start with buy and hold, a moving-average crossover, or an RSI template, then make it your own."
          to="/strategies/new"
          label="Create your first strategy"
        />
      )}
    </>
  )
}
