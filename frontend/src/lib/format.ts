import type { PotholeSummary, Project, RoadSummary } from './types'

const IST = 'Asia/Kolkata'

export function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDateIST(value: string | null | undefined): string {
  const date = parseDate(value)
  if (!date) return 'Not recorded'
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: IST,
  }).format(date)
}

export function formatTimeIST(value: string | null | undefined): string {
  const date = parseDate(value)
  if (!date) return ''
  return `${new Intl.DateTimeFormat('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
    timeZone: IST,
  }).format(date)} IST`
}

export function formatDateTimeIST(value: string | null | undefined): string {
  const date = parseDate(value)
  if (!date) return 'Not recorded'
  return `${formatDateIST(value)} · ${formatTimeIST(value)}`
}

export function formatCompactDateTimeIST(value: string | null | undefined): string {
  const date = parseDate(value)
  if (!date) return 'Not recorded'
  return `${new Intl.DateTimeFormat('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
    timeZone: IST,
  }).format(date)} IST`
}

export function relativeTime(value: string | null | undefined, now = Date.now()): string {
  const date = parseDate(value)
  if (!date) return 'No observations yet'
  const diffSeconds = Math.max(0, Math.round((now - date.getTime()) / 1000))
  if (diffSeconds < 60) return 'Updated just now'
  const minutes = Math.floor(diffSeconds / 60)
  if (minutes < 60) return `Updated ${minutes} min ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `Updated ${hours} hr${hours === 1 ? '' : 's'} ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `Updated ${days} day${days === 1 ? '' : 's'} ago`
  return `Updated ${formatDateIST(value)}`
}

export function formatCoordinates(latitude: number, longitude: number): string {
  return `${Math.abs(latitude).toFixed(5)}° ${latitude >= 0 ? 'N' : 'S'}, ${Math.abs(
    longitude,
  ).toFixed(5)}° ${longitude >= 0 ? 'E' : 'W'}`
}

export function formatCoordinatesPlain(latitude: number, longitude: number): string {
  return `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`
}

export function confidencePercent(value: number | null): string {
  if (value === null || Number.isNaN(value)) return '—'
  return `${Math.round(value * 100)}%`
}

export function statusLabel(status: string | null | undefined): string {
  switch (status) {
    case 'open':
      return 'Open'
    case 'under_repair':
      return 'Under repair'
    case 'repaired':
      return 'Repaired'
    case 'unknown':
      return 'Status unknown'
    default:
      return status || 'Status unknown'
  }
}

export function severityLabel(severity: string | null | undefined): string {
  switch (severity) {
    case 'severe':
      return 'High severity'
    case 'moderate':
      return 'Moderate severity'
    case 'low':
      return 'Low severity'
    default:
      return 'Severity not recorded'
  }
}

export function locationTitle(pothole: PotholeSummary): string {
  const road = pothole.road
  const location = pothole.location
  if (location?.locality) return location.locality
  if (location?.road_name) return location.road_name
  if (road?.locality) return road.locality
  if (road?.name) return road.name
  if (location?.pincode) return `PIN ${location.pincode}`
  if (road?.pincode) return `PIN ${road.pincode}`
  return 'Unmapped road segment'
}

export function potholeRoadPrimaryLabel(pothole: PotholeSummary): string {
  const location = pothole.location
  if (location?.road_name) {
    return location.road_number
      ? `${location.road_name} (${location.road_number})`
      : location.road_name
  }
  return roadPrimaryLabel(pothole.road)
}

export function potholeRoadSecondaryLabel(pothole: PotholeSummary): string {
  const location = pothole.location
  const parts = [location?.classification, location?.authority].filter(Boolean)
  if (parts.length > 0) return parts.join(' · ')
  if (pothole.road) return roadSecondaryLabel(pothole.road)
  if (location?.status === 'pending') return 'Resolving location metadata…'
  if (location?.status === 'resolved') return 'Road metadata resolved'
  return 'Road metadata not recorded'
}

export function potholePincode(pothole: PotholeSummary): string | null {
  return pothole.location?.pincode || pothole.road?.pincode || null
}

export function roadPrimaryLabel(road: RoadSummary | null): string {
  if (!road) return 'Road information unavailable'
  const name = road.name || road.locality
  const number = road.number ? ` (${road.number})` : ''
  if (name) return `${name}${number}`
  if (road.number) return road.number
  return 'Road information unavailable'
}

export function roadSecondaryLabel(road: RoadSummary | null): string {
  if (!road) return 'No road record is linked to this observation.'
  return [road.classification, road.authority].filter(Boolean).join(' · ') || 'Road metadata not recorded'
}

export function formatDistance(meters: number): string {
  if (!Number.isFinite(meters)) return ''
  if (meters < 1000) return `${Math.round(meters)} m`
  return `${(meters / 1000).toFixed(1)} km`
}

export function bearingLabel(fromLat: number, fromLng: number, toLat: number, toLng: number): string {
  const toRad = (value: number) => (value * Math.PI) / 180
  const toDeg = (value: number) => (value * 180) / Math.PI
  const dLng = toRad(toLng - fromLng)
  const y = Math.sin(dLng) * Math.cos(toRad(toLat))
  const x =
    Math.cos(toRad(fromLat)) * Math.sin(toRad(toLat)) -
    Math.sin(toRad(fromLat)) * Math.cos(toRad(toLat)) * Math.cos(dLng)
  const bearing = (toDeg(Math.atan2(y, x)) + 360) % 360
  const directions = ['north', 'north-east', 'east', 'south-east', 'south', 'south-west', 'west', 'north-west']
  return directions[Math.round(bearing / 45) % 8]
}

export function distanceMeters(
  fromLat: number,
  fromLng: number,
  toLat: number,
  toLng: number,
): number {
  const radius = 6371008.8
  const toRad = (value: number) => (value * Math.PI) / 180
  const phi1 = toRad(fromLat)
  const phi2 = toRad(toLat)
  const dPhi = toRad(toLat - fromLat)
  const dLambda = toRad(toLng - fromLng)
  const a =
    Math.sin(dPhi / 2) ** 2 +
    Math.cos(phi1) * Math.cos(phi2) * Math.sin(dLambda / 2) ** 2
  return 2 * radius * Math.asin(Math.sqrt(Math.min(1, a)))
}

export interface VerificationPresentation {
  label: string
  detail: string
  tone: 'verified' | 'unverified' | 'unknown'
}

export function verificationPresentation(project: Project | null): VerificationPresentation {
  if (!project) {
    return {
      label: 'No record linked',
      detail: 'No source-backed public works record is linked to this road segment.',
      tone: 'unknown',
    }
  }
  switch (project.verification_status) {
    case 'verified':
      return {
        label: 'Verified source-backed record',
        detail: 'The work record below is linked to a cited public source.',
        tone: 'verified',
      }
    case 'unverified':
      return {
        label: 'Unverified match',
        detail:
          'A work record has been matched to this road, but the match has not been confirmed against an authoritative source.',
        tone: 'unverified',
      }
    default:
      return {
        label: 'Verification pending',
        detail: 'Source data has been recorded but has not yet been verified.',
        tone: 'unknown',
      }
  }
}

export function projectReference(project: Project | null): string {
  if (!project) return 'Not available'
  if (project.tender_id) return project.tender_id
  if (project.work_order_ref) return project.work_order_ref
  return 'Not recorded'
}

export function projectYear(project: Project | null): string {
  if (!project) return 'Not recorded'
  return project.work_year ? String(project.work_year) : 'Not recorded'
}

export function potholeIdNumber(id: string): number {
  const numeric = Number(id.replace(/[^0-9]/g, ''))
  return Number.isFinite(numeric) ? numeric : 0
}

export function pluralReports(count: number): string {
  return `${count} ${count === 1 ? 'report' : 'reports'}`
}
