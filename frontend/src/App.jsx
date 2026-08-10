import { useState } from 'react'
import { useAuth } from './context/AuthContext.jsx'
import { useAnalysis } from './context/AnalysisContext.jsx'
import Navbar from './components/Navbar.jsx'
import Landing from './pages/Landing.jsx'
import Scorer from './pages/Scorer.jsx'
import History from './pages/History.jsx'
import Resources from './pages/Resources.jsx'

export default function App() {
  const [view, setView] = useState('landing')
  const { loading: authLoading } = useAuth()
  const { loading: analysisLoading, progressMsg } = useAnalysis()

  if (authLoading) {
    return (
      <div className="boot-screen">
        <div className="boot-mark" />
      </div>
    )
  }

  return (
    <div className="app-shell">
      <Navbar view={view} setView={setView} />

      {analysisLoading && view !== 'scorer' && (
        <div className="active-analysis-banner" onClick={() => setView('scorer')}>
          <div className="banner-pulse" />
          <span>⚡ Resume analysis in progress ({progressMsg || 'Processing...'}) — <strong>Click to view</strong></span>
        </div>
      )}

      <main className="app-main">
        {view === 'landing' && <Landing setView={setView} />}
        {view === 'scorer' && <Scorer />}
        {view === 'history' && <History setView={setView} />}
        {view === 'resources' && <Resources />}
      </main>
      <footer className="app-footer">
        <span>ATS Resume Scorer</span>
        <span className="dot">·</span>
        <span>AI-powered analysis & actionable feedback</span>
      </footer>
    </div>
  )
}
