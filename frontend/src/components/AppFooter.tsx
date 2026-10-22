import { Link } from 'react-router-dom'

export function AppFooter() {
  return (
    <footer className="app-footer">
      <div className="app-footer__inner">
        <p>
          RoadSense displays automated road condition observations. Roads without markers may
          not have been recently surveyed.
        </p>
        <div className="app-footer__links">
          <Link to="/public-data-note">Public Data Note</Link>
          <Link to="/about">About</Link>
        </div>
      </div>
    </footer>
  )
}
