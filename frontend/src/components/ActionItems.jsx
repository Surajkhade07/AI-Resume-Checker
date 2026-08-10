import { SEVERITY_RANK, SEVERITY_ICON } from '../lib/scoreHelpers'

function collectActionItems(analysis) {
  const items = []
  for (const issue of analysis.detailed_feedback || []) {
    const level = (issue.severity_level || 'low').toLowerCase()
    for (const action of issue.action_items || []) {
      items.push({ level, source: issue.issue_title || '', action })
    }
  }
  if (items.length === 0) {
    for (const suggestion of analysis.suggestions || []) {
      items.push({ level: 'medium', source: 'General', action: suggestion })
    }
  }
  items.sort((a, b) => (SEVERITY_RANK[a.level] ?? 99) - (SEVERITY_RANK[b.level] ?? 99))
  return items
}

export default function ActionItems({ analysis }) {
  const items = collectActionItems(analysis)
  if (items.length === 0) return null

  return (
    <section className="panel">
      <h3 className="panel-title">⚡ Action Items</h3>
      <p className="panel-caption">Concrete steps to improve your score, sorted by urgency.</p>
      <ul className="action-list">
        {items.map((item, i) => (
          <li key={i}>
            <span>{SEVERITY_ICON[item.level] || '🟢'}</span>
            <span><strong>[{item.source}]</strong> {item.action}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
