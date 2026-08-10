import { useState } from 'react'

export default function ResumeProfile({ analysis }) {
  const profile = analysis.resume_profile || {}
  const candidate = profile.candidate_info || {}
  const summary = profile.professional_summary || ''
  const experience = profile.experience || []
  const education = profile.education || []
  const projects = profile.projects || []
  const certifications = profile.certifications || []
  const actionVerbs = profile.action_verbs || []
  const keywords = profile.keywords || []
  const months = profile.total_experience_months || analysis.experience_months || 0

  const [activeTab, setActiveTab] = useState('experience')

  const years = (months / 12).toFixed(1)

  return (
    <section className="panel resume-profile-panel">
      <div className="panel-header-row">
        <div>
          <h3 className="panel-title">👤 Parsed Resume Profile & Structure</h3>
          <p className="panel-caption">
            Extracted structured data parsed by AI model from your resume document.
          </p>
        </div>
        {months > 0 && (
          <div className="exp-badge-pill">
            <span>⏱️ Total Experience</span>
            <strong>{years} yrs ({months} mos)</strong>
          </div>
        )}
      </div>

      {/* Candidate Contact Card */}
      <div className="candidate-header-card">
        <div className="candidate-avatar">
          {(candidate.name ? candidate.name[0] : '👤').toUpperCase()}
        </div>
        <div className="candidate-details">
          <h3 className="candidate-name">{candidate.name || 'Candidate'}</h3>
          <div className="candidate-contact-grid">
            {candidate.email && (
              <span className="contact-item">
                📧 <a href={`mailto:${candidate.email}`}>{candidate.email}</a>
              </span>
            )}
            {candidate.phone && (
              <span className="contact-item">
                📞 <span>{candidate.phone}</span>
              </span>
            )}
            {candidate.linkedin && (
              <span className="contact-item">
                💼 <a href={candidate.linkedin.startsWith('http') ? candidate.linkedin : `https://${candidate.linkedin}`} target="_blank" rel="noreferrer">LinkedIn Profile</a>
              </span>
            )}
            {candidate.github && (
              <span className="contact-item">
                💻 <a href={candidate.github.startsWith('http') ? candidate.github : `https://${candidate.github}`} target="_blank" rel="noreferrer">GitHub Profile</a>
              </span>
            )}
            {candidate.portfolio && (
              <span className="contact-item">
                🌐 <a href={candidate.portfolio.startsWith('http') ? candidate.portfolio : `https://${candidate.portfolio}`} target="_blank" rel="noreferrer">Portfolio</a>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Professional Summary */}
      {summary && (
        <div className="profile-summary-box">
          <div className="summary-title-row">
            <strong>📝 Professional Summary</strong>
            <span className="summary-len-badge">{summary.split(/\s+/).length} words</span>
          </div>
          <p className="summary-text">"{summary}"</p>
        </div>
      )}

      {/* Tabs */}
      <div className="profile-tabs-nav">
        <button
          className={`tab-btn ${activeTab === 'experience' ? 'active' : ''}`}
          onClick={() => setActiveTab('experience')}
        >
          💼 Experience ({experience.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'projects' ? 'active' : ''}`}
          onClick={() => setActiveTab('projects')}
        >
          🚀 Projects ({projects.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'education' ? 'active' : ''}`}
          onClick={() => setActiveTab('education')}
        >
          🎓 Education ({education.length})
        </button>
        <button
          className={`tab-btn ${activeTab === 'skills' ? 'active' : ''}`}
          onClick={() => setActiveTab('skills')}
        >
          🔑 Keywords & Verbs ({keywords.length + actionVerbs.length})
        </button>
      </div>

      {/* Tab Content */}
      <div className="profile-tab-content">
        {activeTab === 'experience' && (
          <div className="timeline-container">
            {experience.length === 0 ? (
              <p className="empty-note">No dedicated work experience entries detected.</p>
            ) : (
              experience.map((exp, idx) => (
                <div key={idx} className="timeline-item">
                  <div className="timeline-dot" />
                  <div className="timeline-card">
                    <div className="timeline-head">
                      <div>
                        <h4 className="role-title">{exp.job_title || 'Role'}</h4>
                        <span className="company-name">{exp.company || 'Company'}</span>
                      </div>
                      <div className="timeline-dates">
                        <span>{exp.start_date || ''} — {exp.end_date || 'Present'}</span>
                        {exp.duration_months ? (
                          <span className="duration-pill">{exp.duration_months} mos</span>
                        ) : null}
                      </div>
                    </div>
                    {exp.description && (
                      <p className="role-description">{exp.description}</p>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'projects' && (
          <div className="projects-grid">
            {projects.length === 0 ? (
              <p className="empty-note">No dedicated project sections parsed.</p>
            ) : (
              projects.map((proj, idx) => (
                <div key={idx} className="project-card">
                  <h4 className="project-title">⚡ {proj.title || `Project #${idx + 1}`}</h4>
                  {proj.description && <p className="project-desc">{proj.description}</p>}
                  {proj.technologies && proj.technologies.length > 0 && (
                    <div className="project-tech-tags">
                      {proj.technologies.map((t, ti) => (
                        <span key={ti} className="tech-tag">{t}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'education' && (
          <div className="edu-list">
            {education.length === 0 ? (
              <p className="empty-note">No education entries parsed.</p>
            ) : (
              education.map((edu, idx) => (
                <div key={idx} className="edu-card">
                  <span className="edu-icon">🎓</span>
                  <div>
                    <h4 className="edu-degree">{edu.degree || 'Degree / Diploma'}</h4>
                    <p className="edu-inst">{edu.institution || 'University / Institution'}</p>
                    {edu.year && <span className="edu-year">Year: {edu.year}</span>}
                  </div>
                </div>
              ))
            )}

            {certifications.length > 0 && (
              <div className="cert-section" style={{ marginTop: '1.5rem' }}>
                <h4 className="field-label">🏆 Certifications ({certifications.length})</h4>
                <div className="tag-cloud">
                  {certifications.map((c, i) => (
                    <span key={i} className="cert-tag">📜 {c}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'skills' && (
          <div className="skills-intelligence-box">
            {actionVerbs.length > 0 && (
              <div className="intelligence-group">
                <h4 className="field-label">⚡ Strong Action Verbs Detected ({actionVerbs.length})</h4>
                <div className="tag-cloud">
                  {actionVerbs.map((v, i) => (
                    <span key={i} className="verb-tag">🚀 {v}</span>
                  ))}
                </div>
              </div>
            )}

            <div className="intelligence-group" style={{ marginTop: '1.25rem' }}>
              <h4 className="field-label">🔑 ATS Keywords Detected ({keywords.length})</h4>
              <div className="tag-cloud">
                {keywords.map((kw, i) => (
                  <span key={i} className="keyword-tag">🏷️ {kw}</span>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
