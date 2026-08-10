export default function Landing({ setView }) {
  return (
    <div className="landing">
      <section className="hero">
        <div className="hero-scan" aria-hidden="true">
          <div className="hero-scan-doc">
            <span />
            <span />
            <span />
            <span />
          </div>
          <div className="hero-scan-line" />
        </div>
        <p className="eyebrow">Applicant Tracking System Analysis</p>
        <h1>Know exactly how ATS software reads your resume.</h1>
        <p className="hero-sub">
          Upload a resume — optionally alongside a job description — and get a
          score, a breakdown, and a fix list built from what parsers actually see.
        </p>
        <button className="btn btn-primary btn-lg" onClick={() => setView('scorer')}>
          Start analyzing your resume →
        </button>
      </section>

      <section className="feature-grid">
        <div className="feature-card">
          <span className="feature-icon">📊</span>
          <h3>Comprehensive scoring</h3>
          <p>Five weighted dimensions: Formatting (20%), Keywords &amp; Skills (25%), Content Quality (25%), Skill Validation (15%), ATS Compatibility (15%).</p>
        </div>
        <div className="feature-card">
          <span className="feature-icon">🔍</span>
          <h3>Skill validation</h3>
          <p>Checks that the skills you claim are actually demonstrated in your projects and experience — no more empty bullet points.</p>
        </div>
        <div className="feature-card">
          <span className="feature-icon">🔒</span>
          <h3>Privacy first</h3>
          <p>Analysis runs on infrastructure you control, with no third-party API calls. Your resume data stays yours.</p>
        </div>
      </section>

      <section className="steps">
        <h2>How it works</h2>
        <div className="steps-grid">
          <div className="step">
            <span className="step-index">01</span>
            <h4>Upload your resume</h4>
            <p>PDF, DOC, or DOCX — up to 5&nbsp;MB.</p>
          </div>
          <div className="step">
            <span className="step-index">02</span>
            <h4>AI analysis</h4>
            <p>Local models score formatting, keywords, content, and ATS compatibility.</p>
          </div>
          <div className="step">
            <span className="step-index">03</span>
            <h4>Actionable feedback</h4>
            <p>Get a prioritized list of fixes, sorted by how much they'll move your score.</p>
          </div>
        </div>
      </section>
    </div>
  )
}
