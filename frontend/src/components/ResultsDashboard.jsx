import ScoreOverview from './ScoreOverview.jsx'
import ScoreBreakdown from './ScoreBreakdown.jsx'
import ScoreChart from './ScoreChart.jsx'
import Strengths from './Strengths.jsx'
import CriticalIssues from './CriticalIssues.jsx'
import SkillValidation from './SkillValidation.jsx'
import JDComparison from './JDComparison.jsx'
import DetailedFeedback from './DetailedFeedback.jsx'
import ActionItems from './ActionItems.jsx'
import Recommendations from './Recommendations.jsx'
import ResumeProfile from './ResumeProfile.jsx'
import PrivacyAnalysis from './PrivacyAnalysis.jsx'

export default function ResultsDashboard({ analysis }) {
  if (!analysis) return null

  const jdComparison = analysis.jd_comparison || analysis.jd_match_analysis
  const parsedJd = analysis.parsed_jd

  return (
    <div className="results-dashboard">
      {/* 1. Score Overview & Headline */}
      <ScoreOverview analysis={analysis} />

      {/* 2. Score Breakdown by Components & Chart */}
      <div className="dashboard-grid-2col">
        <ScoreBreakdown analysis={analysis} />
        <ScoreChart analysis={analysis} />
      </div>

      {/* 3. Prioritized Strategic Recommendations Engine */}
      <Recommendations analysis={analysis} />

      {/* 4. Critical Blockers & Action Items */}
      <div className="dashboard-grid-2col">
        <CriticalIssues analysis={analysis} />
        <ActionItems analysis={analysis} />
      </div>

      {/* 5. Parsed Candidate Profile & Resume Structure */}
      <ResumeProfile analysis={analysis} />

      {/* 6. Skill Validation Deep Dive & Privacy Analysis */}
      <div className="dashboard-grid-2col">
        <SkillValidation analysis={analysis} />
        <PrivacyAnalysis analysis={analysis} />
      </div>

      {/* 7. Job Description Matching (if JD provided) */}
      {jdComparison && <JDComparison jd={jdComparison} parsedJd={parsedJd} />}

      {/* 8. Detailed Feedback by Severity */}
      <DetailedFeedback analysis={analysis} />

      {/* 9. Verified Strengths */}
      <Strengths strengths={analysis.strengths || []} />
    </div>
  )
}

