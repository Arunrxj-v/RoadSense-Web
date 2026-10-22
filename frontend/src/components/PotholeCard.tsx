import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  confidencePercent,
  formatCompactDateTimeIST,
  formatCoordinates,
  locationTitle,
  roadPrimaryLabel,
  roadSecondaryLabel,
  statusLabel,
} from '../lib/format'
import { potholePath } from '../lib/api'
import type { PotholeSummary } from '../lib/types'
import { Icon } from './Icon'

interface PotholeCardProps {
  pothole: PotholeSummary
  onClose: () => void
}

export function PotholeCard({ pothole, onClose }: PotholeCardProps) {
  const [copied, setCopied] = useState(false)
  const timer = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (timer.current) window.clearTimeout(timer.current)
    }
  }, [])

  const share = async () => {
    const url = new URL(window.location.href)
    url.searchParams.set('lat', pothole.latitude.toFixed(6))
    url.searchParams.set('lng', pothole.longitude.toFixed(6))
    url.searchParams.set('zoom', '16')
    url.searchParams.set('pothole', pothole.id)
    const shareUrl = url.toString()
    try {
      if (navigator.share) {
        await navigator.share({
          title: `RoadSense ${pothole.id}`,
          text: `Road condition observation at ${locationTitle(pothole)}`,
          url: shareUrl,
        })
      } else {
        await navigator.clipboard.writeText(shareUrl)
        setCopied(true)
        timer.current = window.setTimeout(() => setCopied(false), 1800)
      }
    } catch {
      try {
        await navigator.clipboard.writeText(shareUrl)
        setCopied(true)
        timer.current = window.setTimeout(() => setCopied(false), 1800)
      } catch {
        setCopied(false)
      }
    }
  }

  return (
    <section className="pothole-card" aria-label={`Pothole details for ${pothole.id}`}>
      <div className="pothole-card__header">
        <div className="pothole-card__status">
          <span className="pothole-card__status-dot" aria-hidden="true" />
          <span>{pothole.status === 'repaired' ? 'Pothole record' : 'Pothole detected'}</span>
        </div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close pothole details">
          <Icon name="close" size={18} />
        </button>
      </div>

      <div className="pothole-card__body">
        <h2 className="pothole-card__title">{locationTitle(pothole)}</h2>
        <p className="pothole-card__subtitle">{roadPrimaryLabel(pothole.road)}</p>
        <p className="pothole-card__road-meta">{roadSecondaryLabel(pothole.road)}</p>

        <div className="telemetry-grid">
          <div className="telemetry-cell">
            <span className="telemetry-cell__label">Last detected</span>
            <span className="telemetry-cell__value">{formatCompactDateTimeIST(pothole.last_detected_at)}</span>
          </div>
          <div className="telemetry-cell">
            <span className="telemetry-cell__label">First detected</span>
            <span className="telemetry-cell__value">{formatCompactDateTimeIST(pothole.first_detected_at)}</span>
          </div>
          <div className="telemetry-cell">
            <span className="telemetry-cell__label">Reports</span>
            <span className="telemetry-cell__value">{pothole.report_count}</span>
          </div>
          <div className="telemetry-cell">
            <span className="telemetry-cell__label">Confidence</span>
            <span className="telemetry-cell__value">{confidencePercent(pothole.confidence)}</span>
          </div>
          <div className="telemetry-cell telemetry-cell--wide">
            <span className="telemetry-cell__label">Coordinates · {statusLabel(pothole.status)}</span>
            <span className="telemetry-cell__value telemetry-cell__value--muted">
              {formatCoordinates(pothole.latitude, pothole.longitude)}
            </span>
          </div>
        </div>

        <div className="pothole-card__actions">
          <Link className="button button--primary button--grow" to={potholePath(pothole.id)}>
            <span>View details</span>
            <Icon name="arrow_forward" size={16} />
          </Link>
          <button
            type="button"
            className="button button--secondary button--compact"
            onClick={share}
            title="Share a link to this pothole"
            aria-label={copied ? 'Link copied' : 'Share a link to this pothole'}
          >
            <Icon name={copied ? 'check' : 'share'} size={18} />
            {copied ? <span className="sr-only">Link copied</span> : null}
          </button>
        </div>
        {copied ? (
          <p className="mono" style={{ marginTop: 6, fontSize: 10, color: 'var(--secondary)' }} role="status">
            Link copied to clipboard
          </p>
        ) : null}
      </div>
    </section>
  )
}
