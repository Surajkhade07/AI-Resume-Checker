"""
ATS scoring engine that computes resume scores across multiple dimensions.
Uses configurable weights from core.config to calculate component and overall scores.
"""
import logging
from typing import Dict, List, Optional

from backend.core.config import SCORE_WEIGHTS

logger = logging.getLogger('ats_resume_scorer')


def calculate_formatting_score(parsed_data: Dict) -> float:
    """
    Score the resume's formatting based on structure, section headers, and layout.
    
    Args:
        parsed_data: Parsed resume data from Groq/resume parser
        
    Returns:
        Formatting score (0-100) based on structural completeness
    """
    score = 0.0
    max_score = 100.0
    
    # Check for presence of key sections
    sections_found = 0
    key_sections = ['skills', 'experience', 'education', 'professional_summary']
    
    for section in key_sections:
        if parsed_data.get(section):
            sections_found += 1
    
    score += (sections_found / len(key_sections)) * 40  # 40 points for section presence
    
    # Check for action verbs in experience (indicates good formatting)
    action_verbs = parsed_data.get('action_verbs', [])
    if action_verbs:
        verb_score = min(len(action_verbs) / 5, 1.0) * 20  # 20 points for action verbs
        score += verb_score
    
    # Check for quantified achievements via keywords
    keywords = parsed_data.get('keywords', [])
    quant_keywords = [k for k in keywords if any(c.isdigit() for c in k)]
    if quant_keywords:
        score += 15  # 15 points for quantified content
    
    # Check for certifications section
    if parsed_data.get('certifications'):
        score += 10  # 10 points for certifications
    
    # Check for projects section
    if parsed_data.get('projects'):
        score += 15  # 15 points for projects
    
    return min(score, max_score)


def calculate_keywords_score(
    resume_keywords: List[str],
    jd_keywords: Optional[List[str]] = None,
) -> float:
    """
    Calculate keyword optimization score based on keyword density and relevance.
    If JD keywords are provided, scores are based on overlap with JD requirements.
    
    Args:
        resume_keywords: List of keywords extracted from the resume
        jd_keywords: Optional list of keywords from the job description
        
    Returns:
        Keyword score (0-100)
    """
    if not resume_keywords:
        return 0.0
    
    # Base score on having a good variety of keywords
    base_score = min(len(resume_keywords) / 12, 1.0) * 60  # Up to 60 points for variety
    keyword_density_score = min(len(resume_keywords) / 25, 1.0) * 40  # Up to 40 points for density
    
    if jd_keywords:
        from rapidfuzz import fuzz
        matched = 0
        for jk in jd_keywords:
            if any(fuzz.partial_ratio(jk.lower(), rk.lower()) > 80 for rk in resume_keywords):
                matched += 1
        jd_overlap = (matched / len(jd_keywords)) * 100 if jd_keywords else 0.0
        return round(min(base_score * 0.4 + jd_overlap * 0.6, 100.0), 1)
    
    return round(min(base_score + keyword_density_score, 100.0), 1)


def calculate_content_score(parsed_data: Dict) -> float:
    """
    Score the resume content quality based on depth and completeness of each section.
    
    Args:
        parsed_data: Parsed resume data
        
    Returns:
        Content score (0-100)
    """
    score = 0.0
    
    # Score experience depth
    experience = parsed_data.get('experience', [])
    if experience:
        exp_score = min(len(experience) / 2, 1.0) * 25  # 25 points for experience entries
        for exp in experience:
            desc = exp.get('description', '')
            if desc and len(desc) > 40:
                exp_score += 5  # Bonus for detailed descriptions
        score += min(exp_score, 40)
    
    # Score education
    education = parsed_data.get('education', [])
    if education:
        score += 15  # 15 points for education section
    
    # Score professional summary
    summary = parsed_data.get('professional_summary', '')
    if summary:
        summary_score = min(len(summary) / 60, 1.0) * 20  # 20 points for summary
        score += summary_score
    
    # Score projects
    projects = parsed_data.get('projects', [])
    if projects:
        proj_score = min(len(projects) / 2, 1.0) * 15  # 15 points for projects
        score += proj_score
    
    # Score certifications
    certifications = parsed_data.get('certifications', [])
    if certifications:
        score += min(len(certifications) * 5, 10)  # 10 points for certifications
    
    return min(score, 100.0)


def calculate_skill_validation_score(validation_details: Dict) -> float:
    """
    Calculate skill validation score based on how well skills are backed by projects.
    
    Args:
        validation_details: Dict with validated/unvalidated skills breakdown
        
    Returns:
        Skill validation score (0-100)
    """
    if not validation_details:
        return 50.0
    validation_pct = validation_details.get('validation_pct', 0.0)
    validated_count = validation_details.get('validated_count', 0)
    
    # Base score from validation percentage
    score = validation_pct * 0.7  # 70% from validation rate
    
    # Bonus for having validated skills
    if validated_count >= 5:
        score += 20
    elif validated_count >= 3:
        score += 15
    elif validated_count >= 1:
        score += 10
    
    # Bonus for having skill-project mappings
    if validation_details.get('skill_project_mapping'):
        mappings = len(validation_details['skill_project_mapping'])
        score += min(mappings * 2, 10)
    
    return round(min(max(score, 0.0), 100.0), 1)


def calculate_ats_compatibility_score(parsed_data: Dict) -> float:
    """
    Calculate ATS compatibility score based on standard resume best practices.
    
    Args:
        parsed_data: Parsed resume data
        
    Returns:
        ATS compatibility score (0-100)
    """
    score = 50.0  # Start with a neutral base score
    
    # Check for contact information
    if parsed_data.get('email'):
        score += 15
    if parsed_data.get('phone'):
        score += 15
    if parsed_data.get('linkedin'):
        score += 10
    if parsed_data.get('github') or parsed_data.get('portfolio'):
        score += 10
    
    # Section structure penalties / checks
    if not parsed_data.get('professional_summary'):
        score -= 10
    if not parsed_data.get('skills'):
        score -= 15
    if not parsed_data.get('experience'):
        score -= 20
    
    return round(max(0.0, min(score, 100.0)), 1)


def compute_component_scores(
    parsed_data: Dict,
    jd_keywords: Optional[List[str]] = None,
    skill_validation: Optional[Dict] = None,
) -> Dict[str, float]:
    """
    Compute all component scores for a resume analysis.
    Returns scores scaled to their UI maximums:
    - formatting: max 20
    - keywords: max 25
    - content: max 25
    - skill_validation: max 15
    - ats_compatibility: max 15
    Total sum = 100.
    """
    resume_keywords = parsed_data.get('keywords', [])
    
    raw_formatting = calculate_formatting_score(parsed_data)
    raw_keywords = calculate_keywords_score(resume_keywords, jd_keywords)
    raw_content = calculate_content_score(parsed_data)
    raw_skill_val = calculate_skill_validation_score(skill_validation) if skill_validation else 50.0
    raw_ats_comp = calculate_ats_compatibility_score(parsed_data)
    
    # Scale raw 0-100 scores to component maxes
    scores = {
        'formatting': round((raw_formatting / 100.0) * SCORE_WEIGHTS.get('formatting', 20.0), 1),
        'keywords': round((raw_keywords / 100.0) * SCORE_WEIGHTS.get('keywords', 25.0), 1),
        'content': round((raw_content / 100.0) * SCORE_WEIGHTS.get('content', 25.0), 1),
        'skill_validation': round((raw_skill_val / 100.0) * SCORE_WEIGHTS.get('skill_validation', 15.0), 1),
        'ats_compatibility': round((raw_ats_comp / 100.0) * SCORE_WEIGHTS.get('ats_compatibility', 15.0), 1),
    }
    
    return scores


def compute_penalties_and_bonuses(
    parsed_data: Dict,
    component_scores: Dict[str, float],
    skill_validation: Optional[Dict] = None,
) -> tuple[Dict[str, int], Dict[str, int]]:
    """
    Compute itemized penalties and bonuses for display in the ScoreOverview component.
    """
    penalties = {}
    bonuses = {}
    
    # Check penalties
    if not parsed_data.get('professional_summary'):
        penalties['missing_summary'] = 5
    if not parsed_data.get('phone') or not parsed_data.get('email'):
        penalties['missing_contact_info'] = 4
    if len(parsed_data.get('action_verbs', [])) < 3:
        penalties['low_action_verbs'] = 3
    if skill_validation and skill_validation.get('validation_pct', 100) < 50:
        penalties['unvalidated_skills'] = 4
    if not parsed_data.get('projects') and not parsed_data.get('experience'):
        penalties['missing_experience'] = 6
        
    # Check bonuses
    if len(parsed_data.get('action_verbs', [])) >= 5:
        bonuses['strong_action_verbs'] = 4
    if parsed_data.get('certifications'):
        bonuses['certifications_listed'] = 3
    if parsed_data.get('linkedin') and (parsed_data.get('github') or parsed_data.get('portfolio')):
        bonuses['verified_profiles'] = 3
    if skill_validation and skill_validation.get('validation_pct', 0) >= 80:
        bonuses['high_skill_validation'] = 4
    if len(parsed_data.get('skills', [])) >= 10:
        bonuses['rich_skills_inventory'] = 2
        
    return penalties, bonuses


def compute_ats_score(component_scores: Dict[str, float]) -> float:
    """
    Compute the final ATS score from component scores.
    Since component scores are scaled to their weights (20+25+25+15+15=100),
    the overall score is their direct sum.
    """
    total = sum(component_scores.values())
    return round(min(max(total, 0.0), 100.0), 1)


def generate_score_interpretation(ats_score: float) -> str:
    """
    Generate a human-readable interpretation of the ATS score.
    """
    if ats_score >= 90:
        return "Excellent: Your resume is exceptionally well optimized for ATS parsers and recruiters."
    elif ats_score >= 75:
        return "Good: Your resume has solid ATS alignment with only minor refinements recommended."
    elif ats_score >= 60:
        return "Moderate: Your resume meets basic criteria but has several gaps that reduce search visibility."
    elif ats_score >= 40:
        return "Below Average: Major sections, keywords, or structure need significant improvement."
    else:
        return "Needs Overhaul: Key resume sections and ATS compatibility elements are missing."