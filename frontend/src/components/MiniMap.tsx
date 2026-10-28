import { useEffect, useRef, useState } from 'react'
import {
  AttributionControl,
  Map as MapLibreMap,
  Marker,
  NavigationControl,
} from 'maplibre-gl'
import { loadMapStyle } from '../lib/mapStyle'
import { useTheme } from '../theme/ThemeContext'

interface MiniMapProps {
  latitude: number
  longitude: number
  label: string
}

export function MiniMap({ latitude, longitude, label }: MiniMapProps) {
  const { theme } = useTheme()
  const mapContainerRef = useRef<HTMLDivElement | null>(null)
  const [basemapUnavailable, setBasemapUnavailable] = useState(false)

  useEffect(() => {
    const container = mapContainerRef.current
    if (!container) return
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return
    setBasemapUnavailable(false)

    const controller = new AbortController()
    let disposed = false
    let map: MapLibreMap | null = null
    let resizeObserver: ResizeObserver | null = null
    let onResize: (() => void) | null = null

    const init = async () => {
      let loaded
      try {
        loaded = await loadMapStyle(theme, controller.signal)
      } catch {
        return
      }
      if (disposed || !mapContainerRef.current) return

      if (!loaded.basemapAvailable) setBasemapUnavailable(true)

      map = new MapLibreMap({
        container: mapContainerRef.current,
        style: loaded.style,
        center: [longitude, latitude],
        zoom: 16,
        minZoom: 8,
        maxZoom: 19,
        maxPitch: 0,
        dragRotate: false,
        pitchWithRotate: false,
        touchPitch: false,
        attributionControl: false,
      })
      map.addControl(
        new NavigationControl({ showCompass: false }),
        'top-left',
      )
      map.addControl(new AttributionControl({ compact: true }), 'bottom-right')

      const markerElement = document.createElement('div')
      markerElement.className = 'map-marker-wrap'
      markerElement.setAttribute('aria-hidden', 'true')
      markerElement.innerHTML = `
        <span class="map-marker map-marker--selected">
          <span class="map-marker__pulse"></span>
          <span class="map-marker__inner"></span>
        </span>`
      const marker = new Marker({
        element: markerElement,
        anchor: 'center',
      }).setLngLat([longitude, latitude])

      map.on('load', () => marker.addTo(map as MapLibreMap))
      map.on('error', () => setBasemapUnavailable(true))

      onResize = () => map?.resize()
      window.addEventListener('resize', onResize)
      if (typeof ResizeObserver !== 'undefined') {
        resizeObserver = new ResizeObserver(() => map?.resize())
        resizeObserver.observe(mapContainerRef.current)
      }
    }

    void init()

    return () => {
      disposed = true
      controller.abort()
      if (onResize) window.removeEventListener('resize', onResize)
      resizeObserver?.disconnect()
      map?.remove()
    }
  }, [latitude, longitude, theme])

  return (
    <div className="inset-map__canvas" aria-label={`Map showing ${label}`}>
      <div ref={mapContainerRef} className="inset-map__map" />
      {basemapUnavailable ? (
        <span className="inset-map__notice">Basemap unavailable</span>
      ) : null}
    </div>
  )
}
