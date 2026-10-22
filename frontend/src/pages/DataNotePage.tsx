import { Link } from 'react-router-dom'
import { AppFooter } from '../components/AppFooter'
import { AppHeader } from '../components/AppHeader'
import { useDocumentMeta } from '../hooks/useDocumentMeta'

export function DataNotePage() {
  useDocumentMeta({
    title: 'Public Data Note — RoadSense',
    description:
      'Provenance, verification status, privacy, and limitations for RoadSense public road condition data.',
  })

  return (
    <div className="app-shell">
      <AppHeader active="about" />
      <main id="main-content" className="main-area">
        <div className="content-page">
          <div className="content-container">
            <header className="content-header">
              <span className="eyebrow">Data provenance &amp; limitations</span>
              <h1>Public Data Note</h1>
              <p>
                This note explains where RoadSense public data comes from, what is deliberately not
                published, and how verified and unverified records are distinguished.
              </p>
            </header>

            <section className="card prose-card">
              <span className="eyebrow prose-card__eyebrow">01 · Pothole observations</span>
              <h2>Automated vehicle observations</h2>
              <p>
                Pothole records originate from RoadSense-equipped vehicles. The Android application
                performs detection locally, associates a GPS observation, and transmits report
                metadata to the home server. The server groups observations that fall within the
                configured distance and time window into one canonical pothole.
              </p>
              <p>
                Multiple reports for one canonical pothole are useful evidence of persistence, but
                each report is not published as a separate marker.
              </p>
            </section>

            <section className="card prose-card">
              <span className="eyebrow prose-card__eyebrow">02 · Road metadata</span>
              <h2>Linked road segments</h2>
              <p>
                Road name, number, locality, PIN code, authority, and classification are displayed
                only where a road segment record has been linked to the pothole. Where that link is
                absent, the interface says so instead of guessing a road from the coordinates.
              </p>
            </section>

            <section className="card prose-card">
              <span className="eyebrow prose-card__eyebrow">03 · Contract records</span>
              <h2>Source-backed work information</h2>
              <p>
                Contract data is intended to come from publicly available government records, such as
                Kerala e-Tendering or public road-work publications. A contract record preserves the
                contractor name, project or tender reference, work year, source name, source URL, and
                verification status.
              </p>
              <p>
                A record is never labelled verified without provenance. A match that has not been
                confirmed is explicitly marked <strong>Unverified match</strong>. If no source-backed
                record exists, the site shows <strong>Contractor information not available</strong>.
              </p>
            </section>

            <section className="card prose-card">
              <span className="eyebrow prose-card__eyebrow">04 · Privacy</span>
              <h2>What is not published</h2>
              <p>
                The public API exposes canonical pothole coordinates, observation counts, timestamps,
                and linked road/contract metadata. It does not expose camera frames, images, video,
                model tensors, device identifiers, private credentials, database access, or internal
                server details. The public web client is read-only.
              </p>
            </section>

            <section className="card prose-card">
              <span className="eyebrow prose-card__eyebrow">05 · Coverage</span>
              <h2>Unobserved is not defect-free</h2>
              <p>
                Coverage depends on where RoadSense vehicles have travelled. Roads without markers
                may simply not have been observed recently. Automated detections can also be affected
                by lighting, weather, road surface variation, and GPS accuracy. Public users should
                treat this as an indication of recorded conditions, not a safety certification.
              </p>
            </section>

            <div className="content-links">
              <Link className="button button--primary" to="/">
                Open the map
              </Link>
              <Link className="button button--secondary" to="/about">
                About RoadSense
              </Link>
            </div>
          </div>
        </div>
        <AppFooter />
      </main>
    </div>
  )
}
