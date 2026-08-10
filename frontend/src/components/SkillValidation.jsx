import { useState } from 'react'

export default function SkillValidation({ analysis }) {
  const details = analysis.skill_validation_details || {}
  const validated = details.validated || []
  const unvalidated = details.unvalidated || []
  const total = details.total ?? validated.length + unvalidated.length
  const pct = details.validation_pct ?? 0
  const [showValidated, setShowValidated] = useState(false)
  const [showUnvalidated, setShowUnvalidated] = useState(false)

  return (
    <section className="panel">
      <h3 className="panel-title">✅ Skill Validation</h3>
      {total === 0 ? (
        <p className="empty-note">No skills detected on the resume.</p>
      ) : (
        <>
          <div className="stat-row">
            <div className="stat">
              <span className="stat-value">{total}</span>
              <span className="stat-label">Total Skills</span>
            </div>
            <div className="stat">
              <span className="stat-value">{validated.length}</span>
              <span className="stat-label">Validated</span>
            </div>
            <div className="stat">
              <span className="stat-value">{Math.round(pct)}%</span>
              <span className="stat-label">Validation %</span>
            </div>
          </div>
          <div className="bar-track">
            <div className="bar-fill tone-good" style={{ width: `${Math.min(Math.max(pct, 0), 100)}%` }} />
          </div>

          {validated.length > 0 && (
            <div className="expander">
              <button className="expander-toggle" onClick={() => setShowValidated((v) => !v)}>
                {showValidated ? '▾' : '▸'} ✅ Validated skills ({validated.length})
              </button>
              {showValidated && (
                <ul className="bullet-list good">
                  {validated.map((entry, i) => {
                    const projects = entry.projects || []
                    const projectText = projects.length ? projects.slice(0, 3).join(', ') : 'experience section'
                    const sim = typeof entry.similarity === 'number' ? ` (${Math.round(entry.similarity * 100)}% match)` : ''
                    return <li key={i}><strong>{entry.skill}</strong>{sim} — demonstrated in: {projectText}</li>
                  })}
                </ul>
              )}
            </div>
          )}

          {unvalidated.length > 0 && (
            <div className="expander">
              <button className="expander-toggle" onClick={() => setShowUnvalidated((v) => !v)}>
                {showUnvalidated ? '▾' : '▸'} ⚠️ Unvalidated skills ({unvalidated.length})
              </button>
              {showUnvalidated && (
                <>
                  <p className="empty-note">These skills are listed but not tied to a project or experience bullet.</p>
                  <ul className="bullet-list bad">
                    {unvalidated.map((skill, i) => <li key={i}>❌ {skill}</li>)}
                  </ul>
                </>
              )}
            </div>
          )}
        </>
      )}
    </section>
  )
}
