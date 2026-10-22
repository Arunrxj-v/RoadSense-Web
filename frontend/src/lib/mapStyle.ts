import type {
  LayerSpecification,
  StyleSpecification,
} from 'maplibre-gl'
import type { PotholeFeatureCollection } from './mapData'

type MapProvider = 'maptiler' | 'stadia'

interface MapStyleConfig {
  provider: MapProvider
  label: string
  url: string
  hasKey: boolean
  available: boolean
}

export interface LoadedMapStyle {
  style: StyleSpecification
  basemapAvailable: boolean
  message: string | null
}

export const POTHOLE_SOURCE_ID = 'roadsense-canonical-potholes'
export const POTHOLE_CLUSTER_LAYER = 'roadsense-pothole-clusters'
export const POTHOLE_POINT_LAYER = 'roadsense-pothole-points'
export const POTHOLE_HIT_LAYER = 'roadsense-pothole-hit'

const MAP_TILER_STYLE_URL =
  import.meta.env.VITE_MAPTILER_STYLE_URL?.trim() ||
  'https://api.maptiler.com/maps/streets-v2-light/style.json'
const STADIA_STYLE_URL =
  import.meta.env.VITE_STADIA_STYLE_URL?.trim() ||
  'https://tiles.stadiamaps.com/styles/alidade_smooth.json'

const MAP_TILER_KEY = import.meta.env.VITE_MAPTILER_API_KEY?.trim() || ''
const STADIA_KEY = import.meta.env.VITE_STADIA_API_KEY?.trim() || ''
const REQUESTED_PROVIDER = import.meta.env.VITE_MAP_PROVIDER?.trim().toLowerCase()

export const BASEMAP_ERROR_MESSAGE =
  'The vector basemap could not be loaded. Pothole records remain available; check the map provider key or your connection.'

function isLocalHost(): boolean {
  if (typeof window === 'undefined') return false
  return ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)
}

function chooseProvider(): MapProvider {
  if (REQUESTED_PROVIDER === 'maptiler') return 'maptiler'
  if (REQUESTED_PROVIDER === 'stadia') return 'stadia'
  return MAP_TILER_KEY ? 'maptiler' : 'stadia'
}

function appendKey(url: string, key: string, parameter: string): string {
  if (!key) return url
  const resolved = new URL(url)
  resolved.searchParams.set(parameter, key)
  return resolved.toString()
}

function resolveConfig(): MapStyleConfig {
  const provider = chooseProvider()
  if (provider === 'maptiler') {
    return {
      provider,
      label: 'MapTiler',
      url: appendKey(MAP_TILER_STYLE_URL, MAP_TILER_KEY, 'key'),
      hasKey: Boolean(MAP_TILER_KEY),
      available: Boolean(MAP_TILER_KEY),
    }
  }
  return {
    provider,
    label: 'Stadia Maps',
    url: appendKey(STADIA_STYLE_URL, STADIA_KEY, 'api_key'),
    hasKey: Boolean(STADIA_KEY),
    available: Boolean(STADIA_KEY) || isLocalHost(),
  }
}

function firstTextFont(style: StyleSpecification): string[] | undefined {
  for (const layer of style.layers) {
    if (layer.type !== 'symbol') continue
    const font = layer.layout?.['text-font']
    if (
      Array.isArray(font) &&
      font.length > 0 &&
      font.every((entry) => typeof entry === 'string')
    ) {
      return font as string[]
    }
  }
  return undefined
}

function softenBasemap(style: StyleSpecification): StyleSpecification {
  for (const layer of style.layers) {
    const id = layer.id.toLowerCase()
    const sourceLayer =
      'source-layer' in layer ? (layer['source-layer'] || '').toLowerCase() : ''

    if (layer.type === 'background') {
      layer.paint = { ...layer.paint, 'background-color': '#f3f1ea' }
      continue
    }

    if (layer.type === 'fill') {
      const paint = { ...layer.paint }
      if (sourceLayer === 'water') {
        paint['fill-color'] = '#d7e5e3'
      } else if (sourceLayer === 'park') {
        paint['fill-color'] = '#e3ebdf'
      } else if (sourceLayer === 'landcover') {
        paint['fill-color'] = id.includes('wood') ? '#dfe9db' : '#e9eee5'
      } else if (sourceLayer === 'landuse') {
        paint['fill-color'] = '#f0ede5'
      } else if (sourceLayer === 'building') {
        paint['fill-color'] = '#e6e1d7'
        paint['fill-opacity'] = 0.55
      }
      layer.paint = paint
      continue
    }

    if (layer.type === 'line') {
      const paint = { ...layer.paint }
      if (sourceLayer === 'boundary') {
        paint['line-color'] = '#d7d1c6'
      } else if (sourceLayer === 'waterway') {
        paint['line-color'] = '#d7e5e3'
      } else if (sourceLayer === 'railway') {
        paint['line-color'] = '#d8d2c7'
      } else if (sourceLayer === 'transportation') {
        if (id.includes('casing')) {
          paint['line-color'] = '#faf8f3'
        } else if (id.includes('motorway')) {
          paint['line-color'] = '#dfd2be'
        } else if (id.includes('major')) {
          paint['line-color'] = '#e8ddcb'
        } else if (id.includes('path') || id.includes('service')) {
          paint['line-color'] = '#efe9df'
        } else {
          paint['line-color'] = '#f0e9de'
        }
      }
      layer.paint = paint
      continue
    }

    if (layer.type === 'symbol') {
      if (sourceLayer === 'poi' || id.includes('poi')) {
        layer.layout = { ...layer.layout, visibility: 'none' }
        continue
      }
      layer.paint = {
        ...layer.paint,
        'text-color': '#556170',
        'text-halo-color': '#f7f5ef',
        'text-halo-width': 1.3,
      }
    }
  }
  return style
}

function createFallbackStyle(): StyleSpecification {
  return {
    version: 8,
    name: 'RoadSense fallback',
    sources: {},
    layers: [
      {
        id: 'roadsense-background',
        type: 'background',
        paint: { 'background-color': '#f3f1ea' },
      },
    ],
  }
}

function potholeLayers(font: string[] | undefined): LayerSpecification[] {
  const layers: LayerSpecification[] = [
    {
      id: 'roadsense-pothole-cluster-halo',
      type: 'circle',
      source: POTHOLE_SOURCE_ID,
      filter: ['has', 'point_count'],
      paint: {
        'circle-color': '#e05a2b',
        'circle-opacity': 0.16,
        'circle-radius': ['step', ['get', 'point_count'], 22, 5, 27, 10, 33],
      },
    },
    {
      id: POTHOLE_CLUSTER_LAYER,
      type: 'circle',
      source: POTHOLE_SOURCE_ID,
      filter: ['has', 'point_count'],
      paint: {
        'circle-color': '#1e2631',
        'circle-radius': ['step', ['get', 'point_count'], 16, 5, 20, 10, 24],
        'circle-stroke-color': '#ffffff',
        'circle-stroke-width': 2.5,
        'circle-opacity': 0.96,
      },
    },
    {
      id: 'roadsense-pothole-cluster-count',
      type: 'symbol',
      source: POTHOLE_SOURCE_ID,
      filter: ['has', 'point_count'],
      layout: {
        'text-field': ['get', 'point_count_abbreviated'],
        'text-size': 11,
        'text-allow-overlap': true,
        ...(font ? { 'text-font': font } : {}),
      },
      paint: {
        'text-color': '#ffffff',
      },
    },
    {
      id: 'roadsense-pothole-halo',
      type: 'circle',
      source: POTHOLE_SOURCE_ID,
      filter: ['!', ['has', 'point_count']],
      paint: {
        'circle-color': '#e05a2b',
        'circle-opacity': 0.16,
        'circle-radius': 11,
      },
    },
    {
      id: POTHOLE_POINT_LAYER,
      type: 'circle',
      source: POTHOLE_SOURCE_ID,
      filter: ['!', ['has', 'point_count']],
      paint: {
        'circle-color': '#e05a2b',
        'circle-radius': [
          'case',
          ['boolean', ['feature-state', 'hover'], false],
          9,
          6.5,
        ],
        'circle-stroke-color': '#ffffff',
        'circle-stroke-width': 2,
      },
    },
    {
      id: POTHOLE_HIT_LAYER,
      type: 'circle',
      source: POTHOLE_SOURCE_ID,
      filter: ['!', ['has', 'point_count']],
      paint: {
        'circle-color': '#1b1c1a',
        'circle-opacity': 0.01,
        'circle-radius': 16,
      },
    },
  ]
  return layers
}

export function withPotholeLayers(
  style: StyleSpecification,
  data: PotholeFeatureCollection,
): StyleSpecification {
  const font = firstTextFont(style)
  return {
    ...style,
    sources: {
      ...style.sources,
      [POTHOLE_SOURCE_ID]: {
        type: 'geojson',
        data,
        cluster: true,
        clusterRadius: 52,
        clusterMaxZoom: 15,
        clusterMinPoints: 2,
      },
    },
    layers: [...style.layers, ...potholeLayers(font)],
  }
}

export async function loadMapStyle(signal?: AbortSignal): Promise<LoadedMapStyle> {
  const config = resolveConfig()
  const fallback = (): LoadedMapStyle => ({
    style: createFallbackStyle(),
    basemapAvailable: false,
    message: BASEMAP_ERROR_MESSAGE,
  })

  if (!config.available) {
    return fallback()
  }

  const controller = new AbortController()
  const abortFromParent = () => controller.abort()
  if (signal) {
    if (signal.aborted) controller.abort()
    else signal.addEventListener('abort', abortFromParent)
  }

  let timedOut = false
  const timer = window.setTimeout(() => {
    timedOut = true
    controller.abort()
  }, 12_000)

  try {
    const response = await fetch(config.url, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    })
    if (!response.ok) return fallback()

    const parsed = (await response.json()) as StyleSpecification
    if (!parsed || parsed.version !== 8 || !Array.isArray(parsed.layers)) {
      return fallback()
    }

    return {
      style: softenBasemap(parsed),
      basemapAvailable: true,
      message: null,
    }
  } catch {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError')
    if (timedOut) return fallback()
    return fallback()
  } finally {
    window.clearTimeout(timer)
    signal?.removeEventListener('abort', abortFromParent)
  }
}
