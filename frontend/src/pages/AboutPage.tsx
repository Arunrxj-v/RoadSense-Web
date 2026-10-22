import { Link } from 'react-router-dom'
import { AppFooter } from '../components/AppFooter'
import { AppHeader } from '../components/AppHeader'
import { useDocumentMeta } from '../hooks/useDocumentMeta'

export function AboutPage() {
  useDocumentMeta({
    title: 'About RoadSense',
    description:
      'How the RoadSense public road condition map works, what it shows, and what its data limitations are.',
  })

  return (
    <div className="app-shell">
      <AppHeader active="about" />
      <main id="main-content" className="main-area">
        <div className="content-page">
          <div className="content-container">
            <header className="content-header">
              <span className="eyebrow eyebrow--hazard">Public infrastructure information</span>
              <h1>About RoadSense</h1>
              <p>
                RoadSense is a civic road-condition observation system. Road-monitoring vehicles
                detect potholes on-device and submit only the resulting observation — an identifier,
                coordinates, time, and confidence — to a home server. This website is the public
                information layer over that server.
              </p>
            </header>

            <section className="card prose-card">
              <h2>What the map shows</h2>
              <p>
                Every marker is one <strong>canonical pothole</strong>: a physical defect formed by
                deduplicating repeated observations of the same location on the server. Individual
                vehicle reports are not displayed as separate public potholes.
              </p>
              <p>
                The map loads the current canonical pothole feed once, so zooming and moving the
                map do not discard loaded records. PIN code search resolves the location through a
                server-side geocoding service and moves the map to that area; records outside the
                new view remain loaded in the feed.
              </p>
            </section>

            <section className="card prose-card">
              <h2>Architecture</h2>
              <ul>
                <li>Road-monitoring vehicles assess the road surface on-device.</li>
                <li>Only anonymous observation metadata — coordinates, time, and confidence — is submitted.</li>
                <li>Repeated observations are deduplicated into canonical pothole records.</li>
                <li>This website reads a read-only public feed and has no access to internal systems.</li>
              </ul>
              <p>
                Detection media and raw sensor data are not available to this website and are never
                published through its public feed.
              </p>
            </section>

            <section className="card prose-card">
              <h2>Road and contract information</h2>
              <p>
                Road metadata appears only when a road segment record is linked to the pothole.
                Contractor information is shown only when a public work record is linked through that
                road segment. Each record carries its source and a verification status:
              </p>
              <ul>
                <li><strong>Verified source-backed record</strong> — the record is linked to a cited public source.</li>
                <li><strong>Unverified match</strong> — a record has been matched to the road, but the match is not confirmed.</li>
                <li><strong>Verification pending / no record</strong> — no contractor name is presented as fact.</li>
              </ul>
              <p>
                RoadSense does not infer a contractor from the nearest GPS coordinate or from a
                similar-sounding road name.
              </p>
            </section>

            <section className="card prose-card">
              <h2>Important limitations</h2>
              <p>
                A pothole is shown where a RoadSense-equipped vehicle recorded a detection. A road
                without a marker has not necessarily been surveyed recently, and the absence of a
                marker is not a certificate that the road is defect-free. Automated observations are
                not a substitute for inspection by a road authority.
              </p>
            </section>

            <div className="content-links">
              <Link className="button button--primary" to="/">
                Open the map
              </Link>
              <Link className="button button--secondary" to="/public-data-note">
                Public Data Note
              </Link>
            </div>
          </div>
        </div>
        <AppFooter />
      </main>
    </div>
  )
}
