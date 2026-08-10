export default function PrivacyAnalysis({ analysis }) {
  const loc = analysis.location_analysis || {}
  const candidate = analysis.resume_profile?.candidate_info || {}
  const risk = (loc.privacy_risk || 'none').toLowerCase()
  const locations = loc.detected_locations || []
  const recommendations = loc.recommendations || []
  const penalty = loc.penalty_applied || 0

  const riskTone = risk === 'high' ? 'bad' : risk === 'medium' ? 'warn' : 'good'
  const riskLabel = risk === 'high' ? 'High Risk' : risk === 'medium' ? 'Moderate Risk' : 'Safe / Minimal'

  const contactChecklist = [
    { label: 'Email Address', present: Boolean(candidate.email), value: candidate.email },
    { label: 'Phone Number', present: Boolean(candidate.phone), value: candidate.phone },
    { label: 'LinkedIn URL', present: Boolean(candidate.linkedin), value: candidate.linkedin },
    { label: 'GitHub URL', present: Boolean(candidate.github), value: candidate.github },
    { label: 'Portfolio Link', present: Boolean(candidate.portfolio), value: candidate.portfolio },
  ]

  return (
    <section className="panel privacy-panel">
      <div className="panel-header-row">
        <div>
          <h3 className="panel-title">🛡️ Privacy & Contact Safety Analysis</h3>
          <p className="panel-caption">
            ATS scans evaluate candidate contact safety and privacy exposure.
          </p>
        </div>
        <div className={`privacy-risk-badge tone-${riskTone}`}>
          <span>{riskTone === 'good' ? '🛡️' : '⚠️'} Privacy: {riskLabel}</span>
          {penalty > 0 && <span className="penalty-tag">(-{penalty} pts)</span>}
        </div>
      </div>

      <div className="privacy-grid">
        {/* Location & Address Analysis */}
        <div className="privacy-card">
          <h4 className="privacy-subheading">📍 Location Privacy Exposure</h4>
          {locations.length === 0 ? (
            <div className="alert good" style={{ margin: '0.75rem 0' }}>
              <strong>✅ Clean Location Footprint</strong>
              <p>No excessive physical addresses or zip codes detected. Recommended for modern ATS.</p>
            </div>
          ) : (
            <>
              <p className="privacy-desc">
                Detected <strong>{locations.length}</strong> location identifier(s) in resume text:
              </p>
              <ul className="detected-locations-list">
                {locations.map((item, idx) => (
                  <li key={idx} className="detected-loc-item">
                    <span className="loc-type-tag">{item.type ? item.type.toUpperCase() : 'LOC'}</span>
                    <span className="loc-text">"{item.text}"</span>
                  </li>
                ))}
              </ul>
            </>
          )}

          {recommendations.length > 0 && (
            <div className="loc-recs-box">
              <strong className="field-label">Location Recommendations:</strong>
              <ul className="bullet-list">
                {recommendations.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          )}
        </div>

        {/* Contact Information Audit */}
        <div className="privacy-card">
          <h4 className="privacy-subheading">📇 Contact Info Audit</h4>
          <p className="privacy-desc">Essential channels required by ATS recruiters for candidate outreach:</p>
          <ul className="contact-audit-list">
            {contactChecklist.map((c, i) => (
              <li key={i} className={`contact-audit-item ${c.present ? 'audit-pass' : 'audit-miss'}`}>
                <span className="audit-icon">{c.present ? '✅' : '❌'}</span>
                <div className="audit-info">
                  <strong>{c.label}</strong>
                  <span className="audit-val">
                    {c.present ? (c.value || 'Present') : 'Not detected in header'}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}
