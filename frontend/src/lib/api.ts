import type {
  ApiMeta,
  GeocodeResult,
  NearbyCollection,
  PotholeCollection,
  PotholeDetail,
  PotholeSummary,
} from './types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL?.trim() || '/api/v1').replace(/\/$/, '')

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

interface ApiErrorBody {
  error?: { message?: string } | string
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  externalSignal?: AbortSignal,
): Promise<T> {
  const controller = new AbortController()
  let timedOut = false
  const timer = window.setTimeout(() => {
    timedOut = true
    controller.abort()
  }, 15000)

  const abortFromExternal = () => controller.abort()
  if (externalSignal) {
    if (externalSignal.aborted) controller.abort()
    else externalSignal.addEventListener('abort', abortFromExternal)
  }

  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        Accept: 'application/json',
        ...(options.headers || {}),
      },
      signal: controller.signal,
    })

    if (!response.ok) {
      let message = 'The road condition service could not complete that request.'
      try {
        const body = (await response.json()) as ApiErrorBody
        if (typeof body.error === 'string') message = body.error
        else if (body.error?.message) message = body.error.message
      } catch {
        if (response.status >= 500) {
          message = 'The road condition service is temporarily unavailable.'
        }
      }
      throw new ApiError(message, response.status)
    }

    return (await response.json()) as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      if (timedOut) {
        throw new ApiError('The road condition service took too long to respond.', 408)
      }
      throw error
    }
    throw new ApiError(
      'The road condition service could not be reached. Check your connection and try again.',
      0,
    )
  } finally {
    window.clearTimeout(timer)
    externalSignal?.removeEventListener('abort', abortFromExternal)
  }
}

export async function fetchRecentPotholes(
  params: {
    limit: number
    offset: number
    q?: string
    since?: string
  },
  signal?: AbortSignal,
): Promise<PotholeCollection> {
  const search = new URLSearchParams({
    limit: String(params.limit),
    offset: String(params.offset),
  })
  if (params.q) search.set('q', params.q)
  if (params.since) search.set('since', params.since)
  return apiFetch<PotholeCollection>(`/potholes/recent?${search}`, {}, signal)
}

export async function fetchPothole(
  id: string,
  signal?: AbortSignal,
): Promise<PotholeDetail> {
  return apiFetch<PotholeDetail>(`/potholes/${encodeURIComponent(id)}`, {}, signal)
}

export async function refreshPotholeResearch(
  id: string,
): Promise<{ pothole_id: string; research: PotholeDetail['research'] }> {
  return apiFetch<{ pothole_id: string; research: PotholeDetail['research'] }>(
    `/potholes/${encodeURIComponent(id)}/research`,
    { method: 'POST' },
  )
}

export async function fetchNearby(
  latitude: number,
  longitude: number,
  radiusKm = 2,
  signal?: AbortSignal,
): Promise<NearbyCollection> {
  return apiFetch<NearbyCollection>(
    `/potholes/nearby?lat=${latitude}&lng=${longitude}&radius_km=${radiusKm}&limit=100`,
    {},
    signal,
  )
}

export async function fetchMeta(signal?: AbortSignal): Promise<ApiMeta> {
  return apiFetch<ApiMeta>('/meta', {}, signal)
}

export async function geocodePincode(
  pincode: string,
  signal?: AbortSignal,
): Promise<GeocodeResult> {
  return apiFetch<GeocodeResult>(
    `/geocode?pincode=${encodeURIComponent(pincode)}`,
    {},
    signal,
  )
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

export function apiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error && error.message) return error.message
  return 'Something went wrong. Please try again.'
}

export function potholePath(id: string): string {
  return `/pothole/${encodeURIComponent(id)}`
}

export function potholeMapPath(pothole: PotholeSummary): string {
  const params = new URLSearchParams({
    lat: pothole.latitude.toFixed(6),
    lng: pothole.longitude.toFixed(6),
    zoom: '16',
    pothole: pothole.id,
  })
  return `/?${params.toString()}`
}
