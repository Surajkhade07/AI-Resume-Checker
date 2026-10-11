import { useRef, useState } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { useAnalysis } from '../context/AnalysisContext.jsx'
import { generatePdf, ApiError } from '../lib/api.js'
import ResultsDashboard from '../components/ResultsDashboard.jsx'

function summaryText(analysis) {
  const score = Number(analysis.ATS_score ?? analysis.ats_score ?? 0)
  const lines = [`ATS Score: ${Math.round(score)}/100`, '']
  if (analysis.strengths?.length) {
    lines.push('STRENGTHS:', ...analysis.strengths.map((s) => `  - ${s}`), '')
  }
  if (analysis.critical_issues?.length) {
    lines.push('CRITICAL ISSUES:', ...analysis.critical_issues.map((s) => `  - ${s}`), '')
  }
  if (analysis.suggestions?.length) {
    lines.push('SUGGESTIONS:', ...analysis.suggestions.map((s) => `  - ${s}`))
  }
  return lines.join('\n')
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export default function Scorer() {
  const { accessToken, isAuthenticated } = useAuth()
  const {
    mode,
    setMode,
    resumeFile,
    setResumeFile,
    jdMethod,
    setJdMethod,
    jdFile,
    setJdFile,
    jdText,
    setJdText,
    analysis,
    loading,
    error,
    setError,
    progressMsg,
    startAnalysis,
    clearAll,
  } = useAnalysis()

  const [pdfBusy, setPdfBusy] = useState(false)
  const fileInputRef = useRef(null)

  async function handleAnalyze() {
    if (!resumeFile) return
    await startAnalysis(accessToken)
  }

  async function handlePdf() {
    if (!analysis) return
    setPdfBusy(true)
    try {
      const blob = await generatePdf(analysis, accessToken)
      downloadBlob(blob, 'ats_resume_report.pdf')
    } catch (e) {
      setError(e instanceof ApiError ? e.message : `PDF generation failed (${e.message})`)
    } finally {
      setPdfBusy(false)
    }
  }

  return (
    <div className="scorer">
      <div className="scorer-header">
        <div>
          <h1>🎯 ATS Resume Scorer</h1>
          <p className="page-sub">Upload your resume — and optionally a job description — for a comprehensive analysis.</p>
        </div>
        {(resumeFile || analysis) && (
          <button className="btn btn-outline btn-sm" onClick={clearAll} title="Reset upload and start over">
            🔄 New Scan
          </button>
        )}
      </div>

      <div className="mode-toggle">
        <button className={mode === 'general' ? 'active' : ''} onClick={() => setMode('general')}>General ATS Score</button>
        <button className={mode === 'jd' ? 'active' : ''} onClick={() => setMode('jd')}>Job Description Comparison</button>
      </div>

      <div className="upload-grid">
        <div className="upload-card">
          <h3>📄 Upload Resume</h3>
          <div className="dropzone" onClick={() => fileInputRef.current?.click()}>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.doc,.docx,.txt"
              hidden
              onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
            />
            {resumeFile
              ? <span>✅ {resumeFile.name} ({(resumeFile.size / 1024).toFixed(1)} KB)</span>
              : <span>Click to choose a file — PDF, DOC, or DOCX (max 5 MB)</span>}
          </div>
        </div>

        <div className="upload-card">
          <h3>📋 Job Description</h3>
          {mode === 'jd' ? (
            <>
              <div className="mini-toggle">
                <button className={jdMethod === 'paste' ? 'active' : ''} onClick={() => setJdMethod('paste')}>Paste Text</button>
                <button className={jdMethod === 'file' ? 'active' : ''} onClick={() => setJdMethod('file')}>Upload .txt File</button>
              </div>
              {jdMethod === 'file' ? (
                <div className="dropzone small">
                  <input type="file" accept=".txt" onChange={(e) => setJdFile(e.target.files?.[0] || null)} />
                  {jdFile && <span>✅ {jdFile.name}</span>}
                </div>
              ) : (
                <>
                  <textarea
                    rows={7}
                    placeholder="Paste the JD here…"
                    value={jdText}
                    onChange={(e) => setJdText(e.target.value)}
                  />
                  {jdText && <p className="hint-ok">✅ {jdText.length} characters</p>}
                </>
              )}
            </>
          ) : (
            <p className="empty-note">Switch to "Job Description Comparison" mode to enable JD matching.</p>
          )}
        </div>
      </div>

      {error && <div className="alert bad" style={{ marginTop: '1.25rem' }}>{error}</div>}

      <div className="analyze-row">
        <button
          className="btn btn-primary btn-lg"
          disabled={!resumeFile || loading}
          onClick={handleAnalyze}
        >
          {loading ? (progressMsg || 'Analyzing resume...') : '🚀 Analyze Resume'}
        </button>
        {!isAuthenticated && resumeFile && (
          <p className="hint-warn">⚠️ Sign in from the top bar to analyze a resume.</p>
        )}
      </div>

      {loading && (
        <div className="analyzing-indicator">
          <div className="spinner-large" />
          <p><strong>Analyzing your resume...</strong></p>
          <p className="hint-sub">Feel free to browse other pages like Home or History; your analysis will keep running in the background.</p>
        </div>
      )}

      {analysis && (
        <>
          <div className="divider" />
          <ResultsDashboard analysis={analysis} />
          <div className="divider" />
          <section className="panel">
            <h3 className="panel-title">📥 Export Results</h3>
            <div className="export-row">
              <button className="btn btn-primary" onClick={handlePdf} disabled={pdfBusy}>
                {pdfBusy ? 'Generating…' : '📑 Generate PDF Report'}
              </button>
              <button
                className="btn btn-outline"
                onClick={() => downloadBlob(new Blob([summaryText(analysis)], { type: 'text/plain' }), 'ats_summary.txt')}
              >
                📄 Download Summary (.txt)
              </button>
            </div>
          </section>
        </>
      )}
    </div>
  )
}
