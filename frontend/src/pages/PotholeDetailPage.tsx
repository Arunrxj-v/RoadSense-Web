import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AppFooter } from '../components/AppFooter'
import { AppHeader } from '../components/AppHeader'
import { Icon } from '../components/Icon'
import { MiniMap } from '../components/MiniMap'
import { useDocumentMeta } from '../hooks/useDocumentMeta'
import { usePotholeDetail } from '../hooks/useServerData'
import { apiErrorMessage, potholePath, refreshPotholeResearch } from '../lib/api'
import {
  bearingLabel,
  confidencePercent,
  distanceMeters,
  formatCompactDateTimeIST,
  formatCoordinatesPlain,
  formatDateIST,
  formatDistance,
  formatTimeIST,
  locationTitle,
  projectReference,
  projectYear,
  researchPresentation,
  researchReference,
  roadPrimaryLabel,
  severityLabel,
  statusLabel,
  verificationPresentation,
} from '../lib/format'

export function PotholeDetailPage() {
  const { id = '' } = useParams()
  const detail = usePotholeDetail(id || null)
  const pothole = detail.data
  const [copied, setCopied] = useState(false)
  const [refreshBusy, setRefreshBusy] = useState(false)
  const [refreshError, setRefreshError] = useState('')

  useDocumentMeta({
    title: pothole
      ? `${pothole.id} · ${locationTitle(pothole)} — RoadSense`
      : 'Pothole record — RoadSense',
    description: pothole
      ? `Public road condition record ${pothole.id} at ${locationTitle(pothole)}, with ${pothole.report_count} observations.`
      : 'Public road condition record from RoadSense.',
  })

  const refreshResearch = async () => {
    if (!pothole || refreshBusy) return
    setRefreshBusy(true)
    setRefreshError('')
    try {
      await refreshPotholeResearch(pothole.id)
      await detail.refetch()
    } catch (error) {
      setRefreshError(apiErrorMessage(error))
    } finally {
      setRefreshBusy(false)
    }
  }

  const copyCoordinates = async () => {
    if (!pothole) return
    try {
      await navigator.clipboard.writeText(formatCoordinatesPlain(pothole.latitude, pothole.longitude))
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1800)
    } catch {
      setCopied(false)
    }
  }

  if (detail.isLoading) {
    return (
      <div className="app-shell">
        <AppHeader active="detections" />
        <main id="main-content" className="main-area">
          <div className="detail-page">
            <div className="detail-container">
              <div className="skeleton-block" style={{ height: 18, width: 160, marginBottom: 20 }} />
              <div className="skeleton-block" style={{ height: 210, marginBottom: 24 }} />
              <div className="detail-grid">
                <div className="skeleton-block" style={{ height: 380 }} />
                <div className="skeleton-block" style={{ height: 380 }} />
              </div>
              <span className="sr-only" role="status">
                Loading pothole details…
              </span>
            </div>
          </div>
          <AppFooter />
        </main>
      </div>
    )
  }

  if (detail.isError || !pothole) {
    return (
      <div className="app-shell">
        <AppHeader active="detections" />
        <main id="main-content" className="main-area">
          <div className="detail-page">
            <div className="detail-container">
              <div className="detail-breadcrumb">
                <Link className="back-link" to="/">
                  <Icon name="arrow_back" size={18} />
                  <span>Back to Map</span>
                </Link>
              </div>
              <div className="empty-state" role="alert">
                <div className="empty-state__icon">
                  <Icon name="error" size={20} />
                </div>
                <h2>This pothole record could not be loaded</h2>
                <p>{apiErrorMessage(detail.error)}</p>
                <div className="content-links">
                  <button type="button" className="button button--secondary" onClick={() => void detail.refetch()}>
                    <Icon name="refresh" size={16} />
                    Try again
                  </button>
                  <Link className="button button--secondary" to="/detections">
                    Browse detections
                  </Link>
                </div>
              </div>
            </div>
          </div>
          <AppFooter />
        </main>
      </div>
    )
  }

  const road = pothole.road
  const locationMetadata = pothole.location
  const project = pothole.project
  const research = pothole.research
  const verification = verificationPresentation(project)
  const researchView = researchPresentation(research)
  const researchActive = research?.status === 'pending' || research?.status === 'running'
  const researchMatched = Boolean(
    research?.match && (research.confidence === 'high' || research.confidence === 'medium'),
  )
  const contractView = researchMatched || researchActive || !project ? researchView : verification
  const location = locationTitle(pothole)
  const resolving = locationMetadata?.status === 'pending'
  const roadName = locationMetadata?.road_name || road?.name || ''
  const roadLabel = roadName || (resolving ? 'Resolving…' : 'Road information unavailable')
  const subtitleParts = [
    roadName || null,
    locationMetadata?.locality || road?.locality,
    locationMetadata?.state,
  ].filter(Boolean)
  const subtitle = subtitleParts.length
    ? subtitleParts.join(' · ')
    : 'Road information unavailable'
  const displayValue = (primary?: string | null, fallback?: string | null) =>
    primary || fallback || (resolving ? 'Resolving…' : 'Not recorded')
  const resolvingClass = (primary?: string | null, fallback?: string | null) =>
    !primary && !fallback && resolving ? 'meta-row__value--resolving' : undefined
  const showContractor = Boolean(project?.contractor)
  const contractorValue = showContractor
    ? project?.contractor
    : project?.verification_status === 'unknown'
      ? 'Awaiting source verification'
      : 'Not recorded in the linked source'

  return (
    <div className="app-shell">
      <AppHeader active="detections" />
      <main id="main-content" className="main-area">
        <div className="detail-page">
          <div className="detail-container">
            <div className="detail-breadcrumb">
              <Link className="back-link" to="/">
                <Icon name="arrow_back" size={18} />
                <span>Back to Map</span>
              </Link>
              <div className="id-chip">
                <span>Pothole ID:</span>
                <strong>{pothole.id}</strong>
                <span className="id-chip__dot" aria-hidden="true" />
              </div>
            </div>

            <section className="card detail-hero" aria-labelledby="pothole-title">
              <div className="detail-hero__top">
                <div>
                  <div className="detail-hero__status">
                    <span className="detail-hero__status-dot" aria-hidden="true" />
                    <span>{statusLabel(pothole.status) === 'Open' ? 'Pothole detected' : statusLabel(pothole.status)}</span>
                  </div>
                  <h1 id="pothole-title">{location}</h1>
                  <p className="detail-hero__subtitle">{subtitle}</p>
                </div>
                <div className="detail-hero__badges">
                  <div className="stat-chip">
                    <span className="stat-chip__label">Confidence score</span>
                    <span className="stat-chip__value">
                      {confidencePercent(pothole.confidence)}
                      <small>(model output)</small>
                    </span>
                  </div>
                  <div className="stat-chip">
                    <span className="stat-chip__label">Public audit status</span>
                    <span className="stat-chip__value">
                      <Icon name="verified" size={16} />
                      Canonical record
                    </span>
                  </div>
                </div>
              </div>

              <div className="detail-stats">
                <div>
                  <span className="detail-stat__label">Last logged timestamp</span>
                  <p className="detail-stat__value">{formatCompactDateTimeIST(pothole.last_detected_at)}</p>
                </div>
                <div>
                  <span className="detail-stat__label">Vehicle reports</span>
                  <p className="detail-stat__value detail-stat__value--mono">{pothole.report_count}</p>
                </div>
                <div>
                  <span className="detail-stat__label">Severity profile</span>
                  <p className="detail-stat__value">{severityLabel(pothole.severity)}</p>
                </div>
                <div>
                  <span className="detail-stat__label">First observed</span>
                  <p className="detail-stat__value">{formatCompactDateTimeIST(pothole.first_detected_at)}</p>
                </div>
              </div>
            </section>

            <div className="detail-grid">
              <div className="detail-grid__meta">
                <div className="card info-card">
                  <div className="info-card__head">
                    <span className="info-card__head-label">Cadastral &amp; spatial metadata</span>
                    <span className="info-card__head-note">WGS84 Datum</span>
                  </div>

                  <dl className="meta-list">
                    <div className="meta-row">
                      <dt>Road name</dt>
                      <dd className={resolvingClass(locationMetadata?.road_name, road?.name)}>
                        {displayValue(locationMetadata?.road_name, road?.name)}
                      </dd>
                    </div>
                    <div className="meta-row">
                      <dt>Locality</dt>
                      <dd className={resolvingClass(locationMetadata?.locality, road?.locality)}>
                        {displayValue(locationMetadata?.locality, road?.locality)}
                      </dd>
                    </div>
                    <div className="meta-row">
                      <dt>District</dt>
                      <dd className={resolvingClass(locationMetadata?.district)}>
                        {displayValue(locationMetadata?.district)}
                      </dd>
                    </div>
                    <div className="meta-row">
                      <dt>State</dt>
                      <dd className={resolvingClass(locationMetadata?.state)}>
                        {displayValue(locationMetadata?.state)}
                      </dd>
                    </div>
                    <div className="meta-row">
                      <dt>Country</dt>
                      <dd className={resolvingClass(locationMetadata?.country)}>
                        {displayValue(locationMetadata?.country)}
                      </dd>
                    </div>
                    <div className="meta-row">
                      <dt>Postal index code</dt>
                      <dd className={['mono', resolvingClass(locationMetadata?.pincode, road?.pincode)].filter(Boolean).join(' ') || undefined}>
                        {displayValue(locationMetadata?.pincode, road?.pincode)}
                      </dd>
                    </div>
                    <div className="meta-row">
                      <dt>Jurisdictional authority</dt>
                      <dd className={resolvingClass(locationMetadata?.authority, road?.authority)}>
                        {displayValue(locationMetadata?.authority, road?.authority)}
                      </dd>
                    </div>
                    <div className="meta-row">
                      <dt>Geographic coordinates</dt>
                      <dd>
                        <span className="coords-box">
                          <span>{formatCoordinatesPlain(pothole.latitude, pothole.longitude)}</span>
                          <button
                            type="button"
                            onClick={copyCoordinates}
                            title="Copy coordinates"
                            aria-label={copied ? 'Coordinates copied' : 'Copy coordinates'}
                          >
                            <Icon name={copied ? 'check' : 'content_copy'} size={16} />
                          </button>
                        </span>
                      </dd>
                    </div>
                  </dl>

                  <div className="verification-digest">
                    <Icon name="policy" size={20} />
                    <div>
                      <span className="verification-digest__title">Record verification digest</span>
                      <p>
                        This is a canonical pothole formed by deduplicating repeated vehicle
                        observations server-side. Address and road metadata are resolved from the
                        canonical GPS coordinates using {locationMetadata?.attribution || 'map data'}.
                        Fields the provider does not return remain “Not recorded”; contractor values
                        come only from a linked source-backed work record or an explicit automated
                        research result, never from inference.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="detail-grid__map">
                <div className="card inset-card">
                  <div className="info-card__head">
                    <span className="info-card__head-label">
                      <Icon name="pin_drop" size={18} />
                      Micro-location inset
                    </span>
                    <a
                      className="inline-link"
                      href={`https://www.google.com/maps?q=${pothole.latitude},${pothole.longitude}`}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Open in Google Maps
                      <Icon name="open_in_new" size={14} />
                    </a>
                  </div>

                  <div className="inset-map">
                    <MiniMap latitude={pothole.latitude} longitude={pothole.longitude} label={`${pothole.id} at ${location}`} />
                    <div className="inset-badge">
                      <strong>
                        {pothole.latitude.toFixed(6)}° N, {pothole.longitude.toFixed(6)}° E
                      </strong>
                      <span>
                        {roadLabel} / {locationMetadata?.locality || road?.locality || 'Locality not recorded'}
                      </span>
                    </div>
                    <div className="inset-topbadge">RECORD INSET · WGS 84</div>
                  </div>

                  <div className="inset-meta">
                    <span>Projection: EPSG:4326</span>
                    <span>Source: RoadSense observations</span>
                  </div>
                </div>
              </div>
            </div>

            <section className={`card detail-section contract-section contract-section--${contractView.tone}`}>
              <div className="detail-section__head">
                <div>
                  <h2>Road work &amp; contract record</h2>
                  <p>Public work records found through cited government and official sources.</p>
                </div>
                <div className="contract-head-actions">
                  <span className={`chip chip--${contractView.tone}`}>{contractView.label}</span>
                  {research && research.status !== 'none' ? (
                    <button
                      type="button"
                      className="button button--secondary button--compact"
                      onClick={() => void refreshResearch()}
                      disabled={refreshBusy || researchActive}
                    >
                      <Icon name="refresh" size={16} />
                      {researchActive ? 'Researching…' : refreshBusy ? 'Starting…' : 'Research again'}
                    </button>
                  ) : null}
                </div>
              </div>

              {refreshError ? (
                <p className="research-refresh-error" role="alert">{refreshError}</p>
              ) : null}

              {researchActive ? (
                <div className="contract-unavailable research-pending">
                  <Icon name="search" size={20} />
                  <div>
                    <h3>Research pending</h3>
                    <p>
                      RoadSense is checking public government and official records in the
                      background. This page updates automatically when the search finishes.
                    </p>
                  </div>
                </div>
              ) : researchMatched ? (
                <>
                  <div className="contract-meta">
                    <div className="contract-field">
                      <span className="contract-field__label">
                        {research.confidence === 'high'
                          ? 'Verified contractor'
                          : research.contractor
                            ? 'Possible contractor'
                            : 'Contractor'}
                      </span>
                      <p className="contract-field__value">
                        {research.contractor || 'Not recorded in the cited source'}
                      </p>
                    </div>
                    <div className="contract-field">
                      <span className="contract-field__label">Project / work name</span>
                      <p className="contract-field__value">{research.work_title || 'Not recorded'}</p>
                    </div>
                    <div className="contract-field">
                      <span className="contract-field__label">Tender / reference</span>
                      <p className="contract-field__value contract-field__value--mono">
                        {researchReference(research)}
                      </p>
                    </div>
                    <div className="contract-field">
                      <span className="contract-field__label">Authority</span>
                      <p className="contract-field__value">
                        {research.authority || locationMetadata?.authority || road?.authority || 'Not recorded'}
                      </p>
                    </div>
                    <div className="contract-field">
                      <span className="contract-field__label">Match confidence</span>
                      <p className="contract-field__value">
                        {research.confidence === 'high' ? 'Verified source match' : 'Possible match — review source'}
                      </p>
                    </div>
                    <div className="contract-field">
                      <span className="contract-field__label">Researched</span>
                      <p className="contract-field__value contract-field__value--mono">
                        {research.researched_at ? formatDateIST(research.researched_at) : 'Not recorded'}
                      </p>
                    </div>
                  </div>

                  {research.evidence ? (
                    <div className="research-evidence">
                      <span className="contract-field__label">Evidence excerpt</span>
                      <blockquote>{research.evidence}</blockquote>
                    </div>
                  ) : null}

                  <div className="contract-provenance">
                    {research.source_url ? (
                      <a
                        className="inline-link inline-link--primary"
                        href={research.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        View source
                        <Icon name="open_in_new" size={14} />
                      </a>
                    ) : (
                      <span className="chip chip--unknown">Source unavailable</span>
                    )}
                    <p className="contract-provenance__note">{contractView.detail}</p>
                  </div>
                </>
              ) : project ? (
                <>
                  <div className="contract-meta">
                    <div className="contract-field">
                      <span className="contract-field__label">Contractor</span>
                      <p className="contract-field__value">{contractorValue}</p>
                    </div>
                    <div className="contract-field">
                      <span className="contract-field__label">Project / work name</span>
                      <p className="contract-field__value">{project.name || 'Not recorded'}</p>
                    </div>
                    <div className="contract-field">
                      <span className="contract-field__label">Tender / reference</span>
                      <p className="contract-field__value contract-field__value--mono">{projectReference(project)}</p>
                    </div>
                    <div className="contract-field">
                      <span className="contract-field__label">Authority</span>
                      <p className="contract-field__value">{project.authority || road?.authority || 'Not recorded'}</p>
                    </div>
                    <div className="contract-field">
                      <span className="contract-field__label">Work year</span>
                      <p className="contract-field__value contract-field__value--mono">{projectYear(project)}</p>
                    </div>
                    <div className="contract-field">
                      <span className="contract-field__label">Work order / award</span>
                      <p className="contract-field__value contract-field__value--mono">
                        {project.work_order_ref || (project.awarded_at ? formatDateIST(project.awarded_at) : 'Not recorded')}
                      </p>
                    </div>
                  </div>

                  <div className="contract-provenance">
                    {project.source_url ? (
                      <a
                        className="inline-link inline-link--primary"
                        href={project.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Icon name="open_in_new" size={14} />
                        View source
                      </a>
                    ) : (
                      <span className="chip chip--unknown">No source URL recorded</span>
                    )}
                    <p className="contract-provenance__note">{verification.detail}</p>
                  </div>
                </>
              ) : (
                <div className="contract-unavailable">
                  <Icon name={research?.status === 'failed' ? 'cloud_off' : 'link_off'} size={20} />
                  <div>
                    <h3>
                      {research?.status === 'failed'
                        ? 'Research temporarily unavailable'
                        : 'No verified contractor record found'}
                    </h3>
                    <p>
                      {research?.status === 'none'
                        ? 'This pothole does not have enough resolved road metadata for automated research. RoadSense does not infer a contractor from the pothole location or from a similar road name.'
                        : research?.reason ||
                          'No source-backed public works record was found. RoadSense does not infer a contractor from the pothole location or from a similar road name.'}
                    </p>
                  </div>
                </div>
              )}
            </section>

            {road ? (
              <section className="card detail-section">
                <div className="detail-section__head">
                  <div>
                    <h2>Other detections along {road.name || road.number || 'this corridor'}</h2>
                    <p>Sequential canonical records captured during recent vehicular traverses.</p>
                  </div>
                  <span className="chip">{pothole.related.length} related records</span>
                </div>

                {pothole.related.length > 0 ? (
                  <div className="related-list">
                    {pothole.related.map((related) => {
                      const distance = distanceMeters(
                        pothole.latitude,
                        pothole.longitude,
                        related.latitude,
                        related.longitude,
                      )
                      const direction = bearingLabel(
                        pothole.latitude,
                        pothole.longitude,
                        related.latitude,
                        related.longitude,
                      )
                      return (
                        <div className="related-row" key={related.id}>
                          <div className="related-row__main">
                            <div className="related-row__icon">
                              <Icon name="warning" size={18} />
                            </div>
                            <div>
                              <div className="related-row__title">
                                <span>Pothole detected</span>
                                <span className="related-row__dot" aria-hidden="true" />
                                <span className="related-row__direction">
                                  {formatDistance(distance)} {direction}
                                </span>
                              </div>
                              <p className="related-row__meta">
                                {roadPrimaryLabel(related.road)} · Recorded {formatDateIST(related.last_detected_at)},{' '}
                                {formatTimeIST(related.last_detected_at)}
                              </p>
                            </div>
                          </div>
                          <div className="related-row__side">
                            <div className="related-row__confidence">
                              <span>Confidence</span>
                              <strong>{confidencePercent(related.confidence)}</strong>
                            </div>
                            <Link className="related-row__inspect" to={potholePath(related.id)}>
                              Inspect #{related.id}
                            </Link>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <p className="contract-provenance__note" style={{ paddingTop: 12 }}>
                    No other potholes have been recorded along this road segment.
                  </p>
                )}
              </section>
            ) : null}

            <section className="public-notice">
              <Icon name="info" size={22} />
              <div>
                <h2>Public transit &amp; sensing notice</h2>
                <p>
                  RoadSense records automated detections from mobile sensing sweeps. Observations
                  represent conditions at the time of transit. Civic agencies, local transport
                  authorities, and road users should consider road conditions variable according to
                  weather, ongoing maintenance, and vehicular wear. Contract records are shown only
                  when linked to a cited public source.
                </p>
              </div>
            </section>
          </div>
        </div>
        <AppFooter />
      </main>
    </div>
  )
}
