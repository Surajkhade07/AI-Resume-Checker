import { useEffect, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { useAnalysis } from '../context/AnalysisContext.jsx'
import { getHistory, deleteHistoryEntry, getHistoryPdf, ApiError } from '../lib/api.js'
import { COMPONENTS, formatDate, getScoreTone, getScoreEmoji } from '../lib/scoreHelpers.js'
import ResultsDashboard from '../components/ResultsDashboard.jsx'

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export default function History({ setView }) {
  const { accessToken, isAuthenticated } = useAuth()
  const { setAnalysis } = useAnalysis()

  const [history, setHistory] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [modalAnalysis, setModalAnalysis] = useState(null)
  const [downloadingId, setDownloadingId] = useState(null)

  function loadHistory() {
    setLoading(true)
    setError(null)
    getHistory(accessToken)
      .then((data) => {
        setHistory(Array.isArray(data) ? data : [])
      })
      .catch((e) => {
        setError(e instanceof ApiError ? e.message : `Could not load history: ${e.message}`)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadHistory()
  }, [isAuthenticated, accessToken])

  async function handleDelete(id, filename) {
    if (!window.confirm(`Are you sure you want to delete the analysis for "${filename || 'this resume'}"?`)) {
      return
    }
    try {
      await deleteHistoryEntry(id, accessToken)
      setHistory((h) => (h || []).filter((entry) => entry.id !== id))
    } catch (e) {
      setError(e instanceof ApiError ? e.message : `Delete failed: ${e.message}`)
    }
  }

  async function handleDownloadPdf(id, filename) {
    setDownloadingId(id)
    try {
      const blob = await getHistoryPdf(id, accessToken)
      downloadBlob(blob, `ats_report_${filename || 'resume'}.pdf`)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : `PDF download failed: ${e.message}`)
    } finally {
      setDownloadingId(null)
    }
  }

  function handleLoadIntoScorer(entry) {
    if (entry.analysis_result) {
      setAnalysis(entry.analysis_result)
      if (setView) setView('scorer')
    }
  }

  const filteredHistory = (history || []).filter((item) => {
    const q = searchQuery.toLowerCase().trim()
    if (!q) return true
    const name = (item.filename || item.resume_name || '').toLowerCase()
    const scoreStr = String(Math.round(Number(item.ats_score || 0)))
    return name.includes(q) || scoreStr.includes(q)
  })

  // Quick stats
  const totalCount = history ? history.length : 0
  const scores = (history || []).map((h) => Number(h.ats_score || 0))
  const avgScore = totalCount > 0 ? Math.round(scores.reduce((a, b) => a + b, 0) / totalCount) : 0
  const maxScore = totalCount > 0 ? Math.round(Math.max(...scores)) : 0

  return (
    <div className="history-page">
      <div className="history-header">
        <div>
          <h1>📊 Analysis History & Records</h1>
          <p className="page-sub">
            Past resumes and job description comparisons saved against your account.
          </p>
        </div>
        <button className="btn btn-outline btn-sm" onClick={loadHistory} disabled={loading}>
          {loading ? 'Refreshing…' : '🔄 Refresh'}
        </button>
      </div>

      {!isAuthenticated && (
        <div className="alert warn">
          ⚠️ Sign in from the top bar to view your persistent resume analyses.
        </div>
      )}

      {error && <div className="alert bad">{error}</div>}

      {isAuthenticated && history && history.length > 0 && (
        <>
          {/* Stats Row */}
          <div className="history-stats-grid">
            <div className="stat-card">
              <span className="stat-icon">📄</span>
              <div className="stat-body">
                <span className="stat-label">Total Resumes Scanned</span>
                <strong className="stat-number">{totalCount}</strong>
              </div>
            </div>
            <div className="stat-card">
              <span className="stat-icon">📈</span>
              <div className="stat-body">
                <span className="stat-label">Average ATS Score</span>
                <strong className="stat-number">{avgScore}/100</strong>
              </div>
            </div>
            <div className="stat-card">
              <span className="stat-icon">🌟</span>
              <div className="stat-body">
                <span className="stat-label">Highest Score Achieved</span>
                <strong className="stat-number">{maxScore}/100</strong>
              </div>
            </div>
          </div>

          {/* Search Bar */}
          <div className="history-toolbar">
            <input
              type="text"
              className="history-search-input"
              placeholder="Search by resume name or score…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <span className="results-count-tag">
              Showing {filteredHistory.length} of {totalCount} analyses
            </span>
          </div>
        </>
      )}

      {isAuthenticated && history && history.length === 0 && !loading && (
        <div className="empty-state">
          <span className="empty-icon">📂</span>
          <h3>No Resume Analyses Yet</h3>
          <p>Run your first resume scan on the ATS Scorer to see insights and history recorded here.</p>
          <button className="btn btn-primary" onClick={() => setView && setView('scorer')}>
            🎯 Go to ATS Scorer
          </button>
        </div>
      )}

      {/* History Card List */}
      <div className="history-list">
        {filteredHistory.map((entry) => {
          const id = entry.id
          const score = Math.round(Number(entry.ats_score || 0))
          const tone = getScoreTone(score)
          const result = entry.analysis_result || {}
          const compScores = result.component_scores || {}
          const jd = result.jd_comparison || result.jd_match_analysis
          const recCount = (result.recommendations || []).length
          const skillCount = (result.skills || []).length

          return (
            <div key={id} className={`history-card tone-border-${tone}`}>
              <div className="history-card-top">
                <div className="history-card-info">
                  <span className="file-avatar">📄</span>
                  <div>
                    <h3 className="history-card-filename">{entry.filename || 'resume.pdf'}</h3>
                    <div className="history-card-meta">
                      <span>📅 {formatDate(entry.created_at || entry.date)}</span>
                      {skillCount > 0 && <span>• 🎯 {skillCount} skills detected</span>}
                      {recCount > 0 && <span>• 💡 {recCount} recommendations</span>}
                    </div>
                  </div>
                </div>

                <div className="history-card-score-box">
                  <div className={`history-score-chip tone-${tone}`}>
                    <span>{getScoreEmoji(score)}</span>
                    <strong>{score}</strong>
                    <small>/100</small>
                  </div>
                </div>
              </div>

              {/* Component mini indicators */}
              <div className="history-components-bar">
                {COMPONENTS.map((c) => {
                  const val = Math.round(Number(compScores[c.key] || 0))
                  return (
                    <div key={c.key} className="comp-mini-tag" title={`${c.label}: ${val}/${c.max}`}>
                      <span className="comp-mini-icon">{c.icon}</span>
                      <span className="comp-mini-label">{c.label}:</span>
                      <strong>{val}/{c.max}</strong>
                    </div>
                  )
                })}
                {jd && (
                  <div className="comp-mini-tag jd-tag" title={`JD Match: ${Math.round(Number(jd.match_percentage || 0))}%`}>
                    <span className="comp-mini-icon">🎯</span>
                    <span className="comp-mini-label">JD Match:</span>
                    <strong>{Math.round(Number(jd.match_percentage || 0))}%</strong>
                  </div>
                )}
              </div>

              {/* Actions row */}
              <div className="history-card-actions">
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => setModalAnalysis({ filename: entry.filename, data: result })}
                >
                  👁️ View Full Analysis Dashboard
                </button>
                <button
                  className="btn btn-outline btn-sm"
                  onClick={() => handleLoadIntoScorer(entry)}
                >
                  🚀 Open in Scorer
                </button>
                <button
                  className="btn btn-outline btn-sm"
                  disabled={downloadingId === id}
                  onClick={() => handleDownloadPdf(id, entry.filename)}
                >
                  {downloadingId === id ? 'Generating…' : '📑 Download PDF'}
                </button>
                <button
                  className="btn btn-danger-ghost btn-sm"
                  onClick={() => handleDelete(id, entry.filename)}
                  title="Delete from history"
                >
                  🗑️ Delete
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {/* Modal: Full Analysis Dashboard Viewer */}
      {modalAnalysis && (
        <div className="modal-overlay" onClick={() => setModalAnalysis(null)}>
          <div className="modal-content modal-fullscreen" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div>
                <h2>📄 Analysis Record: {modalAnalysis.filename}</h2>
                <p className="modal-sub">Viewing full saved ATS analysis and diagnostic reports.</p>
              </div>
              <div className="modal-header-actions">
                <button
                  className="btn btn-outline btn-sm"
                  onClick={() => {
                    setAnalysis(modalAnalysis.data)
                    setModalAnalysis(null)
                    if (setView) setView('scorer')
                  }}
                >
                  🚀 Load into Active Workspace
                </button>
                <button className="btn btn-outline btn-sm" onClick={() => setModalAnalysis(null)}>
                  ✕ Close
                </button>
              </div>
            </div>

            <div className="modal-body">
              <ResultsDashboard analysis={modalAnalysis.data} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

