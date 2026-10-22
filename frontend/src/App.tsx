import { useEffect } from 'react'
import { Route, Routes, useLocation } from 'react-router-dom'
import { AboutPage } from './pages/AboutPage'
import { DataNotePage } from './pages/DataNotePage'
import { DetectionsPage } from './pages/DetectionsPage'
import { MapPage } from './pages/MapPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { PotholeDetailPage } from './pages/PotholeDetailPage'

function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  return null
}

export function App() {
  return (
    <>
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<MapPage />} />
        <Route path="/detections" element={<DetectionsPage />} />
        <Route path="/pothole/:id" element={<PotholeDetailPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/public-data-note" element={<DataNotePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </>
  )
}
