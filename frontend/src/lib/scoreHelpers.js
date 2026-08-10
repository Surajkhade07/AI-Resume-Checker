// Mirrors components/_helpers.py from the Streamlit frontend.

export function getScoreTone(score) {
  if (score >= 80) return 'good'
  if (score >= 60) return 'warn'
  return 'bad'
}

export function getScoreEmoji(score) {
  if (score >= 90) return '🌟'
  if (score >= 80) return '✅'
  if (score >= 70) return '👍'
  if (score >= 60) return '⚠️'
  return '🔴'
}

export function getSeverityTone(severity) {
  const level = (severity || '').toLowerCase()
  if (level === 'critical' || level === 'high') return 'bad'
  if (level === 'medium' || level === 'moderate') return 'warn'
  return 'good'
}

export function formatDate(dateString) {
  if (!dateString) return 'Just now'
  try {
    const d = new Date(dateString)
    if (isNaN(d.getTime())) return dateString
    return d.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateString
  }
}

export const COMPONENTS = [
  { label: 'Formatting', key: 'formatting', max: 20, icon: '📝', desc: 'Layout, headers, structure & bullets' },
  { label: 'Keywords & Skills', key: 'keywords', max: 25, icon: '🔑', desc: 'Technical & industry keyword match' },
  { label: 'Content Quality', key: 'content', max: 25, icon: '📄', desc: 'Action verbs, measurable metrics & grammar' },
  { label: 'Skill Validation', key: 'skill_validation', max: 15, icon: '✅', desc: 'Skills backed by project/work context' },
  { label: 'ATS Compatibility', key: 'ats_compatibility', max: 15, icon: '🤖', desc: 'Machine readability & privacy safety' },
]

export const SEVERITY_ORDER = ['critical', 'high', 'medium', 'low']
export const SEVERITY_RANK = { critical: 0, high: 1, medium: 2, moderate: 2, low: 3, info: 3 }
export const SEVERITY_ICON = { critical: '🔴', high: '🟠', medium: '🟡', moderate: '🟡', low: '🟢', info: 'ℹ️' }

export const CATEGORY_ICONS = {
  skill_validation: '🎯',
  grammar: '📝',
  location: '📍',
  keywords: '🔑',
  formatting: '📐',
  general: '💡',
}

