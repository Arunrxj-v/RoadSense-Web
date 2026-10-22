import type { FeatureCollection, Point } from 'geojson'
import type { PotholeSummary } from './types'

export interface PotholeFeatureProperties {
  potholeId: string
  reportCount: number
  label: string
}

export type PotholeFeatureCollection = FeatureCollection<
  Point,
  PotholeFeatureProperties
>

function validCoordinate(latitude: number, longitude: number): boolean {
  return (
    Number.isFinite(latitude) &&
    Number.isFinite(longitude) &&
    latitude >= -90 &&
    latitude <= 90 &&
    longitude >= -180 &&
    longitude <= 180
  )
}

export function canonicalPotholesToGeoJSON(
  potholes: PotholeSummary[],
): PotholeFeatureCollection {
  return {
    type: 'FeatureCollection',
    features: potholes
      .filter((pothole) => validCoordinate(pothole.latitude, pothole.longitude))
      .map((pothole) => ({
        type: 'Feature',
        id: pothole.id,
        properties: {
          potholeId: pothole.id,
          reportCount: pothole.report_count,
          label: pothole.road?.locality || pothole.road?.name || pothole.id,
        },
        geometry: {
          type: 'Point',
          coordinates: [pothole.longitude, pothole.latitude],
        },
      })),
  }
}
