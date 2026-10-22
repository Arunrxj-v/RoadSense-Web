import { useEffect, useRef, useState } from 'react'
import {
  AttributionControl,
  LngLatBounds,
  Map as MapLibreMap,
  Marker,
  ScaleControl,
  type GeoJSONSource,
} from 'maplibre-gl'
import { canonicalPotholesToGeoJSON } from '../lib/mapData'
import {
  BASEMAP_ERROR_MESSAGE,
  loadMapStyle,
  POTHOLE_CLUSTER_LAYER,
  POTHOLE_HIT_LAYER,
  POTHOLE_SOURCE_ID,
  withPotholeLayers,
} from '../lib/mapStyle'
import type { MapViewport, PotholeSummary } from '../lib/types'

export interface FlyTarget {
  latitude: number
  longitude: number
  zoom: number
  nonce: number
}

export interface MapApi {
  zoomIn: () => void
  zoomOut: () => void
  recenter: () => void
}

interface MapViewProps {
  mapApiRef?: { current: MapApi | null }
  potholes: PotholeSummary[]
  selectedId: string | null
  initialCenter: { latitude: number; longitude: number; zoom: number }
  flyTarget: FlyTarget | null
  fitPotholesNonce?: number
  onSelect: (id: string) => void
  onViewportChange: (viewport: MapViewport) => void
  onBasemapError: (message: string) => void
}

function setSourceData(map: MapLibreMap, potholes: PotholeSummary[]): void {
  const source = map.getSource(POTHOLE_SOURCE_ID) as GeoJSONSource | undefined
  source?.setData(canonicalPotholesToGeoJSON(potholes))
}

function viewportOf(map: MapLibreMap): MapViewport {
  const center = map.getCenter()
  const bounds = map.getBounds()
  return {
    latitude: center.lat,
    longitude: center.lng,
    zoom: map.getZoom(),
    bbox: {
      minLat: bounds.getSouth(),
      minLng: bounds.getWest(),
      maxLat: bounds.getNorth(),
      maxLng: bounds.getEast(),
    },
  }
}

export function MapView({
  mapApiRef,
  potholes,
  selectedId,
  initialCenter,
  flyTarget,
  fitPotholesNonce = 0,
  onSelect,
  onViewportChange,
  onBasemapError,
}: MapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const selectedMarkerRef = useRef<Marker | null>(null)
  const dataRef = useRef<PotholeSummary[]>(potholes)
  const selectedRef = useRef<string | null>(selectedId)
  const onSelectRef = useRef(onSelect)
  const onViewportRef = useRef(onViewportChange)
  const onBasemapErrorRef = useRef(onBasemapError)
  const [mapReady, setMapReady] = useState(false)

  dataRef.current = potholes
  selectedRef.current = selectedId
  onSelectRef.current = onSelect
  onViewportRef.current = onViewportChange
  onBasemapErrorRef.current = onBasemapError

  useEffect(() => {
    const container = containerRef.current
    if (!container || mapRef.current) return

    const controller = new AbortController()
    let disposed = false

    const init = async () => {
      let loaded
      try {
        loaded = await loadMapStyle(controller.signal)
      } catch {
        return
      }
      if (disposed || !containerRef.current) return

      let basemapErrorReported = !loaded.basemapAvailable
      if (!loaded.basemapAvailable) {
        onBasemapErrorRef.current(loaded.message ?? BASEMAP_ERROR_MESSAGE)
      }

      const map = new MapLibreMap({
        container,
        style: withPotholeLayers(
          loaded.style,
          canonicalPotholesToGeoJSON(dataRef.current),
        ),
        center: [initialCenter.longitude, initialCenter.latitude],
        zoom: initialCenter.zoom,
        minZoom: 4,
        maxZoom: 19,
        maxPitch: 0,
        dragRotate: false,
        pitchWithRotate: false,
        touchPitch: false,
        attributionControl: false,
        renderWorldCopies: true,
      })
      mapRef.current = map

      map.addControl(new AttributionControl({ compact: true }), 'bottom-right')
      map.addControl(
        new ScaleControl({ unit: 'metric', maxWidth: 80 }),
        'bottom-right',
      )

      const canvas = map.getCanvas()
      canvas.setAttribute(
        'aria-label',
        'Interactive road condition map. Use arrow keys to pan and plus or minus to zoom.',
      )

      const emitViewport = () => {
        onViewportRef.current(viewportOf(map))
      }

      if (mapApiRef) {
        mapApiRef.current = {
          zoomIn: () => map.zoomIn({ duration: 220 }),
          zoomOut: () => map.zoomOut({ duration: 220 }),
          recenter: () =>
            map.flyTo({
              center: [initialCenter.longitude, initialCenter.latitude],
              zoom: initialCenter.zoom,
              duration: 900,
            }),
        }
      }

      map.on('load', () => {
        setSourceData(map, dataRef.current)
        setMapReady(true)
        emitViewport()
      })
      map.on('moveend', emitViewport)
      map.on('error', () => {
        if (basemapErrorReported) return
        basemapErrorReported = true
        onBasemapErrorRef.current(BASEMAP_ERROR_MESSAGE)
      })

      map.on('click', POTHOLE_HIT_LAYER, (event) => {
        const potholeId = event.features?.[0]?.properties?.potholeId
        if (typeof potholeId === 'string') onSelectRef.current(potholeId)
      })
      map.on('click', POTHOLE_CLUSTER_LAYER, (event) => {
        const feature = event.features?.[0]
        const clusterId = feature?.properties?.cluster_id
        const geometry = feature?.geometry
        if (typeof clusterId !== 'number' || geometry?.type !== 'Point') return
        const source = map.getSource(POTHOLE_SOURCE_ID) as GeoJSONSource
        void source
          .getClusterExpansionZoom(clusterId)
          .then((zoom) => {
            map.easeTo({
              center: geometry.coordinates as [number, number],
              zoom: Math.min(zoom, 18),
              duration: 550,
            })
          })
          .catch(() => undefined)
      })

      let hoveredId: string | number | null = null
      map.on('mousemove', POTHOLE_HIT_LAYER, (event) => {
        const feature = event.features?.[0]
        if (hoveredId !== null) {
          map.setFeatureState(
            { source: POTHOLE_SOURCE_ID, id: hoveredId },
            { hover: false },
          )
        }
        hoveredId = feature?.id ?? null
        if (hoveredId !== null) {
          map.setFeatureState(
            { source: POTHOLE_SOURCE_ID, id: hoveredId },
            { hover: true },
          )
        }
        map.getCanvas().style.cursor = 'pointer'
      })
      map.on('mouseleave', POTHOLE_HIT_LAYER, () => {
        if (hoveredId !== null) {
          map.setFeatureState(
            { source: POTHOLE_SOURCE_ID, id: hoveredId },
            { hover: false },
          )
          hoveredId = null
        }
        map.getCanvas().style.cursor = ''
      })
      map.on('mouseenter', POTHOLE_CLUSTER_LAYER, () => {
        map.getCanvas().style.cursor = 'pointer'
      })
      map.on('mouseleave', POTHOLE_CLUSTER_LAYER, () => {
        map.getCanvas().style.cursor = ''
      })

      const onResize = () => map.resize()
      window.addEventListener('resize', onResize)
      const resizeObserver =
        typeof ResizeObserver === 'undefined'
          ? null
          : new ResizeObserver(() => map.resize())
      resizeObserver?.observe(container)

      const originalRemove = map.remove.bind(map)
      map.remove = () => {
        window.removeEventListener('resize', onResize)
        resizeObserver?.disconnect()
        if (mapApiRef) mapApiRef.current = null
        originalRemove()
      }
    }

    void init()

    return () => {
      disposed = true
      controller.abort()
      setMapReady(false)
      selectedMarkerRef.current?.remove()
      selectedMarkerRef.current = null
      mapRef.current?.remove()
      mapRef.current = null
    }
  }, [
    initialCenter.latitude,
    initialCenter.longitude,
    initialCenter.zoom,
    mapApiRef,
  ])

  useEffect(() => {
    dataRef.current = potholes
    if (!mapReady || !mapRef.current) return
    setSourceData(mapRef.current, potholes)
  }, [mapReady, potholes])

  useEffect(() => {
    if (!flyTarget || !mapRef.current) return
    mapRef.current.flyTo({
      center: [flyTarget.longitude, flyTarget.latitude],
      zoom: flyTarget.zoom,
      duration: 1_000,
    })
  }, [flyTarget])

  useEffect(() => {
    if (!fitPotholesNonce || !mapReady || !mapRef.current) return
    const features = canonicalPotholesToGeoJSON(dataRef.current).features
    if (features.length === 0) return
    const bounds = new LngLatBounds()
    features.forEach((feature) => {
      bounds.extend(feature.geometry.coordinates as [number, number])
    })
    mapRef.current.fitBounds(bounds, {
      padding: 64,
      maxZoom: 15,
      duration: 900,
    })
  }, [fitPotholesNonce, mapReady])

  useEffect(() => {
    if (!mapReady || !mapRef.current) return
    selectedMarkerRef.current?.remove()
    selectedMarkerRef.current = null

    const selected = selectedId
      ? dataRef.current.find((pothole) => pothole.id === selectedId)
      : null
    if (!selected) return

    const element = document.createElement('button')
    element.type = 'button'
    element.className = 'map-marker-wrap'
    element.title = `Selected pothole ${selected.id}`
    element.setAttribute('aria-label', `Selected pothole ${selected.id}`)
    element.innerHTML = `
      <span class="map-marker map-marker--selected">
        <span class="map-marker__pulse"></span>
        <span class="map-marker__inner"></span>
      </span>`

    const onClick = (event: MouseEvent) => {
      event.stopPropagation()
      onSelectRef.current(selected.id)
    }
    element.addEventListener('click', onClick)

    const marker = new Marker({ element, anchor: 'center' })
      .setLngLat([selected.longitude, selected.latitude])
      .addTo(mapRef.current)
    selectedMarkerRef.current = marker

    return () => {
      element.removeEventListener('click', onClick)
      marker.remove()
      if (selectedMarkerRef.current === marker) {
        selectedMarkerRef.current = null
      }
    }
  }, [mapReady, potholes, selectedId])

  return (
    <div
      ref={containerRef}
      className="map-canvas"
      role="region"
      aria-label="Interactive map of recorded potholes"
    />
  )
}
