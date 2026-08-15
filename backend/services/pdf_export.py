"""
PDF export service for generating downloadable PDF reports from analysis results.
Uses ReportLab for PDF generation with structured sections and formatting.
"""
import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    Frame,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger('ats_resume_scorer')


def _get_styles():
    """
    Get custom paragraph styles for the PDF report.
    
    Returns: Dict of ParagraphStyle objects for different report sections
    """
    styles = getSampleStyleSheet()
    
    # Custom styles for the report
    styles.add(ParagraphStyle(
        name='ReportTitle',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=12,
        textColor=colors.HexColor('#1a237e'),
    ))
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=20,
        spaceAfter=8,
        textColor=colors.HexColor('#283593'),
        borderWidth=0,
        borderPadding=0,
    ))
    styles.add(ParagraphStyle(
        name='ScoreText',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=4,
        textColor=colors.HexColor('#333333'),
    ))
    styles.add(ParagraphStyle(
        name='IssueText',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        leftIndent=10,
    ))
    styles.add(ParagraphStyle(
        name='SuggestionText',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4,
        leftIndent=15,
        textColor=colors.HexColor('#555555'),
    ))
    
    return styles


def _build_score_table(
    scores: Dict[str, float],
    ats_score: float,
    styles,
) -> Table:
    """
    Build a formatted table displaying component scores.
    """
    max_scores = {
        'formatting': 20.0,
        'keywords': 25.0,
        'content': 25.0,
        'skill_validation': 15.0,
        'ats_compatibility': 15.0,
    }

    data = [['Component', 'Score', 'Status']]
    
    for component, score in scores.items():
        max_val = max_scores.get(component, 100.0)
        pct = (score / max_val * 100.0) if max_val > 0 else 0.0
        
        # Determine status
        if pct >= 80:
            status = '✅ Excellent'
        elif pct >= 60:
            status = '⚠️ Good'
        elif pct >= 40:
            status = '🔶 Needs Work'
        else:
            status = '❌ Poor'
        
        component_name = component.replace('_', ' ').title()
        data.append([
            Paragraph(component_name, styles['ScoreText']),
            Paragraph(f"{score:.1f}/{max_val:.0f}", styles['ScoreText']),
            Paragraph(status, styles['ScoreText']),
        ])
    
    # Add overall score row
    data.append([
        Paragraph('<b>Overall ATS Score</b>', styles['ScoreText']),
        Paragraph(f'<b>{ats_score:.1f}/100</b>', styles['ScoreText']),
        Paragraph('', styles['ScoreText']),
    ])
    
    table = Table(data, colWidths=[200, 100, 150])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#283593')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#f5f5f5')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e8eaf6')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))
    
    return table


def _build_issues_section(
    issues: List[Dict[str, Any]],
    styles,
) -> List:
    """
    Build the issues section of the report with severity-colored entries.
    
    Args:
        issues: List of issue details
        styles: Paragraph styles
        
    Returns: List of report elements for the issues section
    """
    elements = []
    
    severity_colors = {
        'critical': colors.HexColor('#ffebee'),
        'moderate': colors.HexColor('#fff8e1'),
        'minor': colors.HexColor('#e8f5e9'),
    }
    
    for i, issue in enumerate(issues, 1):
        severity = issue.get('severity_level', 'minor')
        bg_color = severity_colors.get(severity, colors.white)
        
        issue_data = [[
            Paragraph(
                f"<b>{i}. [{severity.upper()}] {issue.get('issue_title', 'Issue')}</b>",
                styles['IssueText'],
            )
        ]]
        
        issue_table = Table(issue_data, colWidths=[460])
        issue_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        elements.append(issue_table)
        elements.append(Spacer(1, 6))
        
        # Add action items
        if issue.get('action_items'):
            for action in issue['action_items'][:3]:
                elements.append(Paragraph(
                    f"• {action}",
                    styles['SuggestionText'],
                ))
        
        elements.append(Spacer(1, 12))
    
    return elements


def generate_pdf_report(
    analysis_data: Dict[str, Any],
    filename: str = "ATS_Resume_Report.pdf",
) -> bytes:
    """
    Generate a complete PDF report from analysis data.
    
    Args:
        analysis_data: Complete analysis results dictionary containing:
            - ats_score: Overall ATS score
            - component_scores: Dict of individual component scores
            - detailed_feedback: List of issue details
            - suggestions: List of improvement suggestions
            - strengths: List of resume strengths
            - jd_match_analysis: Optional JD comparison results
        filename: Desired output filename
        
    Returns:
        Bytes of the generated PDF document
    """
    buffer = io.BytesIO()
    
    # Create the PDF document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50,
        title=filename,
        author="ATS Resume Analyzer",
    )
    
    styles = _get_styles()
    elements = []
    
    # Title
    elements.append(Paragraph(
        "ATS Resume Analysis Report",
        styles['ReportTitle'],
    ))
    elements.append(Paragraph(
        f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        styles['Normal'],
    ))
    elements.append(Spacer(1, 20))
    
    # Score Summary
    elements.append(Paragraph("Score Summary", styles['SectionHeader']))
    components = analysis_data.get('component_scores', {})
    ats_score = analysis_data.get('ats_score', 0)
    elements.append(_build_score_table(components, ats_score, styles))
    elements.append(Spacer(1, 20))
    
    # Score interpretation
    interpretation = analysis_data.get('interpretation', '')
    if interpretation:
        elements.append(Paragraph(
            f"<b>Interpretation:</b> {interpretation}",
            styles['ScoreText'],
        ))
        elements.append(Spacer(1, 20))
    
    # JD Match Analysis (if available)
    jd_match = analysis_data.get('jd_match_analysis') or analysis_data.get('jd_comparison')
    if jd_match:
        elements.append(Paragraph("Job Description Match Analysis", styles['SectionHeader']))
        match_pct = jd_match.get('match_percentage', 0)
        elements.append(Paragraph(
            f"<b>Match Percentage:</b> {match_pct:.1f}%",
            styles['ScoreText'],
        ))
        elements.append(Paragraph(
            f"<b>Semantic Similarity:</b> {jd_match.get('semantic_similarity', 0):.2f}",
            styles['ScoreText'],
        ))
        
        if jd_match.get('matched_keywords'):
            elements.append(Paragraph(
                f"<b>Matched Keywords:</b> {', '.join(jd_match['matched_keywords'][:10])}",
                styles['ScoreText'],
            ))
        
        if jd_match.get('missing_keywords'):
            elements.append(Paragraph(
                f"<b>Missing Keywords:</b> {', '.join(jd_match['missing_keywords'][:10])}",
                styles['ScoreText'],
            ))
        
        if jd_match.get('skills_gap'):
            elements.append(Paragraph(
                f"<b>Skills Gap:</b> {', '.join(jd_match['skills_gap'][:8])}",
                styles['ScoreText'],
            ))
        
        elements.append(Spacer(1, 20))
    
    # Detailed Feedback
    issues = analysis_data.get('detailed_feedback', [])
    if issues:
        elements.append(Paragraph("Detailed Feedback & Issues", styles['SectionHeader']))
        elements.extend(_build_issues_section(issues, styles))
        elements.append(Spacer(1, 10))
    
    # Suggestions
    suggestions = analysis_data.get('suggestions', [])
    if suggestions:
        elements.append(Paragraph("Improvement Suggestions", styles['SectionHeader']))
        for i, suggestion in enumerate(suggestions[:10], 1):
            elements.append(Paragraph(
                f"{i}. {suggestion}",
                styles['SuggestionText'],
            ))
        elements.append(Spacer(1, 10))
    
    # Strengths
    strengths = analysis_data.get('strengths', [])
    if strengths:
        elements.append(Paragraph("Resume Strengths", styles['SectionHeader']))
        for strength in strengths[:5]:
            elements.append(Paragraph(
                f"✅ {strength}",
                styles['SuggestionText'],
            ))
        elements.append(Spacer(1, 10))
    
    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    logger.info(f"Generated PDF report ({len(pdf_bytes)} bytes)")
    return pdf_bytes