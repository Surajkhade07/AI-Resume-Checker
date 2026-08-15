"""
Fuzzy matching utilities for keyword and skill comparison.
Provides functions for fuzzy matching keywords and normalizing skill strings.
"""
from typing import Dict, List, Tuple
from rapidfuzz import fuzz


def normalize_skill(skill: str) -> str:
    """
    Normalize a skill string for comparison by lowercasing, stripping whitespace,
    and removing common punctuation.
    Args:
        skill: Raw skill string
    Returns: Normalized skill string
    """
    import re
    # Lowercase, strip, and remove punctuation (keep hyphens for compound terms)
    skill = skill.lower().strip()
    skill = re.sub(r'[^\w\s-]', '', skill)
    skill = re.sub(r'\s+', ' ', skill).strip()
    return skill


def fuzzy_match_keywords(
    resume_keywords: List[str],
    jd_keywords: List[str],
    threshold: int = 80,
) -> Dict[str, List[str]]:
    """
    Fuzzy match resume keywords against job description keywords.
    Uses token_sort_ratio from rapidfuzz for robust comparison.
    
    Args:
        resume_keywords: List of keywords extracted from the resume
        jd_keywords: List of keywords extracted from the job description
        threshold: Minimum similarity score (0-100) for a match
        
    Returns:
        Dict with 'matched' and 'missing' keyword lists
    """
    # Normalize all keywords for comparison
    resume_norm = {normalize_skill(k): k for k in resume_keywords if k}
    jd_norm = {normalize_skill(k): k for k in jd_keywords if k}
    
    matched = []
    missing = []
    matched_norms = set()
    
    # For each JD keyword, check if it matches any resume keyword
    for jd_norm, jd_orig in jd_norm.items():
        best_score = 0
        best_resume = None
        
        for res_norm, res_orig in resume_norm.items():
            score = fuzz.token_sort_ratio(jd_norm, res_norm)
            if score > best_score:
                best_score = score
                best_resume = res_orig
        
        if best_score >= threshold and best_resume:
            matched.append(jd_orig)
            matched_norms.add(jd_norm)
        else:
            missing.append(jd_orig)
    
    # Sort for consistent output
    matched.sort()
    missing.sort()
    
    return {
        'matched': matched,
        'missing': missing,
    }


