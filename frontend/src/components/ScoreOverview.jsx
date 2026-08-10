import { getScoreTone, getScoreEmoji } from '../lib/scoreHelpers'

function getGrade(score) {
  if (score >= 90) return { letter: 'A+', color: 'grade-a' }
  if (score >= 80) return { letter: 'A', color: 'grade-a' }
  if (score >= 70) return { letter: 'B', color: 'grade-b' }
  if (score >= 60) return { letter: 'C', color: 'grade-c' }
  if (score >= 50) return { letter: 'D', color: 'grade-d' }
  return { letter: 'F', color: 'grade-f' }
}

export default function ScoreOverview({ analysis }) {
  const score = Number(analysis.ATS_score ?? analysis.ats_score ?? 0)
  const roundedScore = Math.round(score)
  const interpretation = analysis.interpretation || ''
  const tone = getScoreTone(score)
  const grade = getGrade(score)
  const improvement = analysis.estimated_improvement || 0
  const maxPossible = Math.min(100, Math.round(score + improvement))

  const penalties = analysis.penalties || {}
  const bonuses = analysis.bonuses || {}
  const penaltyEntries = Object.entries(penalties)
  const bonusEntries = Object.entries(bonuses)

  return (
    <section className="score-hero">
      <div className={`score-hero-card tone-${tone}`}>
        <div className="score-hero-ring">
          <svg viewBox="0 0 120 120" width="136" height="136">
            <circle cx="60" cy="60" r="52" fill="none" stroke="var(--line)" strokeWidth="10" />
            <circle
              cx="60" cy="60" r="52" fill="none"
              stroke="currentColor" strokeWidth="10" strokeLinecap="round"
              strokeDasharray={`${(score / 100) * 326.7} 326.7`}
              transform="rotate(-90 60 60)"
            />
          </svg>
          <div className="score-hero-number">
            <span>{getScoreEmoji(score)}</span>
            <strong>{roundedScore}</strong>
            <small>/100</small>
          </div>
        </div>

        <div className="score-hero-copy">
          <div className="score-title-row">
            <h2>Overall ATS Readiness Score</h2>
            <span className={`grade-badge ${grade.color}`}>Grade: {grade.letter}</span>
          </div>
          <p className="score-interpretation-text">
            {interpretation || 'Evaluates formatting, keyword density, content quality, skill validation, and ATS parser safety.'}
          </p>

          {/* Quick Boost & Breakdown row */}
          <div className="score-tags-row">
            {improvement > 0 && (
              <div className="score-tag tag-boost" title="Potential score after addressing high-priority recommendations">
                ⚡ Target Potential: <strong>{maxPossible}/100</strong> (+{Math.round(improvement)} pts)
              </div>
            )}

            {bonusEntries.map(([k, v]) => (
              <div key={k} className="score-tag tag-bonus">
                🎁 +{v} pts ({k.replace(/_/g, ' ')})
              </div>
            ))}

            {penaltyEntries.map(([k, v]) => (
              <div key={k} className="score-tag tag-penalty">
                ⚠️ -{v} pts ({k.replace(/_/g, ' ')})
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

