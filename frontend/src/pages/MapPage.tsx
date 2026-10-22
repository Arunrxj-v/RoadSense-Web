import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AppHeader } from '../components/AppHeader'
import { AppFooter } from '../components/AppFooter'
import { Icon } from '../components/Icon'
import { MapView, type FlyTarget, type MapApi } from '../components/MapView'
import { PincodeSearch } from '../components/PincodeSearch'
import { PotholeCard } from '../components/PotholeCard'
import { useDocumentMeta } from '../hooks/useDocumentMeta'
import { useMapPotholes, usePotholeDetail } from '../hooks/useServerData'
import { matchesPeriodDate, type Period } from '../lib/time'
import type { GeocodeResult, MapViewport, PotholeSummary } from '../lib/types'

const DEFAULT_LAT = Number(import.meta.env.VITE_MAP_DEFAULT_LAT || 8.8932)
const DEFAULT_LNG = Number(import.meta.env.VITE_MAP_DEFAULT_LNG || 76.6141)
const DEFAULT_ZOOM = Number(import.meta.env.VITE_MAP_DEFAULT_ZOOM || 14)

const periodOptions: { key: Period; label: string }[] = [
  { key: 'all', label: 'All detections' },
  { key: 'today', label: 'Today' },
  { key: '7d', label: 'Last 7 days' },
  { key: '30d', label: 'Last 30 days' },
]

function validLatitude(value: number): boolean {
  return Number.isFinite(value) && value >= -90 && value <= 90
}

function validLongitude(value: number): boolean {
  return Number.isFinite(value) && value >= -180 && value <= 180
}

function parseNumber(value: string | null, fallback: number): number {
  if (value === null) return fallback
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

export function MapPage() {
  useDocumentMeta({
    title: 'RoadSense — Public road condition map',
    description:
      'Explore potholes recorded by RoadSense road-monitoring vehicles. Search any Indian PIN code and inspect road condition records on the map.',
  })

  const [searchParams, setSearchParams] = useSearchParams()

  const [initialCenter] = useState(() => {
    const lat = parseNumber(searchParams.get('lat'), DEFAULT_LAT)
    const lng = parseNumber(searchParams.get('lng'), DEFAULT_LNG)
    const zoom = Math.min(19, Math.max(4, parseNumber(searchParams.get('zoom'), DEFAULT_ZOOM)))
    return {
      latitude: validLatitude(lat) ? lat : DEFAULT_LAT,
      longitude: validLongitude(lng) ? lng : DEFAULT_LNG,
      zoom,
    }
  })
  const [hadInitialCoordinates] = useState(
    () => Boolean(searchParams.get('lat') && searchParams.get('lng')),
  )

  const [initialPotholeId] = useState(() => {
    const id = searchParams.get('pothole')
    return id && /^PH-?\d+$/i.test(id) ? id : null
  })
  const [selectedId, setSelectedId] = useState<string | null>(initialPotholeId)
  const [flyTarget, setFlyTarget] = useState<FlyTarget | null>(null)
  const [period, setPeriod] = useState<Period>('all')
  const [basemapError, setBasemapError] = useState<string | null>(null)
  const [deepLinkFlown, setDeepLinkFlown] = useState(false)
  const [initialFitDone, setInitialFitDone] = useState(false)
  const [fitPotholesNonce, setFitPotholesNonce] = useState(0)
  const mapApiRef = useRef<MapApi | null>(null)

  const { potholes, loading, initialLoading, error, total, retry } =
    useMapPotholes()
  const detail = usePotholeDetail(selectedId)
  const detailAsSummary = useMemo<PotholeSummary | null>(() => {
    if (!detail.data) return null
    const item = detail.data
    return {
      id: item.id,
      latitude: item.latitude,
      longitude: item.longitude,
      report_count: item.report_count,
      confidence: item.confidence,
      severity: item.severity,
      status: item.status,
      first_detected_at: item.first_detected_at,
      last_detected_at: item.last_detected_at,
      road: item.road,
    }
  }, [detail.data])

  const mapPotholes = useMemo(() => {
    if (!detailAsSummary) return potholes
    if (potholes.some((item) => item.id === detailAsSummary.id)) return potholes
    return [...potholes, detailAsSummary]
  }, [potholes, detailAsSummary])

  const visiblePotholes = useMemo(
    () => mapPotholes.filter((pothole) => matchesPeriodDate(pothole.last_detected_at, period)),
    [mapPotholes, period],
  )

  const selectedSummary = useMemo(() => {
    if (!selectedId) return null
    if (detailAsSummary?.id === selectedId) return detailAsSummary
    return visiblePotholes.find((item) => item.id === selectedId) ?? null
  }, [selectedId, visiblePotholes, detailAsSummary])

  const writeViewportToUrl = useCallback(
    (next: MapViewport) => {
      setSearchParams(
        (current) => {
          const params = new URLSearchParams(current)
          params.set('lat', next.latitude.toFixed(6))
          params.set('lng', next.longitude.toFixed(6))
          params.set('zoom', String(next.zoom))
          return params
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  const handleViewportChange = useCallback(
    (next: MapViewport) => {
      writeViewportToUrl(next)
    },
    [writeViewportToUrl],
  )

  const handleSelect = useCallback(
    (id: string) => {
      setSelectedId(id)
      setSearchParams(
        (current) => {
          const params = new URLSearchParams(current)
          params.set('pothole', id)
          return params
        },
        { replace: true },
      )
    },
    [setSearchParams],
  )

  const handleClose = useCallback(() => {
    setSelectedId(null)
    setSearchParams(
      (current) => {
        const params = new URLSearchParams(current)
        params.delete('pothole')
        return params
      },
      { replace: true },
    )
  }, [setSearchParams])

  const clearSelectedPothole = useCallback(() => {
    setSelectedId(null)
    setSearchParams(
      (current) => {
        const params = new URLSearchParams(current)
        params.delete('pothole')
        return params
      },
      { replace: true },
    )
  }, [setSearchParams])

  const handleSearchResolved = useCallback(
    (result: GeocodeResult) => {
      clearSelectedPothole()
      setPeriod('all')
      setFlyTarget({
        latitude: result.latitude,
        longitude: result.longitude,
        zoom: 15,
        nonce: Date.now(),
      })
    },
    [clearSelectedPothole],
  )

  const handleLocate = useCallback(
    (latitude: number, longitude: number) => {
      clearSelectedPothole()
      setPeriod('all')
      setFlyTarget({ latitude, longitude, zoom: 16, nonce: Date.now() })
    },
    [clearSelectedPothole],
  )

  useEffect(() => {
    if (!initialPotholeId || hadInitialCoordinates || deepLinkFlown || !detail.data) return
    if (detail.data.id !== initialPotholeId) return
    setFlyTarget({
      latitude: detail.data.latitude,
      longitude: detail.data.longitude,
      zoom: 16,
      nonce: Date.now(),
    })
    setDeepLinkFlown(true)
  }, [detail.data, deepLinkFlown, hadInitialCoordinates, initialPotholeId])

  useEffect(() => {
    if (
      initialFitDone ||
      hadInitialCoordinates ||
      initialPotholeId ||
      flyTarget ||
      initialLoading ||
      loading ||
      error ||
      potholes.length === 0
    ) {
      return
    }
    setInitialFitDone(true)
    setFitPotholesNonce((nonce) => nonce + 1)
  }, [
    error,
    flyTarget,
    hadInitialCoordinates,
    initialFitDone,
    initialLoading,
    initialPotholeId,
    loading,
    potholes.length,
  ])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && selectedId) handleClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [selectedId, handleClose])

  const periodLabel = periodOptions.find((option) => option.key === period)?.label ?? 'All detections'
  const showEmpty = !initialLoading && !loading && !error && visiblePotholes.length === 0
  const emptyTitle =
    potholes.length === 0
      ? 'No canonical potholes are available yet.'
      : `No potholes match “${periodLabel}”.`
  const emptyMessage =
    potholes.length === 0
      ? 'Records will appear here once the public feed has observations.'
      : 'Try a wider time range.'

  return (
    <div className="app-shell">
      <AppHeader active="map" />
      <main id="main-content" className="main-area">
        <div className="map-page">
          <div className="map-stage">
            <MapView
              mapApiRef={mapApiRef}
              potholes={visiblePotholes}
              selectedId={selectedId}
              initialCenter={initialCenter}
              flyTarget={flyTarget}
              fitPotholesNonce={fitPotholesNonce}
              onSelect={handleSelect}
              onViewportChange={handleViewportChange}
              onBasemapError={setBasemapError}
            />

            <div className="map-controls-top">
              <PincodeSearch onResolved={handleSearchResolved} onLocate={handleLocate} />
              <div className="map-filters" role="group" aria-label="Filter potholes by detection time">
                {periodOptions.map((option) => (
                  <button
                    key={option.key}
                    type="button"
                    className="filter-pill"
                    aria-pressed={period === option.key}
                    onClick={() => setPeriod(option.key)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            {initialLoading || loading ? (
              <div className="map-viewport-status" role="status" aria-live="polite">
                <span className="spinner" aria-hidden="true" />
                <span>Loading pothole data…</span>
              </div>
            ) : null}

            {error ? (
              <div className="map-viewport-status map-viewport-status--error" role="alert">
                <Icon name="cloud_off" size={16} />
                <span>{error}</span>
                <button type="button" onClick={retry}>
                  Retry
                </button>
              </div>
            ) : null}

            {basemapError ? (
              <div className="map-viewport-status map-viewport-status--error" role="alert">
                <Icon name="map" size={16} />
                <span>{basemapError}</span>
                <button type="button" onClick={() => setBasemapError(null)}>
                  Dismiss
                </button>
              </div>
            ) : null}

            <div className={`map-zoom-panel${selectedSummary ? ' map-zoom-panel--hidden-mobile' : ''}`}>
              <div className="map-zoom-group">
                <button
                  type="button"
                  aria-label="Zoom in"
                  onClick={() => mapApiRef.current?.zoomIn()}
                >
                  <Icon name="add" size={20} />
                </button>
                <button
                  type="button"
                  aria-label="Zoom out"
                  onClick={() => mapApiRef.current?.zoomOut()}
                >
                  <Icon name="remove" size={20} />
                </button>
              </div>
              <button
                type="button"
                className="map-zoom-single"
                aria-label="Recentre the map on the initial Kerala view"
                onClick={() => mapApiRef.current?.recenter()}
              >
                <Icon name="near_me" size={18} />
              </button>
            </div>

            {showEmpty ? (
              <div className="map-empty" role="status">
                <Icon name="info" size={18} />
                <div>
                  <strong>{emptyTitle}</strong>
                  <span>{emptyMessage}</span>
                </div>
              </div>
            ) : null}

            {selectedSummary ? (
              <PotholeCard pothole={selectedSummary} onClose={handleClose} />
            ) : null}

            {selectedId && detail.isError ? (
              <div className="map-viewport-status map-viewport-status--error" role="alert">
                <Icon name="error" size={16} />
                <span>Pothole details could not be loaded.</span>
                <button type="button" onClick={() => void detail.refetch()}>
                  Retry
                </button>
              </div>
            ) : null}

            <div className="map-data-bar">
              <div className="map-data-bar__note">
                <Icon name="info" size={15} />
                <span>
                  RoadSense shows potholes detected by its monitoring system. Roads without
                  detections may not have been recently observed.
                </span>
              </div>
              <div className="map-data-bar__meta">
                <span>
                  {visiblePotholes.length}
                  {total > potholes.length ? ` of ${total}` : ''}{' '}
                  {visiblePotholes.length === 1 && total <= 1 ? 'record' : 'records'}
                  {' '}in feed
                </span>
                <span>Datum: WGS 84</span>
                <span>Canonical potholes only</span>
              </div>
            </div>
          </div>
          <AppFooter />
        </div>
      </main>
    </div>
  )
}
