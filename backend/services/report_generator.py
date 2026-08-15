"""
HTML report generator that creates structured HTML reports from analysis results.
Uses Jinja2 templates for rendering with data from the analysis pipeline.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from backend.core.config import APP_TITLE

logger = logging.getLogger('ats_resume_scorer')

# Setup Jinja2 template environment
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / 'templates'


def _get_template_env() -> Environment:
    """
    Initialize and return a Jinja2 template environment.
    Loads templates from the templates directory.
    
    Returns: Jinja2 Environment configured with the templates folder
    """
    loader = FileSystemLoader(str(TEMPLATE_DIR))
    env = Environment(loader=loader, autoescape=True)
    return env


def _render_template(template_name: str, **kwargs) -> str:
    """
    Render a specific Jinja2 template with provided context.
    
    Args:
        template_name: Name of the template file to render
        **kwargs: Template variables to pass to the renderer
        
    Returns: Rendered HTML string
    """
    try:
        env = _get_template_env()
        template = env.get_template(template_name)
        return template.render(**kwargs)
    except Exception as e:
        logger.error(f"Failed to render template {template_name}: {e}")
        return f"<!-- Error rendering {template_name}: {e} -->"


def _build_summary_context(analysis_data: Dict) -> Dict:
    """
    Build the context dictionary for the summary template.
    Extracts and formats relevant data from the analysis results.
    
    Args:
        analysis_data: Complete analysis results
        
    Returns: Dict with summary-specific template variables
    """
    return {
        'ats_score': analysis_data.get('ats_score', 0),
        'component_scores': analysis_data.get('component_scores', {}),
        'interpretation': analysis_data.get('interpretation', ''),
        'keyword_match': analysis_data.get('keyword_match', 0),
        'matched_keywords': analysis_data.get('matched_keywords', []),
        'missing_keywords': analysis_data.get('missing_keywords', []),
        'skills': analysis_data.get('skills', []),
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'app_title': APP_TITLE,
    }


def _build_issues_context(analysis_data: Dict) -> Dict:
    """
    Build the context dictionary for the action items template.
    Organizes issues by severity level for structured display.
    
    Args:
        analysis_data: Complete analysis results
        
    Returns: Dict with issue-specific template variables
    """
    issues = analysis_data.get('detailed_feedback', [])
    
    # Group issues by severity
    critical = [i for i in issues if i.get('severity_level') == 'critical']
    moderate = [i for i in issues if i.get('severity_level') == 'moderate']
    minor = [i for i in issues if i.get('severity_level') == 'minor']
    
    return {
        'critical_issues': critical,
        'moderate_issues': moderate,
        'minor_issues': minor,
        'total_issues': len(issues),
        'suggestions': analysis_data.get('suggestions', []),
        'critical_issues_count': len(critical),
        'moderate_issues_count': len(moderate),
        'minor_issues_count': len(minor),
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'app_title': APP_TITLE,
    }


def _build_jd_comparison_context(analysis_data: Dict) -> Dict:
    """
    Build the context dictionary for the JD comparison template.
    
    Args:
        analysis_data: Complete analysis results
        
    Returns: Dict with JD comparison-specific template variables
    """
    jd_match = analysis_data.get('jd_match_analysis') or analysis_data.get('jd_comparison', {})
    
    return {
        'match_percentage': jd_match.get('match_percentage', 0),
        'semantic_similarity': jd_match.get('semantic_similarity', 0),
        'matched_keywords': jd_match.get('matched_keywords', []),
        'missing_keywords': jd_match.get('missing_keywords', []),
        'skills_gap': jd_match.get('skills_gap', []),
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'app_title': APP_TITLE,
    }


def _build_quick_actions_context(analysis_data: Dict) -> Dict:
    """
    Build the context dictionary for the quick actions template.
    Provides prioritized action items and quick wins.
    
    Args:
        analysis_data: Complete analysis results
        
    Returns: Dict with quick actions-specific template variables
    """
    issues = analysis_data.get('detailed_feedback', [])
    
    # Get top 3 critical actions
    critical_actions = []
    for issue in issues:
        if issue.get('severity_level') == 'critical':
            critical_actions.append({
                'title': issue.get('issue_title', ''),
                'action': issue.get('how_to_fix', ''),
                'steps': issue.get('action_items', [])[:3],
                'example': issue.get('example_improvement', ''),
            })
            if len(critical_actions) >= 3:
                break
    
    # Get quick wins (minor issues that are easy to fix)
    quick_wins = []
    for issue in issues:
        if issue.get('severity_level') == 'minor':
            quick_wins.append({
                'title': issue.get('issue_title', ''),
                'fix': issue.get('how_to_fix', ''),
            })
            if len(quick_wins) >= 3:
                break
    
    return {
        'critical_actions': critical_actions,
        'quick_wins': quick_wins,
        'strengths': analysis_data.get('strengths', [])[:5],
        'warnings': analysis_data.get('warnings', [])[:3],
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'app_title': APP_TITLE,
    }


def generate_html_report(analysis_data: Dict[str, Any]) -> str:
    """
    Generate a complete HTML report by combining all template sections.
    
    Args:
        analysis_data: Complete analysis results dictionary
        
    Returns:
        Complete HTML string with all report sections
    """
    # Generate each section
    summary_html = _render_template(
        'summary.html',
        **_build_summary_context(analysis_data),
    )
    
    action_items_html = _render_template(
        'action_items.html',
        **_build_issues_context(analysis_data),
    )
    
    jd_comparison_html = _render_template(
        'jd_comparison.html',
        **_build_jd_comparison_context(analysis_data),
    )
    
    quick_actions_html = _render_template(
        'quick_actions.html',
        **_build_quick_actions_context(analysis_data),
    )
    
    # Combine into full report
    html_parts = []
    html_parts.append('<!DOCTYPE html>')
    html_parts.append('<html lang="en">')
    html_parts.append('<head>')
    html_parts.append('<meta charset="UTF-8">')
    html_parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html_parts.append(f'<title>ATS Resume Analysis Report - {APP_TITLE}</title>')
    html_parts.append('<style>')
    html_parts.append("""
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; color: #333; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #1a237e; border-bottom: 3px solid #283593; padding-bottom: 10px; }
        h2 { color: #283593; margin-top: 25px; }
        .section { margin: 20px 0; padding: 15px; background: #fafafa; border-radius: 5px; border-left: 4px solid #283593; }
        .score { font-size: 24px; font-weight: bold; color: #1a237e; }
        .footer { text-align: center; margin-top: 30px; padding-top: 15px; border-top: 1px solid #e0e0e0; color: #888; font-size: 12px; }
    """)
    html_parts.append('</style>')
    html_parts.append('</head>')
    html_parts.append('<body>')
    html_parts.append('<div class="container">')
    
    # Report header
    html_parts.append(f'<h1>ATS Resume Analysis Report</h1>')
    html_parts.append(f'<p>Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>')
    
    # Insert sections
    html_parts.append(summary_html)
    html_parts.append('<hr>')
    html_parts.append(action_items_html)
    html_parts.append('<hr>')
    html_parts.append(jd_comparison_html)
    html_parts.append('<hr>')
    html_parts.append(quick_actions_html)
    
    # Footer
    html_parts.append(f'<div class="footer">Generated by {APP_TITLE}</div>')
    
    html_parts.append('</div>')
    html_parts.append('</body>')
    html_parts.append('</html>')
    
    return '\n'.join(html_parts)