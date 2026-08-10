import { useState } from 'react'
import { SEVERITY_ORDER, getSeverityTone } from '../lib/scoreHelpers'

function IssueCard({ issue }) {
  const [open, setOpen] = useState(false)
  const tone = getSeverityTone(issue.severity_level)
  const icon = tone === 'bad' ? '🔴' : tone === 'warn' ? '🟡' : '🟢'

  return (
    <div className="issue-card">
      <div className={`issue-head tone-${tone}`}>
        <strong>{icon} {issue.issue_title || 'Untitled issue'}</strong>
        {issue.ats_impact && <span className="issue-impact">{issue.ats_impact}</span>}
      </div>
      <button className="expander-toggle" onClick={() => setOpen((v) => !v)}>
        {open ? '▾' : '▸'} Details
      </button>
      {open && (
        <div className="issue-details">
          {issue.explanation && <p><strong>What's happening:</strong> {issue.explanation}</p>}
          {issue.where_it_appears && <p><strong>Where it appears:</strong> {issue.where_it_appears}</p>}
          {issue.how_to_fix && <p><strong>How to fix:</strong> {issue.how_to_fix}</p>}
          {(issue.action_items || []).length > 0 && (
            <>
              <p><strong>Action items:</strong></p>
              <ul className="bullet-list">
                {issue.action_items.map((a, i) => <li key={i}>{a}</li>)}
              </ul>
            </>
          )}
          {issue.example_improvement && (
            <>
              <p><strong>Example improvement:</strong></p>
              <pre className="code-block">{issue.example_improvement}</pre>
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default function DetailedFeedback({ analysis }) {
  const issues = analysis.detailed_feedback || []
  if (issues.length === 0) return null

  const grouped = SEVERITY_ORDER.reduce((acc, level) => {
    acc[level] = issues.filter((i) => (i.severity_level || 'low').toLowerCase() === level)
    return acc
  }, {})

  return (
    <section className="panel">
      <h3 className="panel-title">🔍 Detailed Feedback</h3>
      <p className="panel-caption">{issues.length} issue(s) flagged — grouped by severity.</p>
      {SEVERITY_ORDER.map((level) => {
        const items = grouped[level]
        if (!items.length) return null
        return (
          <div key={level} className="severity-group">
            <h4>{level[0].toUpperCase() + level.slice(1)} ({items.length})</h4>
            {items.map((issue, i) => <IssueCard key={i} issue={issue} />)}
          </div>
        )
      })}
    </section>
  )
}
