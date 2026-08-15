"""
Feedback engine that generates detailed issue reports and improvement suggestions
based on resume analysis results. Produces structured feedback for each scoring component.
"""
import logging
from typing import Any, Dict, List, Optional

from backend.models.schemas import IssueDetail

logger = logging.getLogger('ats_resume_scorer')


def _build_issue(
    title: str,
    severity: str,
    ats_impact: str,
    explanation: str,
    where_it_appears: str,
    how_to_fix: str,
    action_items: List[str],
    example_improvement: str,
) -> IssueDetail:
    """
    Build a structured IssueDetail object from individual components.
    
    Args:
        title: Short issue title
        severity: Severity level (critical/moderate/minor)
        ats_impact: Description of ATS impact
        explanation: Detailed explanation of the issue
        where_it_appears: Where the issue is found in the resume
        how_to_fix: General guidance on fixing
        action_items: Specific actionable steps
        example_improvement: Example of improvement
        
    Returns: IssueDetail model instance
    """
    return IssueDetail(
        issue_title=title,
        severity_level=severity,
        ats_impact=ats_impact,
        explanation=explanation,
        where_it_appears=where_it_appears,
        how_to_fix=how_to_fix,
        action_items=action_items,
        example_improvement=example_improvement,
    )


def generate_formatting_feedback(parsed_data: Dict) -> List[IssueDetail]:
    """
    Generate feedback on resume formatting and structure.
    
    Args:
        parsed_data: Parsed resume data
        
    Returns: List of formatting-related IssueDetail objects
    """
    issues = []
    
    # Check for professional summary
    if not parsed_data.get('professional_summary'):
        issues.append(_build_issue(
            title="Missing Professional Summary",
            severity="critical",
            ats_impact="ATS systems often rank resumes higher when a clear summary is present",
            explanation="A professional summary helps ATS systems quickly identify your career level and expertise.",
            where_it_appears="Top of resume",
            how_to_fix="Add a 2-3 sentence professional summary highlighting your key qualifications and career goals",
            action_items=[
                "Write a summary that includes your years of experience",
                "Mention your top 3-5 key skills or areas of expertise",
                "Include your career objective or what you bring to a role",
            ],
            example_improvement="'Results-driven software engineer with 5+ years of experience in full-stack development, specializing in Python and React. Proven track record of delivering scalable solutions and leading cross-functional teams.'"
        ))
    
    # Check for action verbs
    action_verbs = parsed_data.get('action_verbs', [])
    if len(action_verbs) < 3:
        issues.append(_build_issue(
            title="Insufficient Action Verbs",
            severity="moderate",
            ats_impact="ATS systems look for strong action verbs to identify impact-driven candidates",
            explanation="Strong action verbs make your experience more compelling and help ATS keyword matching.",
            where_it_appears="Experience section bullet points",
            how_to_fix="Start each bullet point with a strong action verb like 'Developed', 'Implemented', 'Led', 'Optimized'",
            action_items=[
                "Review each bullet point and ensure it starts with a strong action verb",
                "Use varied verbs throughout to avoid repetition",
                "Replace weak verbs like 'Was responsible for' with stronger alternatives",
            ],
            example_improvement="'Architected and deployed a microservices platform handling 10K+ requests per second, improving system reliability by 99.9%'"
        ))
    
    # Check for quantified achievements
    keywords = parsed_data.get('keywords', [])
    quant_keywords = [k for k in keywords if any(c.isdigit() for c in k)]
    if not quant_keywords:
        issues.append(_build_issue(
            title="Missing Quantified Achievements",
            severity="critical",
            ats_impact="ATS algorithms prioritize resumes with measurable, data-driven achievements",
            explanation="Quantified achievements (numbers, percentages, metrics) significantly boost ATS scores.",
            where_it_appears="Experience section",
            how_to_fix="Add specific metrics, percentages, and numbers to your achievement descriptions",
            action_items=[
                "Add percentages to show improvement (e.g., 'Increased efficiency by 30%')",
                "Include numbers (e.g., 'Managed team of 10 engineers')",
                "Add timeframes (e.g., 'Delivered project in 3 months')",
                "Include revenue or cost figures where applicable",
            ],
            example_improvement="'Optimized database queries resulting in 40% reduction in page load time and improved user satisfaction scores by 25%'"
        ))
    
    return issues


def generate_keyword_feedback(
    resume_keywords: List[str],
    jd_keywords: Optional[List[str]] = None,
    missing_keywords: Optional[List[str]] = None,
) -> List[IssueDetail]:
    """
    Generate feedback on keyword optimization.
    
    Args:
        resume_keywords: Keywords found in the resume
        jd_keywords: Keywords from the job description (optional)
        missing_keywords: Keywords that are missing from the resume
        
    Returns: List of keyword-related IssueDetail objects
    """
    issues = []
    
    if not resume_keywords:
        issues.append(_build_issue(
            title="No Keywords Detected",
            severity="critical",
            ats_impact="ATS systems rely heavily on keyword matching to rank candidates",
            explanation="Your resume appears to have no extractable keywords, making it invisible to ATS systems.",
            where_it_appears="Throughout the resume",
            how_to_fix="Add industry-standard keywords and technical terms relevant to your target role",
            action_items=[
                "Research common keywords in your industry",
                "Include technical skills, tools, and technologies",
                "Use both spelled-out terms and acronyms",
                "Add industry-specific terminology",
            ],
            example_improvement="Include terms like 'Python, Java, AWS, Agile, Scrum, CI/CD, REST API, Machine Learning'"
        ))
    
    if missing_keywords and len(missing_keywords) > 5:
        issues.append(_build_issue(
            title="Significant Keyword Gaps",
            severity="critical",
            ats_impact="Missing critical keywords significantly reduces your match rate with job descriptions",
            explanation=f"Your resume is missing {len(missing_keywords)} keywords that appear in the job description.",
            where_it_appears="Skills and experience sections",
            how_to_fix="Incorporate the missing keywords naturally into your skills and experience sections",
            action_items=[
                f"Add these top missing keywords: {', '.join(missing_keywords[:5])}",
                "Incorporate keywords naturally into bullet points",
                "Add a 'Technical Skills' section if missing",
                "Ensure both full forms and acronyms are included",
            ],
            example_improvement=f"Add a skills section with: {', '.join(missing_keywords[:5])}"
        ))
    
    if resume_keywords and len(resume_keywords) < 10:
        issues.append(_build_issue(
            title="Low Keyword Density",
            severity="moderate",
            ats_impact="Low keyword density reduces your chances of being matched to relevant positions",
            explanation="Your resume has fewer keywords than typical for your industry.",
            where_it_appears="Skills section and experience descriptions",
            how_to_fix="Expand your skills section and incorporate more relevant keywords naturally",
            action_items=[
                "List all technical skills, tools, and frameworks you've used",
                "Include soft skills where relevant",
                "Add domain-specific terminology",
                "Mention methodologies and processes you're familiar with",
            ],
            example_improvement="Add a comprehensive skills section with 15-20 relevant technical and soft skills"
        ))
    
    return issues


def generate_content_feedback(parsed_data: Dict) -> List[IssueDetail]:
    """
    Generate feedback on content quality and depth.
    
    Args:
        parsed_data: Parsed resume data
        
    Returns: List of content-related IssueDetail objects
    """
    issues = []
    
    # Check experience descriptions
    experience = parsed_data.get('experience', [])
    for i, exp in enumerate(experience):
        desc = exp.get('description', '')
        if desc and len(desc) < 100:
            issues.append(_build_issue(
                title=f"Thin Description for {exp.get('job_title', 'Role')}",
                severity="moderate",
                ats_impact="ATS systems evaluate role depth based on description length and content",
                explanation=f"The description for '{exp.get('job_title', 'a role')}' is too brief to properly convey your responsibilities.",
                where_it_appears=f"Experience: {exp.get('job_title', '')} at {exp.get('company', '')}",
                how_to_fix="Add 3-5 detailed bullet points describing your responsibilities and achievements",
                action_items=[
                    "Add specific responsibilities and daily tasks",
                    "Include technologies and tools used",
                    "Describe the scope and scale of your work",
                    "Add team size, budget, or project impact metrics",
                ],
                example_improvement="'Led development of a customer-facing analytics dashboard using React and D3.js, serving 50K+ users. Implemented real-time data updates reducing report generation time by 60%.'"
            ))
    
    # Check for missing education
    if not parsed_data.get('education'):
        issues.append(_build_issue(
            title="Missing Education Section",
            severity="moderate",
            ats_impact="Many ATS filters require education information for candidate screening",
            explanation="Without an education section, your resume may be filtered out by ATS requirements.",
            where_it_appears="Education section",
            how_to_fix="Add your educational background including degree, institution, and graduation year",
            action_items=[
                "Add your highest degree and institution",
                "Include graduation year or expected graduation",
                "Add relevant coursework or academic achievements",
                "Include GPA if above 3.5",
            ],
            example_improvement="'Bachelor of Science in Computer Science, University of Technology, 2020'"
        ))
    
    # Check for projects
    if not parsed_data.get('projects'):
        issues.append(_build_issue(
            title="No Projects Section",
            severity="minor",
            ats_impact="Projects can provide additional keyword matching opportunities",
            explanation="Adding a projects section can help showcase practical experience and provide more keyword density.",
            where_it_appears="Projects section",
            how_to_fix="Add 2-3 relevant projects with descriptions and technologies used",
            action_items=[
                "Include personal or professional projects",
                "Describe the problem and your solution",
                "List technologies, frameworks, and tools used",
                "Add links to GitHub or live demos if available",
            ],
            example_improvement="'E-commerce Platform: Built a full-stack e-commerce application using React, Node.js, and PostgreSQL with payment integration via Stripe.'"
        ))
    
    return issues


def generate_ats_compatibility_feedback(parsed_data: Dict) -> List[IssueDetail]:
    """
    Generate feedback on ATS compatibility issues.
    
    Args:
        parsed_data: Parsed resume data
        
    Returns: List of ATS compatibility-related IssueDetail objects
    """
    issues = []
    
    # Check for contact information
    if not parsed_data.get('email'):
        issues.append(_build_issue(
            title="Missing Email Address",
            severity="critical",
            ats_impact="ATS systems require email for candidate identification and contact",
            explanation="Without an email address, recruiters cannot contact you through the ATS system.",
            where_it_appears="Contact information section",
            how_to_fix="Add a professional email address at the top of your resume",
            action_items=[
                "Use a professional email (firstname.lastname@domain.com)",
                "Place email in the header with your name",
                "Ensure the email is clearly visible and properly formatted",
            ],
            example_improvement="'john.doe@email.com'"
        ))
    
    if not parsed_data.get('phone'):
        issues.append(_build_issue(
            title="Missing Phone Number",
            severity="moderate",
            ats_impact="Phone numbers are often required for ATS candidate profiles",
            explanation="Recruiters may need your phone number for initial screening calls.",
            where_it_appears="Contact information section",
            how_to_fix="Add your phone number with country code",
            action_items=[
                "Add a phone number where you can be reached",
                "Include country code for international applications",
                "Ensure the number is clearly formatted",
            ],
            example_improvement="'+1 (555) 123-4567'"
        ))
    
    if not parsed_data.get('linkedin'):
        issues.append(_build_issue(
            title="Missing LinkedIn Profile",
            severity="minor",
            ats_impact="LinkedIn profiles provide additional validation and can improve candidate ranking",
            explanation="Many recruiters expect to see a LinkedIn profile linked to your resume.",
            where_it_appears="Contact information section",
            how_to_fix="Add your LinkedIn profile URL to the contact section",
            action_items=[
                "Create a complete LinkedIn profile if you don't have one",
                "Customize your LinkedIn URL for a professional look",
                "Ensure your LinkedIn profile matches your resume",
            ],
            example_improvement="'linkedin.com/in/johndoe'"
        ))
    
    return issues


def generate_skill_validation_feedback(
    validation_details: Dict,
) -> List[IssueDetail]:
    """
    Generate feedback on skill validation results.
    
    Args:
        validation_details: Skill validation results with validated/unvalidated skills
        
    Returns: List of skill validation-related IssueDetail objects
    """
    issues = []
    
    unvalidated = validation_details.get('unvalidated', [])
    if unvalidated:
        issues.append(_build_issue(
            title=f"Unvalidated Skills: {len(unvalidated)} skills need project backing",
            severity="moderate",
            ats_impact="Skills listed without evidence of application may be discounted by ATS systems",
            explanation=f"The following skills are listed but not backed by project or experience evidence: {', '.join(unvalidated[:5])}",
            where_it_appears="Skills section",
            how_to_fix="Add project descriptions or experience bullet points that demonstrate these skills in action",
            action_items=[
                f"Create projects or experiences that demonstrate: {', '.join(unvalidated[:3])}",
                "Add specific examples of using each skill",
                "Describe the context, tools, and outcomes for each skill application",
                "Consider removing skills you cannot demonstrate",
            ],
            example_improvement="For 'Containerization': 'Used modern deployment workflows to improve release consistency and reduce deployment friction.'"
        ))
    
    validation_pct = validation_details.get('validation_pct', 0.0)
    if validation_pct < 50:
        issues.append(_build_issue(
            title="Low Skill Validation Rate",
            severity="critical",
            ats_impact="Low validation rates suggest skills may be exaggerated or lack practical application",
            explanation=f"Only {validation_pct:.0f}% of your skills are backed by evidence in your experience section.",
            where_it_appears="Skills section and Experience section",
            how_to_fix="Connect each skill to specific projects, responsibilities, or achievements",
            action_items=[
                "Map each skill to at least one experience or project",
                "Add context for how each skill was applied",
                "Include measurable outcomes where possible",
                "Remove skills that you cannot demonstrate",
            ],
            example_improvement="Create a skills matrix showing which skills were used in which projects"
        ))
    
    return issues


def generate_all_feedback(
    parsed_data: Dict,
    component_scores: Dict[str, float],
    jd_keywords: Optional[List[str]] = None,
    missing_keywords: Optional[List[str]] = None,
    skill_validation: Optional[Dict] = None,
) -> List[IssueDetail]:
    """
    Generate comprehensive feedback across all analysis dimensions.
    Aggregates issues from all feedback generators and sorts by severity.
    
    Args:
        parsed_data: Parsed resume data
        component_scores: Component scores from the scorer
        jd_keywords: Optional job description keywords
        missing_keywords: Optional list of missing keywords
        skill_validation: Optional skill validation results
        
    Returns:
        Combined list of all IssueDetail objects sorted by severity
    """
    all_issues = []
    
    # Generate feedback from each component
    all_issues.extend(generate_formatting_feedback(parsed_data))
    all_issues.extend(generate_keyword_feedback(
        parsed_data.get('keywords', []),
        jd_keywords,
        missing_keywords,
    ))
    all_issues.extend(generate_content_feedback(parsed_data))
    all_issues.extend(generate_ats_compatibility_feedback(parsed_data))
    
    if skill_validation:
        all_issues.extend(generate_skill_validation_feedback(skill_validation))
    
    # Sort by severity: critical first, then moderate, then minor
    severity_order = {'critical': 0, 'moderate': 1, 'minor': 2}
    all_issues.sort(key=lambda x: severity_order.get(x.severity_level, 99))
    
    return all_issues


def generate_issues_summary(issues: List[IssueDetail]) -> List[str]:
    """
    Generate a concise summary of issues from detailed feedback.
    
    Args:
        issues: List of IssueDetail objects
        
    Returns:
        List of short summary strings describing each issue
    """
    summary = []
    for issue in issues:
        prefix = {
            'critical': '⚠️ Critical:',
            'moderate': '🔶 Moderate:',
            'minor': '💡 Suggestion:',
        }.get(issue.severity_level, '•')
        summary.append(f"{prefix} {issue.issue_title}")
    return summary