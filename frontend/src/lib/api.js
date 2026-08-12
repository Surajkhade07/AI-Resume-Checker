const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ||
  'http://localhost:8000'

class ApiError extends Error {
  constructor(message, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function handle(response) {
  if (!response.ok) {
    let detail = response.statusText || 'Unknown backend error'

    try {
      const body = await response.json()

      detail =
        body?.detail ||
        body?.error ||
        body?.message ||
        JSON.stringify(body)
    } catch {
      try {
        const text = await response.text()

        if (text) {
          detail = text
        }
      } catch {
        // Ignore body parsing errors
      }
    }

    throw new ApiError(
      `Backend returned ${response.status}: ${detail}`,
      response.status
    )
  }

  return response
}


function authHeaders(accessToken) {
  if (!accessToken) {
    return {}
  }

  return {
    Authorization: `Bearer ${accessToken}`,
  }
}


function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}


/**
 * Check whether backend is reachable.
 */
export async function healthCheck() {
  let res

  try {
    res = await fetch(
      `${BACKEND_URL}/api/v1/health`,
      {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
      }
    )
  } catch (error) {
    throw new ApiError(
      `Could not connect to backend: ${error.message}`,
      0
    )
  }

  await handle(res)

  return res.json()
}


/**
 * Check whether the ML models are ready.
 */
export async function readinessCheck() {
  let res

  try {
    res = await fetch(
      `${BACKEND_URL}/api/v1/ready`,
      {
        method: 'GET',
        headers: {
          Accept: 'application/json',
        },
      }
    )
  } catch (error) {
    throw new ApiError(
      `Could not connect to backend: ${error.message}`,
      0
    )
  }

  /*
   * 503 means backend is alive but models
   * are still loading.
   */
  if (res.status === 503) {
    try {
      return await res.json()
    } catch {
      return {
        status: 'starting',
        models_ready: false,
      }
    }
  }

  await handle(res)

  return res.json()
}


/**
 * Upload resume and wait for background analysis.
 *
 * Backend flow:
 *
 * POST /api/v1/analyze-resume
 *        ↓
 * 202 { job_id }
 *        ↓
 * GET /api/v1/analysis/{job_id}
 *        ↓
 * processing
 *        ↓
 * done
 */
export async function analyzeResume({
  resumeFile,
  accessToken,
  jobDescription = '',
  onProgress = null,
}) {
  if (!resumeFile) {
    throw new ApiError(
      'Please select a resume file.',
      400
    )
  }

  if (!accessToken) {
    throw new ApiError(
      'Authentication token is missing. Please sign in again.',
      401
    )
  }

  if (!BACKEND_URL) {
    throw new ApiError(
      'Backend URL is not configured.',
      0
    )
  }

  const formData = new FormData()

  formData.append(
    'resume',
    resumeFile,
    resumeFile.name
  )

  formData.append(
    'job_description',
    jobDescription || ''
  )

  let res

  try {
    if (onProgress) {
      onProgress(
        'Uploading resume to backend...'
      )
    }

    res = await fetch(
      `${BACKEND_URL}/api/v1/analyze-resume`,
      {
        method: 'POST',
        headers: authHeaders(accessToken),
        body: formData,
      }
    )
  } catch (error) {
    throw new ApiError(
      `Failed to connect to backend: ${error.message}`,
      0
    )
  }


  /*
   * Background job accepted.
   */
  if (res.status === 202) {
    let body

    try {
      body = await res.json()
    } catch {
      throw new ApiError(
        'Backend accepted the request but returned invalid JSON.',
        502
      )
    }

    const jobId = body?.job_id

    if (!jobId) {
      throw new ApiError(
        'Backend did not return a job ID.',
        502
      )
    }

    if (onProgress) {
      onProgress(
        'Resume uploaded. Starting AI analysis...'
      )
    }


    /*
     * Give the ML analysis enough time.
     *
     * 5 minutes is safer for a small Render instance,
     * especially when Sentence Transformer is running
     * on CPU.
     */
    const timeoutMs = 5 * 60 * 1000

    /*
     * Poll every 2 seconds.
     */
    const pollInterval = 2000

    const startTime = Date.now()

    let consecutiveNetworkErrors = 0

    while (
      Date.now() - startTime <
      timeoutMs
    ) {
      await sleep(pollInterval)

      let statusRes

      try {
        statusRes = await fetch(
          `${BACKEND_URL}/api/v1/analysis/${jobId}`,
          {
            method: 'GET',
            headers: {
              ...authHeaders(accessToken),
              Accept: 'application/json',
            },
          }
        )

        consecutiveNetworkErrors = 0
      } catch (error) {
        consecutiveNetworkErrors += 1

        /*
         * Don't immediately fail on one transient
         * Render/network error.
         */
        if (
          consecutiveNetworkErrors < 3
        ) {
          if (onProgress) {
            onProgress(
              'Waiting for analysis server...'
            )
          }

          continue
        }

        throw new ApiError(
          `Lost connection to backend while analysis was running: ${error.message}`,
          502
        )
      }


      /*
       * Job disappeared.
       */
      if (statusRes.status === 404) {
        throw new ApiError(
          'Analysis job was not found. The backend may have restarted while the analysis was running.',
          404
        )
      }


      /*
       * Backend temporarily unavailable.
       */
      if (
        statusRes.status === 502 ||
        statusRes.status === 503 ||
        statusRes.status === 504
      ) {
        consecutiveNetworkErrors += 1

        if (onProgress) {
          onProgress(
            'Backend is temporarily unavailable. Waiting...'
          )
        }

        /*
         * Give Render a few attempts to recover.
         */
        if (
          consecutiveNetworkErrors >= 5
        ) {
          throw new ApiError(
            `Backend became unavailable while processing the resume (HTTP ${statusRes.status}). Check Render logs for an application crash or out-of-memory error.`,
            statusRes.status
          )
        }

        continue
      }


      await handle(statusRes)

      let job

      try {
        job = await statusRes.json()
      } catch {
        throw new ApiError(
          'Backend returned invalid analysis status data.',
          502
        )
      }


      /*
       * Analysis completed.
       */
      if (job?.status === 'done') {
        if (!job.result) {
          throw new ApiError(
            'Analysis completed but no result was returned.',
            502
          )
        }

        if (onProgress) {
          onProgress(
            'Analysis completed!'
          )
        }

        return job.result
      }


      /*
       * Background analysis failed.
       */
      if (job?.status === 'error') {
        throw new ApiError(
          job.error ||
          'The backend failed while analyzing the resume.',
          500
        )
      }


      /*
       * Still processing.
       */
      if (
        job?.status === 'processing'
      ) {
        if (onProgress) {
          onProgress(
            'AI is analyzing your resume...'
          )
        }

        continue
      }


      /*
       * Unknown status.
       */
      throw new ApiError(
        `Backend returned unknown analysis status: ${job?.status}`,
        502
      )
    }


    throw new ApiError(
      'Analysis timed out after 5 minutes. The ML analysis may still be running or the Render server may have restarted.',
      504
    )
  }


  /*
   * If backend returned something other than 202,
   * process it normally.
   */
  await handle(res)

  return res.json()
}


/**
 * Get signed-in user's history.
 */
export async function getHistory(
  accessToken
) {
  let res

  try {
    res = await fetch(
      `${BACKEND_URL}/api/v1/history`,
      {
        method: 'GET',
        headers: {
          ...authHeaders(accessToken),
          Accept: 'application/json',
        },
      }
    )
  } catch (error) {
    throw new ApiError(
      `Failed to connect to backend: ${error.message}`,
      0
    )
  }

  await handle(res)

  return res.json()
}


/**
 * Delete history entry.
 */
export async function deleteHistoryEntry(
  analysisId,
  accessToken
) {
  let res

  try {
    res = await fetch(
      `${BACKEND_URL}/api/v1/history/${analysisId}`,
      {
        method: 'DELETE',
        headers: authHeaders(accessToken),
      }
    )
  } catch (error) {
    throw new ApiError(
      `Failed to connect to backend: ${error.message}`,
      0
    )
  }

  await handle(res)
}


/**
 * Generate PDF from current analysis.
 */
export async function generatePdf(
  analysisData,
  accessToken
) {
  let res

  try {
    res = await fetch(
      `${BACKEND_URL}/api/v1/generate-pdf`,
      {
        method: 'POST',
        headers: {
          ...authHeaders(accessToken),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(
          analysisData
        ),
      }
    )
  } catch (error) {
    throw new ApiError(
      `Failed to connect to backend: ${error.message}`,
      0
    )
  }

  await handle(res)

  return res.blob()
}


/**
 * Generate PDF for history entry.
 */
export async function getHistoryPdf(
  analysisId,
  accessToken
) {
  let res

  try {
    res = await fetch(
      `${BACKEND_URL}/api/v1/history/${analysisId}/pdf`,
      {
        method: 'GET',
        headers: authHeaders(accessToken),
      }
    )
  } catch (error) {
    throw new ApiError(
      `Failed to connect to backend: ${error.message}`,
      0
    )
  }

  await handle(res)

  return res.blob()
}


export {
  ApiError,
  BACKEND_URL,
}