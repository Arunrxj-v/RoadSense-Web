export type Period = 'today' | '7d' | '30d' | 'all'

export function startOfTodayIST(now = new Date()): Date {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
  const [year, month, day] = formatter.format(now).split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day) - 5.5 * 60 * 60 * 1000)
}

export function sinceForPeriod(period: Period): string | undefined {
  if (period === 'all') return undefined
  if (period === 'today') return startOfTodayIST().toISOString()
  const days = period === '7d' ? 7 : 30
  return new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString()
}

export function matchesPeriodDate(isoDate: string, period: Period): boolean {
  if (period === 'all') return true
  const timestamp = new Date(isoDate).getTime()
  if (Number.isNaN(timestamp)) return false
  const since = sinceForPeriod(period)
  return since ? timestamp >= new Date(since).getTime() : true
}
