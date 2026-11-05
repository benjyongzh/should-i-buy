import { Link, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  ArrowUpRight,
  BookOpen,
  ChartNoAxesCombined,
  Database,
  FlaskConical,
  GitBranch,
  LayoutDashboard,
  PanelLeftClose,
  Settings2,
} from 'lucide-react'
import { api, useLab } from './lib/api'
import { ErrorBox } from './components/ui'
import { Overview } from './pages/Overview'
import { Strategies } from './pages/Strategies'
import { StrategyEditor } from './pages/StrategyEditor'
import { Profiles } from './pages/Profiles'
import { MarketData } from './pages/MarketData'
import { Backtests, NewBacktest } from './pages/Backtests'
import { RunDetails } from './pages/RunDetails'
import { Compare } from './pages/Compare'
import { ContextData } from './pages/ContextData'
import { StrategySources } from './pages/StrategySources'

const nav = [
  ['/', 'Overview', LayoutDashboard],
  ['/strategies', 'Strategies', GitBranch],
  ['/profiles', 'Backtest profiles', Settings2],
  ['/backtests', 'Backtests', Activity],
  ['/compare', 'Compare', ChartNoAxesCombined],
  ['/data', 'Market data', Database],
  ['/context', 'Market context', BookOpen],
  ['/sources', 'Strategy inputs', Database],
] as const
export default function App() {
  const location = useLocation()
  const lab = useLab()
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => api<{ status: string }>('/health'),
    refetchInterval: 30000,
  })
  const active = lab.runs.filter((r) => ['queued', 'running'].includes(r.status)).length
  return (
    <div className="app">
      <aside className="sidebar">
        <Link className="brand" to="/">
          <span className="brand-mark">
            <FlaskConical size={22} />
          </span>
          <span>
            trading<span className="brand-light">lab</span>
            <small>STRATEGY RESEARCH</small>
          </span>
        </Link>
        <div className="workspace-label">
          <span className="workspace-avatar">P</span>
          <div>
            Personal workspace<small>Local research environment</small>
          </div>
          <PanelLeftClose size={14} />
        </div>
        <p className="nav-caption">WORKSPACE</p>
        <nav>
          {nav.map(([to, label, Icon]) => (
            <NavLink key={to} to={to} end={to === '/'}>
              <Icon size={18} />
              <span>{label}</span>
              {to === '/backtests' && active > 0 && <b>{active}</b>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sandbox-note">
            <BookOpen size={18} />
            <strong>Research, with guardrails.</strong>
            <p>Declarative rules. Immutable inputs. No brokerage execution.</p>
            <Link to="/data">
              Inspect your evidence <ArrowUpRight size={13} />
            </Link>
          </div>
          <div className="connection">
            <span className={`dot ${health.isSuccess ? '' : 'offline'}`} />
            <span>{health.isSuccess ? 'Local API connected' : 'API unavailable'}</span>
            <small>v0.1</small>
          </div>
        </div>
      </aside>
      <div className="app-body">
        <div className="topbar">
          <div>
            <span className="muted">Workspace</span>
            <span className="slash">/</span>
            <strong>
              {nav.find(([to]) =>
                to === '/' ? location.pathname === '/' : location.pathname.startsWith(to),
              )?.[1] || 'Research'}
            </strong>
          </div>
          <div className="topbar-right">
            <span className="environment">
              <span className="dot" /> SELF-HOSTED
            </span>
            <span className="avatar">P</span>
          </div>
        </div>
        <main>
          <ErrorBox error={lab.error} />
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/strategies" element={<Strategies />} />
            <Route path="/strategies/:id" element={<StrategyEditor key={location.pathname} />} />
            <Route path="/profiles" element={<Profiles />} />
            <Route path="/data" element={<MarketData />} />
            <Route path="/context" element={<ContextData />} />
            <Route path="/sources" element={<StrategySources />} />
            <Route path="/backtests" element={<Backtests />} />
            <Route path="/backtests/new" element={<NewBacktest />} />
            <Route path="/backtests/:id" element={<RunDetails />} />
            <Route path="/compare" element={<Compare />} />
            <Route
              path="*"
              element={
                <div className="empty">
                  <h1>Page not found</h1>
                  <Link to="/">Return to the overview</Link>
                </div>
              }
            />
          </Routes>
          <footer>
            TRADING LAB{' '}
            <span>Historical research · Explicit assumptions · Reproducible results</span>
            <span>Daily US equities & ETFs</span>
          </footer>
        </main>
      </div>
    </div>
  )
}
