from typing import List, Dict, Optional
import numpy as np
import spacy
from sentence_transformers import SentenceTransformer

from backend.util.matching import fuzzy_match_keywords, normalize_skill
from rapidfuzz import fuzz


def calculate_semantic_similarity(
    resume_text: str, jd_text: str, embedder: Optional[SentenceTransformer] = None
) -> float:
    if not resume_text or not jd_text:
        return 0.0

    if embedder is not None:
        try:
            resume_emb = embedder.encode(resume_text[:5000], convert_to_tensor=False)
            jd_emb     = embedder.encode(jd_text[:5000], convert_to_tensor=False)

            similarity = np.dot(resume_emb, jd_emb) / (
                np.linalg.norm(resume_emb) * np.linalg.norm(jd_emb) + 1e-9
            )
            return float(np.clip(similarity, 0.0, 1.0))
        except Exception:
            pass

    # Fallback to fuzzy token set ratio if embedder is unavailable
    ratio = fuzz.token_set_ratio(resume_text[:3000], jd_text[:3000])
    return float(ratio / 100.0)


def identify_matched_keywords(
    resume_keywords: List[str], jd_keywords: List[str]
) -> List[str]:
    result = fuzzy_match_keywords(resume_keywords or [], jd_keywords or [], threshold=80)
    return result['matched']


def identify_missing_keywords(
    resume_keywords: List[str], jd_keywords: List[str], top_n: int = 15
) -> List[str]:
    result = fuzzy_match_keywords(resume_keywords or [], jd_keywords or [], threshold=80)
    return result['missing'][:top_n]


def analyze_skills_gap(
    resume_skills: List[str], jd_text: str, nlp: Optional[spacy.Language] = None
) -> List[str]:
    jd_skills = set()

    if nlp is not None:
        try:
            doc = nlp(jd_text[:5000])
            for ent in doc.ents:
                if ent.label_ in ['PRODUCT', 'ORG', 'LANGUAGE']:
                    jd_skills.add(ent.text.lower())

            for chunk in doc.noun_chunks:
                ct = chunk.text.lower().strip()
                if 1 <= len(ct.split()) <= 4:
                    jd_skills.add(ct)
        except Exception:
            pass

    if not jd_skills:
        # Simple word token fallback
        for word in jd_text.split():
            cleaned = word.strip('.,;:!?()[]{}"\'').lower()
            if len(cleaned) > 2:
                jd_skills.add(cleaned)

    # Normalize resume skills for comparison
    resume_normalized = {normalize_skill(s) for s in (resume_skills or [])}

    gap = []
    for jd_skill in jd_skills:
        jd_norm = normalize_skill(jd_skill)

        # Check canonical match first
        if jd_norm in resume_normalized:
            continue

        # Then try fuzzy match against all resume skills
        best_score = max(
            (fuzz.token_sort_ratio(jd_norm, rs) for rs in resume_normalized),
            default=0,
        )
        if best_score < 75:
            gap.append(jd_skill)

    return sorted(gap)[:20]


def calculate_match_percentage(
    resume_keywords: List[str],
    jd_keywords: List[str],
    semantic_similarity: float,
) -> float:
    if not jd_keywords:
        return 0.0
    matched = identify_matched_keywords(resume_keywords, jd_keywords)
    keyword_overlap = len(matched) / len(jd_keywords)
    match_pct = (keyword_overlap * 0.6 + semantic_similarity * 0.4) * 100
    return float(np.clip(match_pct, 0.0, 100.0))


def compare_resume_with_jd(
    resume_text: str,
    resume_keywords: List[str],
    resume_skills: List[str],
    jd_text: str,
    jd_keywords: List[str],
    embedder: Optional[SentenceTransformer] = None,
    nlp: Optional[spacy.Language] = None,
) -> Dict:
    semantic_similarity = calculate_semantic_similarity(resume_text, jd_text, embedder)
    matched_keywords    = identify_matched_keywords(resume_keywords, jd_keywords)
    missing_keywords    = identify_missing_keywords(resume_keywords, jd_keywords)
    skills_gap          = analyze_skills_gap(resume_skills, jd_text, nlp)
    match_percentage    = calculate_match_percentage(
        resume_keywords, jd_keywords, semantic_similarity
    )

    return {
        'match_percentage':    round(match_percentage, 1),
        'semantic_similarity': round(semantic_similarity, 2),
        'matched_keywords':    matched_keywords,
        'missing_keywords':    missing_keywords,
        'skills_gap':          skills_gap,
    }