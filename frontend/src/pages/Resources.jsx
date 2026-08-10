import { useState } from 'react'

const KEYWORDS = {
  Tech: ['Programming languages (Python, Java, JavaScript)', 'Frameworks (React, Django, Spring)', 'Tools (Git, Docker, Kubernetes)', 'Methodologies (Agile, Scrum, CI/CD)'],
  Business: ['Project management', 'Stakeholder engagement', 'Budget management', 'Strategic planning', 'Team leadership'],
  Creative: ['Adobe Creative Suite', 'UI/UX Design', 'Wireframing & Prototyping', 'Brand identity', 'Visual communication'],
}

export default function Resources() {
  const [tab, setTab] = useState('Tech')

  return (
    <div className="resources-page">
      <h1>📚 Resources &amp; Tips</h1>
      <p className="page-sub">Learn how to optimize your resume for ATS systems.</p>

      <section className="panel">
        <h3 className="panel-title">🎯 ATS Optimization Tips</h3>
        <div className="dos-donts">
          <div>
            <h4>✅ Do's</h4>
            <ul className="bullet-list good">
              <li>Use standard section headings</li>
              <li>Include relevant keywords from the job description</li>
              <li>Use simple, clean formatting</li>
              <li>List skills explicitly</li>
              <li>Quantify achievements with numbers</li>
              <li>Use standard fonts (Arial, Calibri, Times New Roman)</li>
              <li>Save as PDF or DOCX</li>
            </ul>
          </div>
          <div>
            <h4>❌ Don'ts</h4>
            <ul className="bullet-list bad">
              <li>Avoid tables and text boxes</li>
              <li>Don't use headers/footers for important info</li>
              <li>Avoid images and graphics</li>
              <li>Don't use unusual fonts</li>
              <li>Avoid columns (use single column layout)</li>
              <li>Don't keyword stuff</li>
              <li>Avoid abbreviations without spelling out first</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="panel">
        <h3 className="panel-title">🔑 Common ATS Keywords by Industry</h3>
        <div className="mini-toggle">
          {Object.keys(KEYWORDS).map((k) => (
            <button key={k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)}>
              {k === 'Tech' ? '💻 Tech' : k === 'Business' ? '💼 Business' : '🎨 Creative'}
            </button>
          ))}
        </div>
        <ul className="bullet-list" style={{ marginTop: '1rem' }}>
          {KEYWORDS[tab].map((item, i) => <li key={i}>{item}</li>)}
        </ul>
      </section>

      <section className="panel">
        <h3 className="panel-title">📄 ATS-Friendly Resume Templates</h3>
        <div className="alert info">Coming soon: Downloadable ATS-optimized resume templates.</div>
      </section>
    </div>
  )
}
