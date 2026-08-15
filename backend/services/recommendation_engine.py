"""
Recommendation engine that generates actionable suggestions, strengths,
and structured prioritized recommendations for ATS resume improvements.
"""
import logging
from typing import Any, Dict, List, Optional

from backend.models.schemas import IssueDetail

logger = logging.getLogger('ats_resume_scorer')


def _map_severity_to_priority(severity: str) -> tuple[str, str, str, float]:
    """Map issue severity to priority value, label, icon, and estimated score impact."""
    s = (severity or 'minor').lower()
    if s == 'critical':
        return 'critical', 'Critical', '🔴', 8.0
    elif s in ('high', 'urgent'):
        return 'high', 'High', '🟠', 6.0
    elif s in ('moderate', 'medium'):
        return 'medium', 'Medium', '🟡', 4.0
    else:
        return 'low', 'Low', '🟢', 2.0


def _infer_category(title: str, explanation: str) -> str:
    """Infer category from issue text."""
    combined = (title + ' ' + explanation).lower()
    if 'format' in combined or 'summary' in combined or 'layout' in combined or 'bullet' in combined:
        return 'formatting'
    if 'keyword' in combined or 'density' in combined or 'term' in combined:
        return 'keywords'
    if 'skill' in combined or 'validation' in combined or 'project' in combined:
        return 'skill_validation'
    if 'location' in combined or 'privacy' in combined or 'address' in combined:
        return 'location'
    if 'grammar' in combined or 'verb' in combined or 'spelling' in combined:
        return 'grammar'
    if 'experience' in combined or 'content' in combined or 'metric' in combined:
        return 'content'
    return 'general'


def _build_structured_recommendations(
    issues: List[IssueDetail],
    parsed_data: Dict,
    jd_match: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Build structured recommendation cards matching the format expected by the frontend Recommendations component.
    """
    recommendations = []
    
    # 1. Recommendations from feedback issues
    for issue in issues:
        pval, plabel, picon, impact = _map_severity_to_priority(issue.severity_level)
        category = _infer_category(issue.issue_title, issue.explanation)
        
        rec = {
            'title': issue.issue_title,
            'description': issue.how_to_fix or issue.explanation,
            'priority_icon': picon,
            'priority_label': plabel,
            'priority_value': pval,
            'impact_score': impact,
            'category': category,
            'action_items': issue.action_items or [issue.how_to_fix] if issue.how_to_fix else [],
        }
        recommendations.append(rec)
        
    # 2. Recommendations from JD match if missing keywords
    if jd_match and jd_match.get('missing_keywords'):
        missing = jd_match['missing_keywords'][:5]
        recommendations.append({
            'title': f"Integrate Missing Target JD Keywords ({len(missing)} terms)",
            'description': f"Target job description emphasizes: {', '.join(missing)}. Weave these into your skills and experience bullets.",
            'priority_icon': '🟠',
            'priority_label': 'High',
            'priority_value': 'high',
            'impact_score': 7.0,
            'category': 'keywords',
            'action_items': [f"Add '{kw}' to relevant project bullet points" for kw in missing[:3]],
        })

    # Sort recommendations by priority value
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    recommendations.sort(key=lambda r: (priority_order.get(r['priority_value'], 9), -r['impact_score']))
    
    return recommendations


def _generate_suggestions(issues: List[IssueDetail]) -> List[str]:
    """Extract flat actionable suggestions."""
    suggestions = []
    for issue in issues:
        suggestions.append(f"{issue.issue_title}: {issue.how_to_fix}")
        for item in issue.action_items[:2]:
            suggestions.append(item)
    return suggestions[:15]


def _generate_strengths(
    parsed_data: Dict,
    component_scores: Dict[str, float],
) -> List[str]:
    """Identify strengths in the resume based on analysis results."""
    strengths = []
    
    if parsed_data.get('professional_summary'):
        strengths.append("Professional summary present — helps ATS identify your career level and target domain quickly")
    
    experience = parsed_data.get('experience', [])
    if len(experience) >= 2:
        strengths.append(f"Structured work history with {len(experience)} position(s) documented")
    
    if parsed_data.get('education'):
        strengths.append("Education section clearly structured for academic qualification parsing")
    
    skills = parsed_data.get('skills', [])
    if len(skills) >= 8:
        strengths.append(f"Rich technical skills inventory with {len(skills)} verified skills detected")
    elif skills:
        strengths.append("Dedicated skills section present for search keyword indexing")
    
    if parsed_data.get('certifications'):
        strengths.append(f"Professional certifications listed ({len(parsed_data['certifications'])} verified credentials)")
    
    if parsed_data.get('projects'):
        strengths.append(f"Projects section showcases practical hands-on application ({len(parsed_data['projects'])} projects)")
    
    action_verbs = parsed_data.get('action_verbs', [])
    if len(action_verbs) >= 5:
        strengths.append(f"Strong action verb utilization ({len(action_verbs)} verbs) — boosts experience readability")
    
    if parsed_data.get('linkedin'):
        strengths.append("LinkedIn profile link included for professional validation")
    
    if parsed_data.get('github') or parsed_data.get('portfolio'):
        strengths.append("GitHub / Portfolio link provided for tangible technical evidence")
    
    # Check component scores
    for component, score in component_scores.items():
        comp_title = component.replace('_', ' ').title()
        if component in ('formatting', 'keywords', 'content') and score >= 18:
            strengths.append(f"Strong {comp_title} score ({score:.1f} pts)")
        elif component in ('skill_validation', 'ats_compatibility') and score >= 12:
            strengths.append(f"High {comp_title} score ({score:.1f} pts)")
    
    return strengths if strengths else ["Resume document is well-formatted and ready for optimization"]


def _generate_critical_issues(issues: List[IssueDetail]) -> List[str]:
    """Extract critical issues that need immediate attention."""
    critical = []
    for issue in issues:
        if (issue.severity_level or '').lower() == 'critical':
            critical.append(issue.issue_title)
    return critical[:6]


def _generate_warnings(issues: List[IssueDetail]) -> List[str]:
    """Generate warning messages based on moderate and minor issues."""
    warnings = []
    for issue in issues:
        if (issue.severity_level or '').lower() in ('moderate', 'medium', 'minor', 'low'):
            warnings.append(f"{issue.issue_title}: {issue.explanation[:100]}")
    return warnings[:6]


def generate_recommendations(
    parsed_data: Dict,
    component_scores: Dict[str, float],
    issues: List[IssueDetail],
    jd_match: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate comprehensive recommendations including structured recommendation items,
    summary, estimated score boost, suggestions, strengths, critical issues, and warnings.
    """
    structured_recs = _build_structured_recommendations(issues, parsed_data, jd_match)
    suggestions = _generate_suggestions(issues)
    strengths = _generate_strengths(parsed_data, component_scores)
    critical_issues = _generate_critical_issues(issues)
    warnings = _generate_warnings(issues)
    
    # Calculate potential improvement
    total_impact = sum(r['impact_score'] for r in structured_recs[:4])
    estimated_improvement = round(min(max(total_impact, 0.0), 30.0), 1)
    
    summary = (
        f"Generated {len(structured_recs)} prioritized action steps. "
        f"Addressing high-priority items can boost your ATS readiness by up to +{int(estimated_improvement)} pts."
        if structured_recs else "No critical improvements needed. Your resume is well optimized."
    )
    
    return {
        'recommendations': structured_recs,
        'recommendation_summary': summary,
        'estimated_improvement': estimated_improvement,
        'suggestions': suggestions,
        'strengths': strengths,
        'critical_issues': critical_issues,
        'warnings': warnings,
    }
