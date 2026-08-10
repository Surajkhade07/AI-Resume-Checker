import re
from typing import List, Dict, Any, Optional
from backend.models.schemas import IssueDetail


def analyze_issues(
    resume_text: str,
    parsed_resume: Dict,
    skills: List[str],
    projects: List[Dict],
    action_verbs: List[str],
    skill_validation: Dict,
    scores: Dict,
    contact_info: Optional[Dict] = None,
) -> List[IssueDetail]:
    issues: List[IssueDetail] = []

    exp_entries = [e for e in parsed_resume.get('experience', []) if isinstance(e, dict)]
    edu_entries = [e for e in parsed_resume.get('education', []) if isinstance(e, dict)]
    proj_entries = [p for p in parsed_resume.get('projects', []) if isinstance(p, dict)]
    summary = (parsed_resume.get('professional_summary') or '').strip()

    # 1. Check Missing Sections
    if not exp_entries:
        issues.append(IssueDetail(
            issue_title="Missing Work Experience Section",
            severity_level="critical",
            ats_impact="High ATS deduction (-15 pts)",
            explanation="ATS systems and hiring managers look for dedicated work experience with job titles, companies, and dates.",
            where_it_appears="Experience Section",
            how_to_fix="Add an 'Experience' or 'Work History' section listing your relevant roles in reverse chronological order.",
            action_items=["Create an 'Experience' header", "Add job title, company, dates, and bullet points with metrics"],
            example_improvement="Software Engineer | Tech Corp | Jan 2023 - Present\n• Developed microservices handling 50k req/sec..."
        ))

    if not summary or len(summary) < 30:
        issues.append(IssueDetail(
            issue_title="Missing or Weak Professional Summary",
            severity_level="moderate",
            ats_impact="Medium Impact (-5 pts)",
            explanation="A concise professional summary at the top helps recruiters and ATS parse your core identity and value proposition.",
            where_it_appears="Top of Resume",
            how_to_fix="Add a 2-3 sentence summary highlighting your years of experience, core tech stack, and primary career achievements.",
            action_items=["Write a 3-sentence summary incorporating top skills and years of experience"],
            example_improvement="Results-driven Full Stack Developer with 3+ years of experience in React, Node.js, and cloud systems..."
        ))

    # 2. Check Skills & Skill Validation
    if len(skills) < 6:
        issues.append(IssueDetail(
            issue_title="Low Skill Count Detected",
            severity_level="high",
            ats_impact="High ATS deduction (-10 pts)",
            explanation=f"Only {len(skills)} skills detected. Most ATS screeners expect 10-25 relevant skills matching the job domain.",
            where_it_appears="Skills Section",
            how_to_fix="Expand your Skills section by categorizing languages, frameworks, developer tools, and database technologies.",
            action_items=["Add relevant technical languages, databases, cloud tools, and frameworks"],
            example_improvement="Languages: Python, TypeScript, SQL\nFrameworks: FastAPI, React, Node.js\nTools: Docker, Git, AWS"
        ))

    unvalidated = skill_validation.get('unvalidated_skills', [])
    if len(unvalidated) >= 3:
        sample_unvalidated = ", ".join(unvalidated[:4])
        issues.append(IssueDetail(
            issue_title="Unvalidated Skills Lacking Context",
            severity_level="moderate",
            ats_impact="Moderate Impact (-6 pts)",
            explanation=f"Skills such as ({sample_unvalidated}) are listed in your skills section but never referenced in your project or experience descriptions.",
            where_it_appears="Projects & Experience Bullets",
            how_to_fix="Showcase how you applied these skills in actual project deliverables or work tasks with measurable outcomes.",
            action_items=[f"Mention {skill} in a project bullet" for skill in unvalidated[:3]],
            example_improvement=f"• Built real-time analytics dashboard using {unvalidated[0] if unvalidated else 'React'} reducing latency by 30%."
        ))

    # 3. Check Action Verbs & Metrics
    if len(action_verbs) < 5:
        issues.append(IssueDetail(
            issue_title="Insufficient Strong Action Verbs",
            severity_level="moderate",
            ats_impact="Moderate Impact (-5 pts)",
            explanation="Resumes starting bullet points with passive words ('responsible for', 'worked on') score lower on content evaluation.",
            where_it_appears="Bullet Points",
            how_to_fix="Begin every bullet point with powerful action verbs such as Engineered, Orchestrated, Spearheaded, Automated, or Optimized.",
            action_items=["Replace passive phrases with strong past-tense action verbs"],
            example_improvement="Before: Was responsible for database optimization\nAfter: Optimized PostgreSQL queries reducing execution time by 45%"
        ))

    # Check for numbers / quantifiable metrics
    number_matches = len(re.findall(r'\b\d+(?:%|\+|k|x)?\b', resume_text))
    if number_matches < 3:
        issues.append(IssueDetail(
            issue_title="Lack of Quantifiable Achievements",
            severity_level="moderate",
            ats_impact="Moderate Impact (-5 pts)",
            explanation="Resumes with metrics (% growth, users served, latency reduced, revenue generated) rank significantly higher in recruiter scans.",
            where_it_appears="Experience & Projects",
            how_to_fix="Quantify your accomplishments using the XYZ formula: Accomplished [X], as measured by [Y], by doing [Z].",
            action_items=["Add numbers, percentages, team sizes, or speed improvements to at least 3 bullet points"],
            example_improvement="• Scaled backend API to handle 10,000+ daily active users with 99.9% uptime."
        ))

    # 4. Check Contact Information
    if contact_info:
        if not contact_info.get('email'):
            issues.append(IssueDetail(
                issue_title="Missing Email Address",
                severity_level="critical",
                ats_impact="Severe Impact",
                explanation="No valid email address was detected. ATS systems require a direct contact email to parse candidate records.",
                where_it_appears="Header",
                how_to_fix="Place your professional email clearly in the contact header at the very top.",
                action_items=["Add your email address in the contact section"],
                example_improvement="john.doe@email.com | (555) 123-4567 | linkedin.com/in/johndoe"
            ))
        if not contact_info.get('linkedin'):
            issues.append(IssueDetail(
                issue_title="Missing LinkedIn Profile URL",
                severity_level="low",
                ats_impact="Low Impact (-2 pts)",
                explanation="Most modern recruiters verify candidate backgrounds on LinkedIn.",
                where_it_appears="Header",
                how_to_fix="Include a clickable LinkedIn profile link in your contact info header.",
                action_items=["Add your LinkedIn profile link to header"],
                example_improvement="linkedin.com/in/yourusername"
            ))

    # 5. Check Formatting & Bullet Points
    bullet_count = sum(
        1 for line in resume_text.split('\n')
        if re.match(r'^\s*[•\-\*\◦]', line) or re.match(r'^\s*\d+\.', line)
    )
    if bullet_count < 5:
        issues.append(IssueDetail(
            issue_title="Sparse Use of Bullet Points",
            severity_level="moderate",
            ats_impact="Moderate Impact (-4 pts)",
            explanation="Large walls of paragraph text make it difficult for ATS scanners and human reviewers to identify key achievements.",
            where_it_appears="Body Format",
            how_to_fix="Break descriptions into 3-5 concise bullet points per role/project.",
            action_items=["Format experience and projects as distinct bullet points"],
            example_improvement="• Implemented authentication using JWT and OAuth2\n• Deployed containerized services with Docker to AWS"
        ))

    return issues


def generate_issues_summary(detailed_feedback: List[IssueDetail]) -> List[str]:
    summary = []
    for issue in detailed_feedback:
        if isinstance(issue, dict):
            title = issue.get('issue_title', '')
        else:
            title = issue.issue_title
        if title and title not in summary:
            summary.append(title)
    return summary