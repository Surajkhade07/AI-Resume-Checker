import { useState } from 'react'

export default function CriticalIssues({ analysis }) {
  const critical = analysis.critical_issues || []
  const summary = analysis.issues_summary || []
  const detailedFeedback = analysis.detailed_feedback || []
  const [expanded, setExpanded] = useState(false)

  // Find critical issues in detailed_feedback
  const criticalFeedbacks = detailedFeedback.filter(
    (f) => (f.severity_level || '').toLowerCase() === 'critical'
  )

  if (critical.length === 0 && criticalFeedbacks.length === 0 && summary.length === 0) {
    return (
      <section className="panel">
        <h3 className="panel-title">🚨 Critical Issues & ATS Blockers</h3>
        <div className="alert good">
          <strong>✅ No Critical ATS Blockers Found!</strong>
          <p>Your resume passed core formatting and critical ATS filter checks without urgent blockers.</p>
        </div>
      </section>
    )
  }

  const allCriticalItems = [
    ...critical,
    ...criticalFeedbacks.map((f) => `${f.issue_title}: ${f.ats_impact || f.how_to_fix}`),
  ]
  const uniqueCritical = Array.from(new Set(allCriticalItems))

  const extra = summary.filter((s) => !uniqueCritical.some((c) => c.includes(s)))

  return (
    <section className="panel">
      <div className="panel-header-row">
        <div>
          <h3 className="panel-title">🚨 Critical Issues & ATS Blockers</h3>
          <p className="panel-caption">
            High-severity issues that frequently cause automated ATS screen rejection.
          </p>
        </div>
        {uniqueCritical.length > 0 && (
          <span className="crit-count-badge">
            ⚠️ {uniqueCritical.length} Critical Blocker(s)
          </span>
        )}
      </div>

      {uniqueCritical.length > 0 ? (
        <div className="critical-issues-container">
          {uniqueCritical.map((item, i) => (
            <div key={i} className="critical-issue-card">
              <span className="crit-icon">🔴</span>
              <div className="crit-content">
                <strong>{item}</strong>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="alert warn">
          <strong>⚠️ Moderate issues flagged</strong>
          <p>Review the detailed feedback and action items below to maximize your score.</p>
        </div>
      )}

      {extra.length > 0 && (
        <div className="expander" style={{ marginTop: '1rem' }}>
          <button className="expander-toggle" onClick={() => setExpanded((v) => !v)}>
            {expanded ? '▾' : '▸'} 📋 Additional flagged items ({extra.length})
          </button>
          {expanded && (
            <ul className="bullet-list" style={{ marginTop: '0.5rem' }}>
              {extra.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  )
}

