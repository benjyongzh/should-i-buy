import type { ReactNode } from 'react'
import { ArrowUpRight, FlaskConical } from 'lucide-react'
import { Link } from 'react-router-dom'

export const money = (value: unknown, currency = 'SGD') =>
  typeof value === 'string' || typeof value === 'number'
    ? new Intl.NumberFormat('en-SG', {
        style: 'currency',
        currency,
        maximumFractionDigits: 2,
      }).format(Number(value))
    : '—'
export const percent = (value: unknown) => {
  const numeric =
    typeof value === 'number'
      ? value
      : typeof value === 'string' && value.trim()
        ? Number(value)
        : NaN
  return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(2)}%` : '—'
}
export const number = (value: unknown) => (typeof value === 'number' ? value.toFixed(2) : '—')
export const short = (value: string) => value.slice(0, 8)
export function Field({
  label,
  children,
  hint,
}: {
  label: string
  children: ReactNode
  hint?: string
}) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  )
}
export function PageTitle({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <header className="page-title">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="muted">{description}</p>
      </div>
      {action}
    </header>
  )
}
export function Empty({
  title,
  text,
  to,
  label,
}: {
  title: string
  text: string
  to?: string
  label?: string
}) {
  return (
    <div className="empty">
      <FlaskConical size={28} />
      <h3>{title}</h3>
      <p>{text}</p>
      {to && (
        <Link className="button" to={to}>
          {label}
          <ArrowUpRight size={16} />
        </Link>
      )}
    </div>
  )
}
export function ErrorBox({ error }: { error: unknown }) {
  return error ? (
    <div role="alert" className="error">
      {error instanceof Error ? error.message : String(error)}
    </div>
  ) : null
}
export function Badge({ value }: { value: string }) {
  return <span className={`badge ${value}`}>{value.replaceAll('_', ' ')}</span>
}
export function Stat({
  label,
  value,
  detail,
}: {
  label: string
  value: ReactNode
  detail?: string
}) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
      {detail && <small>{detail}</small>}
    </div>
  )
}
export function Panel({
  title,
  children,
  action,
}: {
  title: string
  children: ReactNode
  action?: ReactNode
}) {
  return (
    <section className="panel">
      <div className="panel-title">
        <h2>{title}</h2>
        {action}
      </div>
      {children}
    </section>
  )
}
