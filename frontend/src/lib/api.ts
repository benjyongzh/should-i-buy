import { useQueries, useQuery } from '@tanstack/react-query'
import type { Dataset, Experiment, Profile, Result, Run, Strategy, Version } from '../types'

const noStrategies: Strategy[] = []
const noProfiles: Profile[] = []
const noDatasets: Dataset[] = []
const noRuns: Run[] = []
const noExperiments: Experiment[] = []
const noVersions: Version[] = []

export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch('/api' + path, {
    method,
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const payload = await response.json()
  if (!response.ok) {
    const d = payload.detail
    throw new Error(
      typeof d === 'string'
        ? d
        : Array.isArray(d)
          ? d.map((e: { loc: string[]; msg: string }) => `${e.loc.join('.')}: ${e.msg}`).join('\n')
          : d?.message || 'Request failed',
    )
  }
  return payload as T
}
export function useLab() {
  const strategies = useQuery({
    queryKey: ['strategies'],
    queryFn: () => api<Strategy[]>('/strategies'),
  })
  const profiles = useQuery({
    queryKey: ['profiles'],
    queryFn: () => api<Profile[]>('/backtest-profiles'),
  })
  const datasets = useQuery({
    queryKey: ['datasets'],
    queryFn: () => api<Dataset[]>('/market-data/datasets'),
  })
  const runs = useQuery({
    queryKey: ['runs'],
    queryFn: () => api<Run[]>('/backtests'),
    refetchInterval: 2500,
  })
  const experiments = useQuery({
    queryKey: ['experiments'],
    queryFn: () => api<Experiment[]>('/experiments'),
  })
  const versions = useQuery({
    queryKey: ['versions', strategies.data?.map((s) => s.id)],
    enabled: !!strategies.data,
    queryFn: async () =>
      (
        await Promise.all(
          (strategies.data || []).map((s) => api<Version[]>(`/strategies/${s.id}/versions`)),
        )
      ).flat(),
  })
  return {
    strategies: strategies.data || noStrategies,
    profiles: profiles.data || noProfiles,
    datasets: datasets.data || noDatasets,
    runs: runs.data || noRuns,
    experiments: experiments.data || noExperiments,
    versions: versions.data || noVersions,
    loading: [strategies, profiles, datasets, runs].some((q) => q.isPending),
    error: [strategies, profiles, datasets, runs, versions].find((q) => q.error)?.error,
  }
}
export function useResults(runs: Run[]) {
  return useQueries({
    queries: runs
      .filter((r) => r.status === 'completed')
      .map((r) => ({
        queryKey: ['result', r.id],
        queryFn: () => api<Result>(`/backtests/${r.id}/results`),
        staleTime: Infinity,
      })),
  })
}
