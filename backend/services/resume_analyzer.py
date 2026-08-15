"""
Resume analyzer orchestrator that coordinates the full analysis pipeline.
Combines resume parsing, Groq LLM extraction, ATS scoring, JD matching,
feedback generation, and recommendations into a single analysis flow.
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.services.resume_parser import parse_resume_file
from backend.services.groq_parser import parse_resume, parse_job_description
from backend.services.ats_scorer import (
    compute_component_scores,
    compute_ats_score,
    compute_penalties_and_bonuses,
    generate_score_interpretation,
)
from backend.services.feedback_engine import generate_all_feedback, generate_issues_summary
from backend.services.model_loader import ensure_embedder, ensure_nlp_model
from backend.services.recommendation_engine import generate_recommendations

logger = logging.getLogger('ats_resume_scorer')


def _extract_text_from_file(file_data: bytes, filename: str) -> Tuple[str, Dict]:
    """
    Extract text and metadata from an uploaded resume file.
    """
    logger.info(f"Starting text extraction for: {filename}")
    text, metadata = parse_resume_file(file_data, filename)
    logger.info(f"Text extraction complete: {len(text)} chars from {filename}")
    return text, metadata


def _parse_resume_with_groq(raw_text: str) -> Dict:
    """
    Parse resume text using Groq LLM to extract structured data.
    """
    logger.info("Parsing resume with Groq LLM...")
    parsed_data = parse_resume(raw_text)

    method = parsed_data.pop('parsed_via', 'groq')
    if method != 'groq':
        logger.warning(
            f"Resume parsed via '{method}' fallback (Groq unavailable). "
            f"{len(parsed_data.get('skills', []))} skills, "
            f"{len(parsed_data.get('experience', []))} experiences detected locally."
        )
    else:
        logger.info(
            f"Groq parsing complete: {len(parsed_data.get('skills', []))} skills, "
            f"{len(parsed_data.get('experience', []))} experiences"
        )
    return parsed_data


def _parse_jd_with_groq(jd_text: str) -> Dict:
    """
    Parse job description text using Groq LLM to extract structured data.
    """
    logger.info("Parsing job description with Groq LLM...")
    jd_data = parse_job_description(jd_text)

    method = jd_data.pop('parsed_via', 'groq')
    if method != 'groq':
        logger.warning(
            f"Job description parsed via '{method}' fallback (Groq unavailable). "
            f"{len(jd_data.get('required_skills', []))} required skills detected locally."
        )
    else:
        logger.info(
            f"JD parsing complete: {len(jd_data.get('required_skills', []))} required skills, "
            f"{len(jd_data.get('keywords', []))} keywords"
        )
    return jd_data


def _perform_jd_matching(
    resume_text: str,
    parsed_data: Dict,
    jd_data: Dict,
    app_state,
) -> Optional[Dict]:
    """
    Perform JD matching analysis if both resume and JD data are available.
    """
    if not jd_data:
        return None
    
    logger.info("Performing JD matching analysis...")
    embedder = ensure_embedder(app_state)
    nlp = ensure_nlp_model(app_state)

    if embedder is None or nlp is None:
        logger.warning("JD matching skipped because NLP or embedding models are unavailable")
        return None
    
    try:
        from backend.services.jd_matcher import compare_resume_with_jd
    except ImportError as e:
        logger.warning(f"JD matcher unavailable: {e}")
        return None

    jd_match = compare_resume_with_jd(
        resume_text=resume_text,
        resume_keywords=parsed_data.get('keywords', []),
        resume_skills=parsed_data.get('skills', []),
        jd_text=jd_data.get('raw_text', ''),
        jd_keywords=jd_data.get('keywords', []),
        embedder=embedder,
        nlp=nlp,
    )

    logger.info(f"JD matching complete: {jd_match.get('match_percentage', 0):.1f}% match")
    return jd_match


def _compute_skill_validation(parsed_data: Dict) -> Dict:
    """
    Compute skill validation by checking which skills are backed by project/experience evidence.
    """
    skills = parsed_data.get('skills', [])
    experience = parsed_data.get('experience', [])
    projects = parsed_data.get('projects', [])
    
    # Collect all text from experiences and projects for validation
    evidence_text = ""
    for exp in experience:
        if isinstance(exp, dict):
            evidence_text += (exp.get('description', '') + ' ').lower()
    for proj in projects:
        if isinstance(proj, dict):
            evidence_text += (proj.get('description', '') + ' ').lower()
            evidence_text += ' '.join(proj.get('technologies', [])) + ' '
    
    validated = []
    unvalidated = []
    
    for skill in skills:
        skill_lower = str(skill).lower().strip()
        if skill_lower in evidence_text:
            validated.append(skill)
        else:
            unvalidated.append(skill)
    
    total = len(skills)
    validated_count = len(validated)
    validation_pct = (validated_count / total * 100) if total > 0 else 0.0
    
    # Build skill-project mapping
    skill_project_mapping = {}
    for skill in validated:
        skill_lower = str(skill).lower().strip()
        related_projects = []
        for proj in projects:
            if isinstance(proj, dict):
                techs = [str(t).lower() for t in proj.get('technologies', [])]
                if skill_lower in techs or skill_lower in proj.get('description', '').lower():
                    related_projects.append(proj.get('title', 'Project'))
        if related_projects:
            skill_project_mapping[skill] = related_projects
    
    return {
        'validated': [
            {
                'skill': s,
                'projects': skill_project_mapping.get(s, []),
                'similarity': 1.0,
            }
            for s in validated
        ],
        'unvalidated': unvalidated,
        'total': total,
        'validated_count': validated_count,
        'validation_pct': round(validation_pct, 1),
        'skill_project_mapping': skill_project_mapping,
    }


def _analyze_location_and_privacy(parsed_data: Dict, raw_text: str) -> Dict[str, Any]:
    """
    Analyze location data and privacy risk for candidate contact safety.
    """
    detected = []
    
    # Check for street address patterns
    street_pattern = re.compile(
        r'\b\d+\s+[A-Za-z0-9\s,.-]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Court|Ct)\b',
        re.IGNORECASE,
    )
    for match in street_pattern.findall(raw_text)[:3]:
        detected.append({'type': 'Full Street Address', 'text': match.strip()})
        
    # Check for zip/postal code patterns in header area
    zip_pattern = re.compile(r'\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b|\b\d{5}(?:-\d{4})?\b|\b\d{6}\b')
    for line in raw_text.splitlines()[:20]:
        zips = zip_pattern.findall(line)
        for z in zips[:2]:
            if not any(d['text'] == z for d in detected):
                detected.append({'type': 'Postal / Zip Code', 'text': z})

    privacy_risk = "none"
    penalty = 0.0
    recommendations = []
    
    if any(d['type'] == 'Full Street Address' for d in detected):
        privacy_risk = "high"
        penalty = 5.0
        recommendations.append("Remove exact street address to protect personal privacy. Modern ATS systems only require City, State / Country.")
    elif detected:
        privacy_risk = "medium"
        recommendations.append("Consider simplifying location to City, State/Country for standard remote and hybrid ATS matching.")
    else:
        privacy_risk = "none"

    return {
        'privacy_risk': privacy_risk,
        'detected_locations': detected,
        'recommendations': recommendations,
        'penalty_applied': penalty,
    }


def analyze_resume(
    file_data: bytes,
    filename: str,
    jd_text: Optional[str],
    app_state,
) -> Dict[str, Any]:
    """
    Main analysis pipeline that orchestrates the complete resume analysis.
    
    Args:
        file_data: Raw bytes of the uploaded resume file
        filename: Original filename of the resume
        jd_text: Optional job description text for JD matching
        app_state: FastAPI app state with loaded NLP models (nlp, embedder)
        
    Returns:
        Complete analysis result dictionary with all scores, feedback, and recommendations
    """
    logger.info(f"=== Starting analysis for: {filename} ===")
    
    # Step 1: Extract text from the uploaded file
    resume_text, metadata = _extract_text_from_file(file_data, filename)
    
    # Step 2: Parse resume with Groq LLM
    parsed_data = _parse_resume_with_groq(resume_text)
    parsed_data['raw_text'] = resume_text
    
    # Step 3: Parse job description if provided
    jd_data = None
    if jd_text and jd_text.strip():
        jd_data = _parse_jd_with_groq(jd_text)
        jd_data['raw_text'] = jd_text
    
    # Step 4: Compute skill validation
    skill_validation = _compute_skill_validation(parsed_data)
    
    # Step 5: Compute component scores & penalties/bonuses
    jd_keywords = jd_data.get('keywords', []) if jd_data else None
    component_scores = compute_component_scores(
        parsed_data=parsed_data,
        jd_keywords=jd_keywords,
        skill_validation=skill_validation,
    )
    penalties, bonuses = compute_penalties_and_bonuses(
        parsed_data=parsed_data,
        component_scores=component_scores,
        skill_validation=skill_validation,
    )
    
    # Step 6: Compute overall ATS score
    ats_score = compute_ats_score(component_scores)
    interpretation = generate_score_interpretation(ats_score)
    
    # Step 7: Perform JD matching if JD text was provided
    jd_match = None
    if jd_data:
        try:
            jd_match = _perform_jd_matching(resume_text, parsed_data, jd_data, app_state)
        except Exception as e:
            logger.warning(f"JD matching failed (continuing without it): {e}")
            jd_match = None
    
    # Step 8: Generate detailed feedback
    missing_keywords = jd_match.get('missing_keywords', []) if jd_match else None
    issues = generate_all_feedback(
        parsed_data=parsed_data,
        component_scores=component_scores,
        jd_keywords=jd_keywords,
        missing_keywords=missing_keywords,
        skill_validation=skill_validation,
    )
    issues_summary = generate_issues_summary(issues)
    
    # Step 9: Generate recommendations
    recommendations = generate_recommendations(
        parsed_data=parsed_data,
        component_scores=component_scores,
        issues=issues,
        jd_match=jd_match or {},
    )
    
    # Step 10: Build structured candidate profile and privacy analysis
    location_analysis = _analyze_location_and_privacy(parsed_data, resume_text)
    
    experience = parsed_data.get('experience', [])
    total_experience_months = sum(
        int(e.get('duration_months', 0))
        for e in experience
        if isinstance(e, dict) and str(e.get('duration_months', 0)).isdigit()
    )
    
    resume_profile = {
        'candidate_info': {
            'name': parsed_data.get('name', ''),
            'email': parsed_data.get('email', ''),
            'phone': parsed_data.get('phone', ''),
            'linkedin': parsed_data.get('linkedin', ''),
            'github': parsed_data.get('github', ''),
            'portfolio': parsed_data.get('portfolio', ''),
        },
        'professional_summary': parsed_data.get('professional_summary', ''),
        'experience': experience,
        'education': parsed_data.get('education', []),
        'projects': parsed_data.get('projects', []),
        'certifications': parsed_data.get('certifications', []),
        'action_verbs': parsed_data.get('action_verbs', []),
        'keywords': parsed_data.get('keywords', []),
        'total_experience_months': total_experience_months,
    }
    
    # Step 11: Build complete result matching all frontend variable expectations
    result = {
        # Core scores
        'ats_score': ats_score,
        'ATS_score': ats_score,
        'component_scores': component_scores,
        'interpretation': interpretation,
        
        # Recommendations & Feedback
        'recommendations': recommendations['recommendations'],
        'recommendation_summary': recommendations['recommendation_summary'],
        'estimated_improvement': recommendations['estimated_improvement'],
        'suggestions': recommendations['suggestions'],
        'strengths': recommendations['strengths'],
        'critical_issues': recommendations['critical_issues'],
        'warnings': recommendations['warnings'],
        'issues_summary': issues_summary,
        'detailed_feedback': [issue.dict() if hasattr(issue, 'dict') else issue for issue in issues],
        
        # Candidate Profile & Privacy
        'resume_profile': resume_profile,
        'parsed_data': parsed_data,
        'location_analysis': location_analysis,
        
        # Skill validation & Keywords
        'skill_validation_details': skill_validation,
        'keyword_match': round((component_scores.get('keywords', 0) / 25.0) * 100, 1),
        'missing_keywords': missing_keywords or [],
        'matched_keywords': jd_match.get('matched_keywords', []) if jd_match else [],
        'skills': parsed_data.get('skills', []),
        'experience_months': total_experience_months,
        
        # Score adjustments
        'penalties': penalties,
        'bonuses': bonuses,
        
        # JD matching
        'jd_match_analysis': jd_match,
        'jd_comparison': jd_match,
        'parsed_jd': jd_data,
        
        # Metadata
        'filename': filename,
        'metadata': metadata,
    }
    
    logger.info(f"=== Analysis complete for: {filename} (ATS Score: {ats_score:.1f}) ===")
    return result