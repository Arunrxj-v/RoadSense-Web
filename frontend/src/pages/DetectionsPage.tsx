import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AppFooter } from '../components/AppFooter'
import { AppHeader } from '../components/AppHeader'
import { Icon } from '../components/Icon'
import { useDocumentMeta } from '../hooks/useDocumentMeta'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { useRecentPotholes } from '../hooks/useServerData'
import { apiErrorMessage, potholeMapPath, potholePath } from '../lib/api'
import {
  confidencePercent,
  formatDateIST,
  formatTimeIST,
  locationTitle,
  roadPrimaryLabel,
  statusLabel,
} from '../lib/format'
import { sinceForPeriod, type Period } from '../lib/time'

const periodOptions: { key: Period; label: string }[] = [
  { key: 'today', label: 'Today' },
  { key: '7d', label: 'Last 7 days' },
  { key: '30d', label: 'Last 30 days' },
  { key: 'all', label: 'All' },
]

export function DetectionsPage() {
  useDocumentMeta({
    title: 'Recent detections — RoadSense',
    description:
      'A chronological ledger of canonical pothole records observed by RoadSense road-monitoring vehicles.',
  })

  const [period, setPeriod] = useState<Period>('today')
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(25)
  const debouncedQuery = useDebouncedValue(query.trim(), 400)
  const since = useMemo(() => sinceForPeriod(period), [period])

  useEffect(() => {
    setLimit(25)
  }, [period, debouncedQuery])

  const recent = useRecentPotholes({
    limit,
    offset: 0,
    q: debouncedQuery || undefined,
    since,
  })

  const potholes = recent.data?.potholes ?? []
  const total = recent.data?.meta.total ?? 0
  const hasMore = potholes.length < total
  const isLoading = recent.isLoading
  const isFetching = recent.isFetching

  const resetFilters = () => {
    setPeriod('all')
    setQuery('')
  }

  return (
    <div className="app-shell">
      <AppHeader active="detections" />
      <main id="main-content" className="main-area">
        <section className="ledger-hero">
          <div className="page-container ledger-hero__inner">
            <div className="ledger-hero__copy">
              <div className="ledger-hero__eyebrow">
                <span className="ledger-hero__eyebrow-dot" aria-hidden="true" />
                <span className="eyebrow">Telemetry ledger · Canonical records</span>
              </div>
              <h1>Recent Detections</h1>
              <p className="ledger-hero__description">
                A clean chronological record of road defects detected across monitored routes.
              </p>
            </div>

            <div className="ledger-tools">
              <div className="ledger-search">
                <Icon name="search" size={18} />
                <label className="sr-only" htmlFor="detection-filter">
                  Filter detections by road, locality, or PIN code
                </label>
                <input
                  id="detection-filter"
                  type="search"
                  placeholder="Filter by road, locality, or pincode…"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  autoComplete="off"
                />
                {isFetching ? (
                  <span
                    className="spinner"
                    aria-hidden="true"
                    style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)' }}
                  />
                ) : null}
              </div>
              <div className="segmented" id="timeFilters" role="group" aria-label="Filter by detection time">
                {periodOptions.map((option) => (
                  <button
                    key={option.key}
                    type="button"
                    className="segmented__button"
                    aria-pressed={period === option.key}
                    onClick={() => setPeriod(option.key)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="ledger-list-section">
          <div className="page-container">
            <div className="ledger-headings" aria-hidden="true">
              <div>Status</div>
              <div>Location / Corridor</div>
              <div>Timestamp</div>
              <div>Telemetry</div>
              <div className="ledger-headings__actions">Actions</div>
            </div>

            {isLoading ? (
              <div className="ledger-rows" aria-label="Loading recent detections" role="status">
                {Array.from({ length: 6 }).map((_, index) => (
                  <div key={index} className="skeleton-row" />
                ))}
                <span className="sr-only">Loading recent detections…</span>
              </div>
            ) : recent.isError ? (
              <div className="empty-state" role="alert">
                <div className="empty-state__icon">
                  <Icon name="cloud_off" size={20} />
                </div>
                <h2>The detection ledger could not be loaded</h2>
                <p>{apiErrorMessage(recent.error)}</p>
                <button type="button" className="button button--secondary" onClick={() => void recent.refetch()}>
                  <Icon name="refresh" size={16} />
                  Try again
                </button>
              </div>
            ) : potholes.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state__icon">
                  <Icon name="signpost" size={20} />
                </div>
                <h2>
                  {debouncedQuery
                    ? 'No records match that search'
                    : period === 'today'
                      ? 'No potholes have been recorded today'
                      : 'No potholes have been reported yet'}
                </h2>
                <p>
                  {debouncedQuery
                    ? 'Try a road name, locality, or 6-digit PIN code. Records appear here after a vehicle observation is accepted by the server.'
                    : 'Unmarked roads may not have been surveyed recently. You can widen the time range to see earlier observations.'}
                </p>
                <button type="button" className="button button--secondary" onClick={resetFilters}>
                  {debouncedQuery ? 'Clear search and filters' : 'View all detections'}
                </button>
              </div>
            ) : (
              <div className="ledger-rows">
                {potholes.map((pothole) => (
                  <article className="ledger-row" key={pothole.id}>
                    <div className="ledger-row__status">
                      <span
                        className="ledger-dot"
                        title={statusLabel(pothole.status)}
                        aria-label={statusLabel(pothole.status)}
                      />
                      <span className="ledger-row__mobile-status">Pothole defect</span>
                    </div>

                    <div className="ledger-row__location">
                      <h2 className="ledger-row__title">{locationTitle(pothole)}</h2>
                      <span className="ledger-row__road">{roadPrimaryLabel(pothole.road)}</span>
                    </div>

                    <div className="ledger-row__time">
                      <span className="ledger-row__date">{formatDateIST(pothole.last_detected_at)}</span>
                      <span className="ledger-row__clock">{formatTimeIST(pothole.last_detected_at)}</span>
                    </div>

                    <div className="ledger-row__telemetry">
                      <div className="telemetry-mini">
                        <span className="telemetry-mini__label">Pin</span>
                        <span className="telemetry-mini__value">{pothole.road?.pincode || '—'}</span>
                      </div>
                      <div className="telemetry-mini">
                        <span className="telemetry-mini__label">Confidence</span>
                        <span className="telemetry-mini__value telemetry-mini__value--confidence">
                          {confidencePercent(pothole.confidence)}
                        </span>
                      </div>
                    </div>

                    <div className="ledger-row__actions">
                      <Link
                        className="inline-link inline-link--primary"
                        to={potholeMapPath(pothole)}
                        aria-label={`View ${pothole.id} on the map`}
                      >
                        View on map
                        <Icon name="arrow_outward" size={14} />
                      </Link>
                      <Link
                        className="inline-link"
                        to={potholePath(pothole.id)}
                        aria-label={`Open details for ${pothole.id}`}
                      >
                        Details
                        <Icon name="chevron_right" size={14} />
                      </Link>
                    </div>
                  </article>
                ))}
              </div>
            )}

            {!isLoading && !recent.isError && potholes.length > 0 ? (
              <div className="ledger-footer">
                <span className="ledger-count">
                  Showing 1–{potholes.length} of {total} recent{' '}
                  {total === 1 ? 'detection' : 'detections'}
                </span>
                <button
                  type="button"
                  className="button button--secondary ledger-more"
                  disabled={!hasMore || isFetching}
                  onClick={() => setLimit((value) => value + 25)}
                >
                  {isFetching ? <span className="spinner" aria-hidden="true" /> : null}
                  <span>{hasMore ? 'Load earlier detections' : 'All available records loaded'}</span>
                  <Icon name={hasMore ? 'expand_more' : 'check'} size={16} />
                </button>
              </div>
            ) : null}

            <div className="survey-note">
              <Icon name="verified_user" size={20} />
              <div>
                <span className="survey-note__title">Survey methodology &amp; spatial coverage</span>
                <p>
                  Every row is one canonical pothole: repeated observations from RoadSense-equipped
                  vehicles are deduplicated server-side before publication. Potholes appear only where
                  a detection was recorded. Unmarked roads may not have been surveyed recently rather
                  than being certified defect-free. Road and contract details are shown only when a
                  source-backed record is linked.
                </p>
              </div>
            </div>
          </div>
        </section>
        <AppFooter />
      </main>
    </div>
  )
}
