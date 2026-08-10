export default function JDComparison({ jd, parsedJd }) {
  if (!jd) return null
  const matchPct = Number(jd.match_percentage || 0)
  const semantic = Number(jd.semantic_similarity || 0)
  const matched = jd.matched_keywords || []
  const missing = jd.missing_keywords || []
  const gap = jd.skills_gap || []

  const reqSkills = parsedJd?.required_skills || []
  const prefSkills = parsedJd?.preferred_skills || []
  const responsibilities = parsedJd?.key_responsibilities || []

  return (
    <section className="panel jd-panel">
      <div className="panel-header-row">
        <div>
          <h3 className="panel-title">🎯 Job Description Match & Requirements Fit</h3>
          <p className="panel-caption">
            Detailed semantic and keyword comparison against your target job posting.
          </p>
        </div>
        {parsedJd?.job_title && (
          <div className="target-role-pill">
            <span>Target Role:</span>
            <strong>{parsedJd.job_title}</strong>
          </div>
        )}
      </div>

      {/* Top Metrics Row */}
      <div className="jd-grid">
        <div className="jd-metric-card">
          <div className="stat-inline">
            <span className="stat-label">Keyword & Skill Overlap</span>
            <strong className="stat-value">{Math.round(matchPct)}%</strong>
          </div>
          <div className="bar-track">
            <div className="bar-fill tone-good" style={{ width: `${Math.min(Math.max(matchPct, 0), 100)}%` }} />
          </div>

          <div className="stat-inline" style={{ marginTop: '1rem' }}>
            <span className="stat-label">Semantic AI Context Alignment</span>
            <strong className="stat-value">{Math.round(semantic * 100)}%</strong>
          </div>
          <div className="bar-track">
            <div className="bar-fill tone-info" style={{ width: `${Math.min(Math.max(semantic * 100, 0), 100)}%` }} />
          </div>
        </div>

        <div className="jd-metric-card">
          <h4 className="field-label">✅ Matched Keywords ({matched.length})</h4>
          {matched.length > 0 ? (
            <div className="tag-cloud">
              {matched.slice(0, 20).map((kw, i) => (
                <span key={i} className="keyword-tag match">✓ {kw}</span>
              ))}
            </div>
          ) : (
            <p className="empty-note">No overlapping keywords detected yet.</p>
          )}
        </div>
      </div>

      {/* Missing Keywords & Skills Gap */}
      <div className="jd-grid" style={{ marginTop: '1.25rem' }}>
        <div className="jd-metric-card">
          <h4 className="field-label">❌ Missing Keywords from JD ({missing.length})</h4>
          {missing.length ? (
            <ul className="bullet-list bad">
              {missing.slice(0, 12).map((kw, i) => (
                <li key={i}>
                  <strong>{kw}</strong> — add to relevant experience or skills bullets
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-note">Great! All key job description terms are present in your resume.</p>
          )}
        </div>

        <div className="jd-metric-card">
          <h4 className="field-label">📊 Skills Gap Analysis ({gap.length})</h4>
          {gap.length ? (
            <ul className="bullet-list warn">
              {gap.slice(0, 10).map((s, i) => (
                <li key={i}>
                  <strong>{s}</strong> — mentioned in JD but missing in resume
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-note">No significant technical skill gap detected.</p>
          )}
        </div>
      </div>

      {/* Target JD Breakdown if available */}
      {parsedJd && (reqSkills.length > 0 || prefSkills.length > 0 || responsibilities.length > 0) && (
        <div className="jd-requirements-box" style={{ marginTop: '1.25rem' }}>
          <h4 className="requirements-heading">📋 Target Role Requirements Breakdown</h4>
          <div className="requirements-grid">
            {reqSkills.length > 0 && (
              <div>
                <strong>Must-Have Required Skills:</strong>
                <div className="tag-cloud" style={{ marginTop: '0.4rem' }}>
                  {reqSkills.map((s, i) => <span key={i} className="req-tag required">⭐ {s}</span>)}
                </div>
              </div>
            )}
            {prefSkills.length > 0 && (
              <div>
                <strong>Preferred / Nice-to-Have Skills:</strong>
                <div className="tag-cloud" style={{ marginTop: '0.4rem' }}>
                  {prefSkills.map((s, i) => <span key={i} className="req-tag preferred">👍 {s}</span>)}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  )
}

