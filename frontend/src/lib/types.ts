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

export type LocationStatus = 'pending' | 'resolved' | 'failed' | 'skipped' | string

export interface PotholeLocation {
  status: LocationStatus
  road_name: string | null
  road_number: string | null
  classification: string | null
  locality: string | null
  pincode: string | null
  district: string | null
  state: string | null
  country: string | null
  authority: string | null
  administrative_area: string | null
  suburb: string | null
  municipality: string | null
  operator: string | null
  provider: string | null
  attribution: string | null
  geocoded_at: string | null
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
  location?: PotholeLocation | null
}

export type ResearchStatus = 'none' | 'pending' | 'running' | 'completed' | 'failed' | string
export type ResearchConfidence = 'high' | 'medium' | 'low' | 'none' | string

export interface ContractResearch {
  status: ResearchStatus
  match: boolean | null
  confidence: ResearchConfidence
  contractor: string | null
  work_title: string | null
  authority: string | null
  tender_number: string | null
  work_reference: string | null
  source_url: string | null
  source_title: string | null
  evidence: string | null
  reason: string | null
  researched_at: string | null
}

export interface PotholeDetail extends Omit<PotholeSummary, 'road'> {
  road: RoadDetail | null
  project: Project | null
  research: ContractResearch
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
