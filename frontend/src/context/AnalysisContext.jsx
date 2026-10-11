import { createContext, useContext, useState, useRef, useEffect } from 'react'
import { analyzeResume, ApiError } from '../lib/api.js'

const AnalysisContext = createContext(null)

export function AnalysisProvider({ children }) {
  const [mode, setMode] = useState('general') // 'general' | 'jd'
  const [resumeFile, setResumeFile] = useState(null)
  const [jdMethod, setJdMethod] = useState('paste')
  const [jdFile, setJdFile] = useState(null)
  const [jdText, setJdText] = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [jobId, setJobId] = useState(null)
  const [progressMsg, setProgressMsg] = useState('')

  // Abort controller / flag to prevent stale state updates
  const activeAnalysisRef = useRef(0)

  async function resolveJd() {
    if (mode !== 'jd') return ''
    if (jdText.trim()) return jdText.trim()
    if (!jdFile) return ''
    if (jdFile.name.toLowerCase().endsWith('.txt')) {
      try {
        return await jdFile.text()
      } catch {
        return ''
      }
    }
    setError('Job description files must be .txt — paste the JD text instead.')
    return ''
  }

  async function startAnalysis(accessToken) {
    if (!resumeFile) return

    const currentRun = ++activeAnalysisRef.current
    setError(null)
    setAnalysis(null)
    setLoading(true)
    setProgressMsg('Uploading and parsing resume...')

    try {
      const jobDescription = await resolveJd()
      if (activeAnalysisRef.current !== currentRun) return

      setProgressMsg('Evaluating ATS score and analyzing keywords...')
      const result = await analyzeResume({
        resumeFile,
        accessToken,
        jobDescription,
      })

      if (activeAnalysisRef.current === currentRun) {
        setAnalysis(result)
        setProgressMsg('')

        // Persist to local storage for instant availability in History
        try {
          const stored = JSON.parse(localStorage.getItem('ats_analysis_history') || '[]')
          const newEntry = {
            id: result.record_id || `scan_${Date.now()}`,
            filename: resumeFile.name,
            resume_name: resumeFile.name,
            ats_score: result.ats_score ?? result.ATS_score ?? 0,
            keyword_match: result.keyword_match ?? 0,
            created_at: new Date().toISOString(),
            date: new Date().toISOString(),
            analysis_result: result,
            analysis_data: result,
          }
          const updated = [newEntry, ...stored.filter((i) => i.id !== newEntry.id)]
          localStorage.setItem('ats_analysis_history', JSON.stringify(updated.slice(0, 50)))
        } catch {
          // localStorage may be unavailable or full
        }
      }
    } catch (e) {
      if (activeAnalysisRef.current === currentRun) {
        setError(e instanceof ApiError ? e.message : `Analysis failed: ${e.message}`)
        setProgressMsg('')
      }
    } finally {
      if (activeAnalysisRef.current === currentRun) {
        setLoading(false)
      }
    }
  }

  function resetAnalysis() {
    setAnalysis(null)
    setError(null)
    setLoading(false)
    setProgressMsg('')
  }

  function clearAll() {
    setResumeFile(null)
    setJdFile(null)
    setJdText('')
    setAnalysis(null)
    setError(null)
    setLoading(false)
    setProgressMsg('')
  }

  const value = {
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
    setAnalysis,
    loading,
    error,
    setError,
    progressMsg,
    startAnalysis,
    resetAnalysis,
    clearAll,
  }

  return <AnalysisContext.Provider value={value}>{children}</AnalysisContext.Provider>
}

export function useAnalysis() {
  const ctx = useContext(AnalysisContext)
  if (!ctx) throw new Error('useAnalysis must be used within AnalysisProvider')
  return ctx
}
