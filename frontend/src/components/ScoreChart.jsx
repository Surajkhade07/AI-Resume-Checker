import { COMPONENTS } from '../lib/scoreHelpers'

// Pure-SVG radar chart — no charting library needed.
// Reads the same analysis.component_scores object every other
// results component reads (see lib/scoreHelpers.js COMPONENTS).
export default function ScoreChart({ analysis }) {
  const componentScores = analysis.component_scores || {}
  const size = 280
  const center = size / 2
  const radius = 100
  const levels = 4 // ring count

  const points = COMPONENTS.map((c, i) => {
    const angle = (Math.PI * 2 * i) / COMPONENTS.length - Math.PI / 2
    const value = Number(componentScores[c.key] || 0)
    const pct = c.max ? Math.min(value / c.max, 1) : 0
    return {
      ...c,
      value,
      pct,
      angle,
      x: center + Math.cos(angle) * radius * pct,
      y: center + Math.sin(angle) * radius * pct,
      labelX: center + Math.cos(angle) * (radius + 34),
      labelY: center + Math.sin(angle) * (radius + 34),
    }
  })

  const polygonPoints = points.map((p) => `${p.x},${p.y}`).join(' ')

  const rings = Array.from({ length: levels }, (_, i) => {
    const r = (radius * (i + 1)) / levels
    const ringPoints = COMPONENTS.map((_, j) => {
      const angle = (Math.PI * 2 * j) / COMPONENTS.length - Math.PI / 2
      return `${center + Math.cos(angle) * r},${center + Math.sin(angle) * r}`
    }).join(' ')
    return <polygon key={i} points={ringPoints} fill="none" stroke="var(--line)" strokeWidth="1" />
  })

  const axisLines = points.map((p, i) => (
    <line key={i} x1={center} y1={center} x2={center + Math.cos(p.angle) * radius} y2={center + Math.sin(p.angle) * radius} stroke="var(--line)" strokeWidth="1" />
  ))

  return (
    <section className="panel">
      <h3 className="panel-title">🕸️ Score Shape</h3>
      <p className="panel-caption">Each axis is one scoring component, scaled to its own max — a bigger, rounder shape means a more even resume.</p>
      <div className="radar-wrap">
        <svg viewBox={`0 0 ${size} ${size}`} width="100%" style={{ maxWidth: 340 }}>
          {rings}
          {axisLines}
          <polygon points={polygonPoints} fill="var(--primary)" fillOpacity="0.18" stroke="var(--primary)" strokeWidth="2" />
          {points.map((p, i) => (
            <circle key={i} cx={p.x} cy={p.y} r="4" fill="var(--primary)" />
          ))}
          {points.map((p, i) => (
            <text
              key={i}
              x={p.labelX}
              y={p.labelY}
              textAnchor="middle"
              dominantBaseline="middle"
              className="radar-label"
            >
              {p.icon} {Math.round(p.value)}/{p.max}
            </text>
          ))}
        </svg>
      </div>
    </section>
  )
}
