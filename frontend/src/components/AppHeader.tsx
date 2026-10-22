import { Link, NavLink } from 'react-router-dom'
import { useApiMeta } from '../hooks/useServerData'
import { relativeTime } from '../lib/format'
import { Icon } from './Icon'

interface AppHeaderProps {
  active: 'map' | 'detections' | 'about'
}

const navItems = [
  { key: 'map', label: 'Map', to: '/' },
  { key: 'detections', label: 'Detections', to: '/detections' },
  { key: 'about', label: 'About', to: '/about' },
] as const

export function AppHeader({ active }: AppHeaderProps) {
  const meta = useApiMeta()
  const latest = meta.data?.latest_detection_at ?? null
  const feedLabel = meta.isError
    ? 'Feed unavailable'
    : meta.isLoading
      ? 'Checking feed'
      : relativeTime(latest)

  return (
    <header className="app-header">
      <div className="app-header__inner">
        <div className="brand-block">
          <Link className="brand" to="/" aria-label="RoadSense road condition map home">
            <span>RoadSense</span>
            <span className="brand__dot" aria-hidden="true" />
          </Link>
          <span className="brand-divider" aria-hidden="true">
            /
          </span>
          <span className="brand-subtitle">Road condition map</span>
        </div>

        <nav className="top-nav" aria-label="Primary">
          {navItems.map((item) => (
            <NavLink
              key={item.key}
              to={item.to}
              end={item.to === '/'}
              className="top-nav__link"
              aria-current={active === item.key ? 'page' : undefined}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="feed-status" title={meta.isError ? 'The API feed is unavailable' : 'Latest recorded observation'}>
          <span
            className={`feed-status__dot${latest && !meta.isError ? ' feed-status__dot--live' : ''}`}
            aria-hidden="true"
          />
          <span>{feedLabel}</span>
          {meta.isLoading ? <Icon name="progress_activity" size={12} className="feed-spinner" /> : null}
        </div>
      </div>
    </header>
  )
}
