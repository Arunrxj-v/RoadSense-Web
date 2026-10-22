import { Link } from 'react-router-dom'
import { AppFooter } from '../components/AppFooter'
import { AppHeader } from '../components/AppHeader'
import { useDocumentMeta } from '../hooks/useDocumentMeta'

export function NotFoundPage() {
  useDocumentMeta({
    title: 'Page not found — RoadSense',
    description: 'The requested RoadSense page could not be found.',
  })

  return (
    <div className="app-shell">
      <AppHeader active="map" />
      <main id="main-content" className="main-area">
        <div className="content-page">
          <div className="content-container">
            <header className="content-header">
              <span className="eyebrow">404</span>
              <h1>Page not found</h1>
              <p>The page you requested does not exist or has moved.</p>
            </header>
            <div className="content-links">
              <Link className="button button--primary" to="/">
                Open the map
              </Link>
              <Link className="button button--secondary" to="/detections">
                Recent detections
              </Link>
            </div>
          </div>
        </div>
        <AppFooter />
      </main>
    </div>
  )
}
