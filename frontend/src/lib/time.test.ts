import { afterEach, describe, expect, it, vi } from 'vitest'
import { matchesPeriodDate, sinceForPeriod, startOfTodayIST } from './time'

afterEach(() => {
  vi.useRealTimers()
})

describe('Indian Standard Time period filters', () => {
  it('starts today at IST midnight', () => {
    const start = startOfTodayIST(new Date('2026-10-21T10:00:00Z'))
    expect(start.toISOString()).toBe('2026-10-20T18:30:00.000Z')
  })

  it('uses a rolling seven-day window', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-21T10:00:00Z'))
    expect(sinceForPeriod('7d')).toBe('2026-10-14T10:00:00.000Z')
    expect(sinceForPeriod('all')).toBeUndefined()
  })

  it('includes records after the period boundary and excludes older ones', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-21T10:00:00Z'))
    expect(matchesPeriodDate('2026-10-21T00:30:00Z', 'today')).toBe(true)
    expect(matchesPeriodDate('2026-10-20T18:29:59Z', 'today')).toBe(false)
    expect(matchesPeriodDate('2026-10-15T10:00:00Z', '7d')).toBe(true)
    expect(matchesPeriodDate('not-a-date', 'all')).toBe(true)
  })
})
