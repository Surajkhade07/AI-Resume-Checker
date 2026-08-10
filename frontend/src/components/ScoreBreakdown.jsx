import { COMPONENTS, getScoreTone } from '../lib/scoreHelpers'

export default function ScoreBreakdown({ analysis }) {
  const componentScores = analysis.component_scores || {}

  return (
    <section className="panel">
      <h3 className="panel-title">📈 Score Breakdown</h3>
      <div className="breakdown-grid">
        {COMPONENTS.map(({ label, key, max, icon }) => {
          const value = Number(componentScores[key] || 0)
          const pct = max ? (value / max) * 100 : 0
          const tone = getScoreTone((value / max) * 100)
          return (
            <div className="breakdown-row" key={key}>
              <div className="breakdown-label">
                <span>{icon} {label}</span>
                <span className="breakdown-value">{Math.round(value)}/{max}</span>
              </div>
              <div className="bar-track">
                <div className={`bar-fill tone-${tone}`} style={{ width: `${Math.min(pct, 100)}%` }} />
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
