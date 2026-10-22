export type VerificationStatus = 'verified' | 'unverified' | 'unknown' | string

export interface RoadSummary {
  id: number | null
  name: string | null
  number: string | null
  locality: string | null
  pincode: string | null
  authority: string | null
  classification: string | null
}

export interface RoadDetail extends RoadSummary {
  latitude: number | null
  longitude: number | null
  geometry_available: boolean
}

export interface Project {
  name: string | null
  tender_id: string | null
  work_order_ref: string | null
  authority: string | null
  contractor: string | null
  work_year: number | null
  awarded_at: string | null
  source_name: string | null
  source_url: string | null
  verification_status: VerificationStatus
}

export interface PotholeSummary {
  id: string
  latitude: number
  longitude: number
  report_count: number
  confidence: number | null
  severity: string | null
  status: string
  first_detected_at: string
  last_detected_at: string
  road: RoadSummary | null
}

export interface PotholeDetail extends Omit<PotholeSummary, 'road'> {
  road: RoadDetail | null
  project: Project | null
  related: PotholeSummary[]
}

export interface PotholeCollection {
  potholes: PotholeSummary[]
  meta: {
    count: number
    total: number
    limit: number
    offset: number
    bbox?: BoundingBox
    generated_at: string
  }
}

export interface BoundingBox {
  minLat: number
  minLng: number
  maxLat: number
  maxLng: number
}

export interface MapViewport {
  latitude: number
  longitude: number
  zoom: number
  bbox: BoundingBox
}

export interface GeocodeResult {
  pincode: string
  latitude: number
  longitude: number
  display_name: string | null
  source: string
}

export interface ApiMeta {
  pothole_count: number
  latest_detection_at: string | null
  generated_at: string
}

export interface NearbyCollection {
  potholes: (PotholeSummary & { distance_m: number })[]
  meta: {
    count: number
    center: { latitude: number; longitude: number }
    radius_km: number
    generated_at: string
  }
}
