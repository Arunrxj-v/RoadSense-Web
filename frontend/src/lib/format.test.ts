import { describe, expect, it } from 'vitest'
import {
  confidencePercent,
  formatCoordinates,
  locationTitle,
  potholePincode,
  potholeRoadPrimaryLabel,
  potholeRoadSecondaryLabel,
  roadPrimaryLabel,
  verificationPresentation,
} from './format'
import type { PotholeLocation, PotholeSummary, RoadSummary } from './types'

const road: RoadSummary = {
  id: 1,
  name: 'MC Road',
  number: 'SH 1',
  locality: 'Chinnakkada',
  pincode: '691001',
  authority: 'Kerala PWD',
  classification: 'State Highway',
}

const pothole: PotholeSummary = {
  id: 'PH-000001',
  latitude: 8.893214,
  longitude: 76.614102,
  report_count: 5,
  confidence: 0.944,
  severity: 'severe',
  status: 'open',
  first_detected_at: '2026-10-20T05:00:00Z',
  last_detected_at: '2026-10-21T10:00:00Z',
  road,
}

const resolvedLocation: PotholeLocation = {
  status: 'resolved',
  road_name: 'Engineering College Road',
  road_number: null,
  classification: 'residential',
  locality: 'Chengannur',
  pincode: '689121',
  district: 'Alappuzha',
  state: 'Kerala',
  country: 'India',
  authority: null,
  administrative_area: 'Chengannur',
  suburb: null,
  municipality: null,
  operator: null,
  provider: 'maptiler',
  attribution: 'MapTiler / OpenStreetMap contributors',
  geocoded_at: '2026-10-21T10:05:00Z',
}

describe('public formatting helpers', () => {
  it('formats coordinates without inventing precision', () => {
    expect(formatCoordinates(8.893214, 76.614102)).toBe('8.89321° N, 76.61410° E')
  })

  it('formats a confidence ratio as a percentage', () => {
    expect(confidencePercent(0.944)).toBe('94%')
    expect(confidencePercent(null)).toBe('—')
  })

  it('prefers locality, then road name, for a location title', () => {
    expect(locationTitle(pothole)).toBe('Chinnakkada')
    expect(locationTitle({ ...pothole, road: { ...road, locality: null } })).toBe('MC Road')
    expect(locationTitle({ ...pothole, road: null })).toBe('Unmapped road segment')
  })

  it('prefers cached reverse-geocoded metadata when present', () => {
    const resolved = { ...pothole, location: resolvedLocation }
    expect(locationTitle(resolved)).toBe('Chengannur')
    expect(potholeRoadPrimaryLabel(resolved)).toBe('Engineering College Road')
    expect(potholeRoadSecondaryLabel(resolved)).toBe('residential')
    expect(potholePincode(resolved)).toBe('689121')
  })

  it('shows a resolving state without inventing road fields', () => {
    const pending: PotholeSummary = {
      ...pothole,
      road: null,
      location: {
        ...resolvedLocation,
        status: 'pending',
        road_name: null,
        classification: null,
        locality: null,
        pincode: null,
        district: null,
        state: null,
        country: null,
        administrative_area: null,
        provider: null,
        attribution: null,
        geocoded_at: null,
      },
    }
    expect(locationTitle(pending)).toBe('Unmapped road segment')
    expect(potholeRoadPrimaryLabel(pending)).toBe('Road information unavailable')
    expect(potholeRoadSecondaryLabel(pending)).toBe('Resolving location metadata…')
    expect(potholePincode(pending)).toBeNull()
  })

  it('combines road name and number for the ledger', () => {
    expect(roadPrimaryLabel(road)).toBe('MC Road (SH 1)')
    expect(roadPrimaryLabel(null)).toBe('Road information unavailable')
  })

  it('maps project verification status to a provenance label', () => {
    expect(verificationPresentation(null).tone).toBe('unknown')
    expect(
      verificationPresentation({
        name: 'Work record',
        tender_id: null,
        work_order_ref: null,
        authority: null,
        contractor: null,
        work_year: 2025,
        awarded_at: null,
        source_name: null,
        source_url: null,
        verification_status: 'verified',
      }).tone,
    ).toBe('verified')
    expect(
      verificationPresentation({
        name: 'Work record',
        tender_id: null,
        work_order_ref: null,
        authority: null,
        contractor: null,
        work_year: 2025,
        awarded_at: null,
        source_name: null,
        source_url: null,
        verification_status: 'unverified',
      }).tone,
    ).toBe('unverified')
  })
})
