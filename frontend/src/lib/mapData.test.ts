import { describe, expect, it } from 'vitest'
import { canonicalPotholesToGeoJSON } from './mapData'
import type { PotholeSummary } from './types'

function pothole(overrides: Partial<PotholeSummary> = {}): PotholeSummary {
  return {
    id: 'PH-000001',
    latitude: 9.0128,
    longitude: 76.5409,
    report_count: 4,
    confidence: 0.9,
    severity: 'severe',
    status: 'open',
    first_detected_at: '2026-10-21T20:51:08.684000Z',
    last_detected_at: '2026-10-22T10:55:07.200000Z',
    road: null,
    ...overrides,
  }
}

describe('canonicalPotholesToGeoJSON', () => {
  it('uses longitude-latitude order and stable feature properties', () => {
    const result = canonicalPotholesToGeoJSON([
      pothole({
        road: {
          id: 1,
          name: 'Main Road',
          number: null,
          locality: 'Kollam',
          pincode: '691001',
          authority: null,
          classification: null,
        },
      }),
    ])

    expect(result.features).toHaveLength(1)
    expect(result.features[0].id).toBe('PH-000001')
    expect(result.features[0].geometry.coordinates).toEqual([76.5409, 9.0128])
    expect(result.features[0].properties).toEqual({
      potholeId: 'PH-000001',
      reportCount: 4,
      label: 'Kollam',
    })
  })

  it('skips malformed coordinates instead of breaking the map source', () => {
    const result = canonicalPotholesToGeoJSON([
      pothole(),
      pothole({ id: 'PH-000002', latitude: Number.NaN }),
      pothole({ id: 'PH-000003', longitude: 181 }),
      pothole({ id: 'PH-000004', latitude: -91 }),
    ])

    expect(result.features.map((feature) => feature.id)).toEqual(['PH-000001'])
  })

  it('falls back to the public pothole id when no road label exists', () => {
    const result = canonicalPotholesToGeoJSON([pothole()])
    expect(result.features[0].properties.label).toBe('PH-000001')
  })
})
