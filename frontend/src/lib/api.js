const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'

class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function handle(response) {
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      detail = body.detail || JSON.stringify(body)
    } catch {
      try { detail = await response.text() } catch { /* noop */ }
    }
    throw new ApiError(`Backend returned ${response.status}: ${detail}`, response.status)
  }
  return response
}

function authHeaders(accessToken) {
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {}
}

export async function healthCheck() {
  const res = await fetch(`${BACKEND_URL}/api/v1/health`)
  await handle(res)
  return res.json()
}

export async function analyzeResume({ resumeFile, accessToken, jobDescription = '' }) {
  const formData = new FormData()
  formData.append('resume', resumeFile, resumeFile.name)
  formData.append('job_description', jobDescription)

  const res = await fetch(`${BACKEND_URL}/api/v1/analyze-resume`, {
    method: 'POST',
    headers: authHeaders(accessToken),
    body: formData,
  })

  // If backend accepted the job for background processing, poll for result
  if (res.status === 202) {
    const body = await res.json()
    const jobId = body.job_id
    const timeoutMs = 120000 // 2 minutes timeout
    const pollInterval = 1000
    const start = Date.now()

    while (Date.now() - start < timeoutMs) {
      await new Promise((r) => setTimeout(r, pollInterval))
      const statusRes = await fetch(`${BACKEND_URL}/api/v1/analysis/${jobId}`, {
        headers: authHeaders(accessToken),
      })
      if (statusRes.status === 200) {
        const job = await statusRes.json()
        if (job.status === 'done') {
          return job.result
        }
        if (job.status === 'error') {
          throw new ApiError(`Analysis failed: ${job.error}`, 500)
        }
        // otherwise still processing
        continue
      }
      // non-200: propagate error if any
      await handle(statusRes)
    }
    throw new ApiError('Analysis timed out after 120s', 504)
  }

  await handle(res)
  return res.json()
}

export async function getHistory(accessToken) {
  const res = await fetch(`${BACKEND_URL}/api/v1/history`, {
    headers: authHeaders(accessToken),
  })
  await handle(res)
  return res.json()
}

export async function deleteHistoryEntry(analysisId, accessToken) {
  const res = await fetch(`${BACKEND_URL}/api/v1/history/${analysisId}`, {
    method: 'DELETE',
    headers: authHeaders(accessToken),
  })
  await handle(res)
}

export async function generatePdf(analysisData, accessToken) {
  const res = await fetch(`${BACKEND_URL}/api/v1/generate-pdf`, {
    method: 'POST',
    headers: { ...authHeaders(accessToken), 'Content-Type': 'application/json' },
    body: JSON.stringify(analysisData),
  })
  await handle(res)
  return res.blob()
}

export async function getHistoryPdf(analysisId, accessToken) {
  const res = await fetch(`${BACKEND_URL}/api/v1/history/${analysisId}/pdf`, {
    headers: authHeaders(accessToken),
  })
  await handle(res)
  return res.blob()
}

export { ApiError, BACKEND_URL }
