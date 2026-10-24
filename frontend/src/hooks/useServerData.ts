import { useQuery } from '@tanstack/react-query'
import {
  apiErrorMessage,
  fetchMeta,
  fetchPothole,
  fetchRecentPotholes,
} from '../lib/api'

export function useApiMeta() {
  return useQuery({
    queryKey: ['meta'],
    queryFn: ({ signal }) => fetchMeta(signal),
    staleTime: 60_000,
    refetchInterval: 120_000,
    retry: 1,
  })
}

export function usePotholeDetail(id: string | null) {
  return useQuery({
    queryKey: ['pothole', id],
    queryFn: ({ signal }) => fetchPothole(id as string, signal),
    enabled: Boolean(id),
    staleTime: 30_000,
    refetchInterval: (query) => {
      const data = query.state.data
      if (data?.location?.status === 'pending') return 4_000
      if (data?.research?.status === 'pending' || data?.research?.status === 'running') {
        return 5_000
      }
      return false
    },
    retry: 1,
  })
}

export function useRecentPotholes(params: {
  limit: number
  offset: number
  q?: string
  since?: string
}) {
  return useQuery({
    queryKey: ['recent-potholes', params],
    queryFn: ({ signal }) => fetchRecentPotholes(params, signal),
    placeholderData: (previous) => previous,
    staleTime: 20_000,
    refetchInterval: (query) =>
      query.state.data?.potholes.some(
        (pothole) => pothole.location?.status === 'pending',
      )
        ? 5_000
        : false,
    retry: 1,
  })
}


export function useMapPotholes() {
  const query = useQuery({
    queryKey: ['map-potholes'],
    queryFn: ({ signal }) =>
      fetchRecentPotholes({ limit: 2000, offset: 0 }, signal),
    staleTime: 30_000,
    refetchInterval: (query) =>
      query.state.data?.potholes.some(
        (pothole) => pothole.location?.status === 'pending',
      )
        ? 5_000
        : false,
    retry: 1,
  })

  return {
    potholes: query.data?.potholes ?? [],
    loading: query.isFetching,
    initialLoading: query.isPending,
    error: query.isError ? apiErrorMessage(query.error) : null,
    total: query.data?.meta.total ?? 0,
    retry: () => void query.refetch(),
  }
}
