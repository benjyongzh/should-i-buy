import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { ContextSnapshot } from '../types'
import { ErrorBox, Field, Panel } from './ui'

export function ContextImport({
  series,
  onSuccess,
}: {
  series: { series_id: string; name: string }[]
  onSuccess: (id: string) => Promise<void>
}) {
  const [seriesId, setSeries] = useState('FEAR_GREED_US')
  const [source, setSource] = useState('')
  const [url, setURL] = useState('')
  const [policy, setPolicy] = useState('')
  const [csv, setCSV] = useState('')
  const [synthetic, setSynthetic] = useState(false)
  const [fileError, setFileError] = useState('')
  const save = useMutation({
    mutationFn: () =>
      api<ContextSnapshot>('/research/context/import-csv', 'POST', {
        series_id: seriesId,
        source,
        source_url: url,
        availability_policy: policy,
        observations_csv: csv,
        synthetic,
      }),
    onSuccess: (row) => onSuccess(row.id),
  })
  return (
    <Panel title="Import a timestamped source CSV">
      <p>
        Fear &amp; Greed requires a permitted historical source with publication timestamps. Import
        creates a viewing-only snapshot; review is separate.
      </p>
      <ErrorBox error={save.error || fileError} />
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate()
        }}
      >
        <Field label="CSV series">
          <select value={seriesId} onChange={(e) => setSeries(e.target.value)}>
            {series.map((s) => (
              <option key={s.series_id} value={s.series_id}>
                {s.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Source name">
          <input
            required
            maxLength={160}
            value={source}
            onChange={(e) => setSource(e.target.value)}
          />
        </Field>
        <Field label="Source URL">
          <input
            required
            type="url"
            maxLength={1000}
            value={url}
            onChange={(e) => setURL(e.target.value)}
          />
        </Field>
        <Field label="Publication availability policy">
          <textarea
            required
            minLength={20}
            maxLength={2000}
            value={policy}
            onChange={(e) => setPolicy(e.target.value)}
          />
        </Field>
        <Field label="CSV file (optional)">
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={async (e) => {
              const file = e.target.files?.[0]
              if (!file) return
              if (file.size > 5_000_000) {
                setFileError('CSV file must be at most 5 MB.')
                return
              }
              try {
                setCSV(await file.text())
                setFileError('')
              } catch {
                setFileError('Unable to read the CSV file.')
              }
            }}
          />
        </Field>
        <Field
          label="Observation CSV"
          hint="observation_date,available_at,value; optional release_date. Use timezone-aware publication timestamps. Blank availability prevents approval."
        >
          <textarea
            required
            maxLength={5_000_000}
            value={csv}
            onChange={(e) => {
              setCSV(e.target.value)
              setFileError('')
            }}
            rows={6}
          />
        </Field>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={synthetic}
            onChange={(e) => setSynthetic(e.target.checked)}
          />
          This is explicitly synthetic fixture data.
        </label>
        <button className="button" disabled={save.isPending || !!fileError}>
          {save.isPending ? 'Validating…' : 'Import viewing-only snapshot'}
        </button>
      </form>
    </Panel>
  )
}
