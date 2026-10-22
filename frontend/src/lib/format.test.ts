import { describe, expect, it } from 'vitest'
import {
  confidencePercent,
  formatCoordinates,
  locationTitle,
  roadPrimaryLabel,
  verificationPresentation,
} from './format'
import type { PotholeSummary, RoadSummary } from './types'

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
