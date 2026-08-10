import re
import spacy
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import Dict, List, Optional, Tuple

from backend.util.file_utils import log_warning
from backend.core.config import SENTENCE_TRANSFORMER_MODEL
from backend.util.matching import fuzzy_match_keywords

ZIP_CODE_PATTERN = r'\b\d{5}(?:-\d{4})?\b'

STREET_ADDRESS_PATTERN = (
    r'\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+'
    r'(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir|Way|Place|Pl)\b'
)

def _tier_score(n: float, tiers: list) -> float:
    for threshold, pts in tiers:
        if n >= threshold:
            return pts
    return 0.0

# Tech stack, libraries, acronyms, and common terms that spaCy NER falsely classifies as locations (GPE/LOC)
TECH_AND_NON_LOCATION_TERMS = {
    'numpy', 'seaborn', 'pandas', 'pytorch', 'tensorflow', 'keras', 'streamlit',
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'golang', 'rust', 'ruby', 'php',
    'ann', 'cnn', 'rnn', 'lstm', 'gru', 'rag', 'gans', 'gan', 'agentic ai', 'genai', 'llm', 'llms',
    'sql', 'mysql', 'postgresql', 'postgres', 'sqlite', 'mongodb', 'redis', 'nosql', 'oracle',
    'git', 'github', 'gitlab', 'docker', 'kubernetes', 'k8s', 'aws', 'azure', 'gcp', 'ci/cd',
    'linux', 'unix', 'scikit-learn', 'sklearn', 'matplotlib', 'power bi', 'powerbi', 'tableau',
    'excel', 'jupyter', 'jupyter notebook', 'vs code', 'vscode', 'html', 'css', 'sass', 'tailwind',
    'bert', 'gpt', 'nlp', 'cv', 'ai', 'ml', 'deep learning', 'machine learning',
    'model evaluation', 'predictive analytics', 'data visualization', 'api', 'rest', 'graphql',
    'json', 'devops', 'agile', 'scrum', 'fastapi', 'flask', 'django', 'node', 'nodejs',
    'react', 'reactjs', 'express', 'spring', 'springboot', 'vue', 'angular',
    'computer science', 'engineering', 'bachelor', 'master', 'phd', 'b.tech', 'm.tech', 'b.e', 'bca', 'mca',
    'accuracy', 'precision', 'recall', 'f1', 'roc-auc', 'loss', 'epoch', 'cuda', 'gpu', 'cpu',
    'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
    'january', 'february', 'march', 'april', 'june', 'july', 'august', 'september', 'october', 'november', 'december',
    'present', 'current', 'experience', 'projects', 'education', 'skills', 'summary',
    'software engineer', 'data scientist', 'machine learning engineer', 'ai engineer',
    'supervised', 'unsupervised', 'reinforcement', 'neural', 'networks', 'network',
}

def _is_invalid_location(term: str) -> bool:
    cleaned = term.strip().lower()
    cleaned_alpha = re.sub(r'[^a-zA-Z\s]', '', cleaned).strip()

    # 1. Reject if has numbers or percentage (e.g. 89%, 100+, 2024)
    if any(char.isdigit() for char in term) or '%' in term or '+' in term:
        return True

    # 2. Reject short tokens / acronyms
    if len(cleaned_alpha) < 3:
        return True

    # 3. Reject if in tech blocklist
    if cleaned in TECH_AND_NON_LOCATION_TERMS or cleaned_alpha in TECH_AND_NON_LOCATION_TERMS:
        return True

    # 4. Reject if contains any technical keyword
    words = cleaned.split()
    for w in words:
        if w in TECH_AND_NON_LOCATION_TERMS and len(w) >= 3:
            return True

    return False

# Location/privacy detection
def detect_location_info(text: str, nlp: Optional[spacy.Language] = None) -> Dict:
    locations = []
    seen_texts = set()

    # 1. Street address regex matching (full addresses)
    for match in re.finditer(STREET_ADDRESS_PATTERN, text, re.IGNORECASE):
        matched_str = match.group().strip()
        if matched_str and matched_str.lower() not in seen_texts:
            seen_texts.add(matched_str.lower())
            locations.append({'text': matched_str, 'type': 'address', 'start': match.start()})

    # 2. ZIP code regex pattern (in address context)
    for match in re.finditer(ZIP_CODE_PATTERN, text):
        matched_str = match.group().strip()
        # Verify it looks like a real zip code (not a port like 8000 or year like 2024 or metric like 50000)
        start_idx = max(0, match.start() - 20)
        end_idx = min(len(text), match.end() + 20)
        ctx = text[start_idx:end_idx].lower()
        if any(w in ctx for w in ['st', 'ave', 'road', 'rd', 'suite', 'apt', 'city', 'state', 'il', 'ca', 'ny', 'tx', 'fl', 'pune', 'mumbai', 'bangalore', 'delhi', 'hyderabad', 'chennai']):
            if matched_str not in seen_texts:
                seen_texts.add(matched_str)
                locations.append({'text': matched_str, 'type': 'zip', 'start': match.start()})

    # 3. SpaCy NER on contact header ONLY (first 400 characters of resume), filtered against tech blocklist
    if nlp is not None:
        header_text = text[:450]
        try:
            doc = nlp(header_text)
            for ent in doc.ents:
                if ent.label_ in ['GPE', 'LOC']:
                    ent_clean = ent.text.strip()
                    if ent_clean and not _is_invalid_location(ent_clean):
                        if ent_clean.lower() not in seen_texts:
                            seen_texts.add(ent_clean.lower())
                            locations.append({'text': ent_clean, 'type': ent.label_.lower(), 'start': ent.start_char})
        except Exception:
            pass

    has_address = any(loc['type'] == 'address' for loc in locations)
    has_zip     = any(loc['type'] == 'zip'     for loc in locations)

    if has_address and has_zip:
        privacy_risk, penalty = 'high', 5.0
    elif has_address:
        privacy_risk, penalty = 'high', 4.0
    elif has_zip:
        privacy_risk, penalty = 'medium', 2.0
    elif len(locations) > 3:
        privacy_risk, penalty = 'medium', 2.0
    elif locations:
        privacy_risk, penalty = 'low', 0.0
    else:
        privacy_risk, penalty = 'none', 0.0

    recommendations = []
    if not locations:
        recommendations.append("No privacy concerns detected.")
    if has_address:
        recommendations.append("Remove full street addresses — ATS systems don't need this and it's a privacy risk.")
    if has_zip:
        recommendations.append("Remove zip codes — this level of location detail is unnecessary.")
    if privacy_risk in ('low', 'medium') and not has_address and not has_zip:
        recommendations.append("Consider keeping only 'City, State' in the contact header.")

    return {
        'location_found':     len(locations) > 0,
        'detected_locations': locations,
        'privacy_risk':       privacy_risk,
        'recommendations':    recommendations,
        'penalty_applied':    penalty,
    }

def _calculate_semantic_similarity(skill: str, text: str, embedder: Optional[SentenceTransformer]) -> float:
    if not skill or not text or embedder is None:
        return 0.0
    try:
        skill_vec = embedder.encode(skill, convert_to_tensor=False)
        # Split text into sentences for accurate semantic matching
        sentences = [s.strip() for s in re.split(r'[.\n•\-\*\;]', text) if len(s.strip()) > 10]
        if not sentences:
            sentences = [text[:300]]
        
        sent_vecs = embedder.encode(sentences[:10], convert_to_tensor=False)
        sims = [
            np.dot(skill_vec, sv) / (np.linalg.norm(skill_vec) * np.linalg.norm(sv) + 1e-9)
            for sv in sent_vecs
        ]
        return float(max(0.0, min(1.0, max(sims, default=0.0))))
    except Exception as e:
        log_warning(f"Similarity error for '{skill}': {e}", context='ats_scorer')
        return 0.0

def _skill_matches(
    skill: str,
    text: str,
    embedder: Optional[SentenceTransformer] = None,
    threshold: float = 0.55
) -> Tuple[bool, float]:
    if not skill or not text:
        return False, 0.0

    from backend.util.matching import get_skill_variants, SKILL_SYNONYMS, SKILL_ALIASES
    from rapidfuzz import fuzz

    text_lower = text.lower()
    variants = get_skill_variants(skill)
    
    # Collect synonyms and alias mappings
    synonyms = []
    for v in variants:
        synonyms.extend(SKILL_SYNONYMS.get(v, []))
        canon = SKILL_ALIASES.get(v)
        if canon:
            synonyms.extend(SKILL_SYNONYMS.get(canon, []))
            
    all_search_terms = list(dict.fromkeys(variants + synonyms))

    # Fast check 1: Exact word boundary or token match for any variant/synonym
    for term in all_search_terms:
        term_clean = term.strip().lower()
        if not term_clean:
            continue
        # Exact token match
        pattern = r'\b' + re.escape(term_clean) + r'\b'
        if re.search(pattern, text_lower):
            return True, 1.0
        # Substring in text for multi-word or compound terms
        if len(term_clean) > 3 and term_clean in text_lower:
            return True, 0.95

    # Fast check 2: RapidFuzz partial token matching
    for term in variants:
        if len(term) >= 3:
            ratio = fuzz.partial_ratio(term.lower(), text_lower)
            if ratio >= 82:
                return True, ratio / 100.0

    # Fast check 3: Semantic similarity if SentenceTransformer available
    if embedder is not None and len(skill) > 2:
        sim = _calculate_semantic_similarity(skill, text, embedder)
        if sim >= threshold:
            return True, sim

    return False, 0.0

# Skill validation
def validate_skills_with_projects(
    skills: List[str],
    projects: List[Dict],
    experience_entries: List[Dict],
    resume_text: Optional[str] = None,
    embedder: Optional[SentenceTransformer] = None,
    threshold: float = 0.55,
) -> Dict:
    if not skills:
        return {
            'validated_skills':      [],
            'unvalidated_skills':    [],
            'validation_percentage': 0.0,
            'skill_project_mapping': {},
            'validation_score':      0.0,
        }

    # Pre-build structured project items including technologies & descriptions
    project_items = []
    for p in projects:
        if isinstance(p, dict):
            title = p.get('title') or 'Project'
            desc = p.get('description', '')
            techs = ' '.join(p.get('technologies', []) or [])
            tools = ' '.join(p.get('tools', []) or [])
            skills_used = ' '.join(p.get('skills', []) or [])
            full_text = f"{title} {desc} {techs} {tools} {skills_used}"
            project_items.append((title, full_text))

    # Pre-build structured experience items including job title, company, bullet descriptions
    experience_items = []
    for e in experience_entries:
        if isinstance(e, dict):
            role = e.get('job_title', '')
            company = e.get('company', '')
            desc = e.get('description', '')
            techs = ' '.join(e.get('technologies', []) or [])
            label = f"{role} at {company}".strip(" at ") or "Work Experience"
            full_text = f"{role} {company} {desc} {techs}"
            experience_items.append((label, full_text))

    # If raw resume text is provided, extract project/experience paragraphs
    resume_body_lines = []
    if resume_text:
        for line in resume_text.split('\n'):
            line_str = line.strip()
            # Look for bullet points or descriptive statements outside the pure skills listing
            if len(line_str) > 15 and not line_str.lower().startswith('skills:'):
                resume_body_lines.append(line_str)
    resume_body_context = ' \n '.join(resume_body_lines)

    validated_skills      = []
    unvalidated_skills    = []
    skill_project_mapping = {}

    for skill in skills:
        matching_contexts = []
        max_similarity    = 0.0

        # 1. Check against projects
        for title, project_text in project_items:
            matched, sim = _skill_matches(skill, project_text, embedder, threshold)
            max_similarity = max(max_similarity, sim)
            if matched:
                matching_contexts.append(title)

        # 2. Check against experience roles
        for role_label, exp_text in experience_items:
            matched, sim = _skill_matches(skill, exp_text, embedder, threshold)
            max_similarity = max(max_similarity, sim)
            if matched and role_label not in matching_contexts:
                matching_contexts.append(role_label)

        # 3. Check against raw resume project/experience body text
        if not matching_contexts and resume_body_context:
            matched, sim = _skill_matches(skill, resume_body_context, embedder, threshold)
            if matched:
                max_similarity = max(max_similarity, sim)
                matching_contexts.append("Project / Work Experience Context")

        if matching_contexts:
            unique_contexts = list(dict.fromkeys(matching_contexts))
            validated_skills.append({
                'skill': skill,
                'projects': unique_contexts,
                'similarity': max_similarity if max_similarity > 0 else 1.0,
            })
            skill_project_mapping[skill] = unique_contexts
        else:
            unvalidated_skills.append(skill)
            skill_project_mapping[skill] = []

    validation_percentage = len(validated_skills) / len(skills) if skills else 0.0
    validation_score      = validation_percentage * 15.0

    return {
        'validated_skills':      validated_skills,
        'unvalidated_skills':    unvalidated_skills,
        'validation_percentage': validation_percentage,
        'skill_project_mapping': skill_project_mapping,
        'validation_score':      validation_score,
    }

#01: formatting score
def _calc_formatting_score(parsed_resume: Dict, text: str) -> float:

    score = 0.0


    exp_entries  = [e for e in parsed_resume.get('experience', []) if isinstance(e, dict)]
    edu_entries  = [e for e in parsed_resume.get('education', [])  if isinstance(e, dict)]
    skills       = parsed_resume.get('skills', [])
    summary      = parsed_resume.get('professional_summary', '')
    proj_entries = [p for p in parsed_resume.get('projects', [])   if isinstance(p, dict)]

    if exp_entries and any(e.get('job_title') or e.get('description') for e in exp_entries):
        score += 3.0
    if edu_entries:
        score += 2.0
    if len(skills) >= 3:
        score += 2.0
    if len(summary) > 30:
        score += 1.5
    if proj_entries:
        score += 1.5

    bullet_count = sum(
        1 for line in text.split('\n')
        if re.match(r'^\s*[•\-\*\◦]', line) or re.match(r'^\s*\d+\.', line)
    )
    score += _tier_score(bullet_count, [(15,5.0),(10,4.0),(5,3.0),(3,2.0),(1,1.0)])

    filled = sum(1 for has_it in [
        bool(exp_entries), bool(edu_entries), bool(skills),
        bool(summary.strip()), bool(proj_entries),
    ] if has_it)
    score += _tier_score(filled, [(4,5.0),(3,4.0),(2,3.0),(1,2.0)])

    return min(20.0, max(0.0, score))

#02 keyword score
def _calc_keywords_score(
    resume_keywords: List[str],
    skills: List[str],
    jd_keywords: Optional[List[str]] = None,
) -> float:
    score = 0.0

    score += _tier_score(len(resume_keywords), [(20,10.0),(15,8.0),(10,6.0),(5,4.0),(3,2.0)])
    score += _tier_score(len(skills),          [(15,10.0),(10,8.0),(7,6.0),(5,4.0),(3,2.0)])

    if jd_keywords:
        all_resume_terms = list(set(resume_keywords + skills))
        fuzzy_result     = fuzzy_match_keywords(all_resume_terms, jd_keywords, threshold=80)
        match_pct        = len(fuzzy_result['matched']) / len(jd_keywords) if jd_keywords else 0
        score += _tier_score(match_pct, [(0.7,5.0),(0.5,4.0),(0.3,3.0),(0.2,2.0),(0.1,1.0)])
    
    elif len(resume_keywords) >= 10:
        score += 3.0

    return min(25.0, max(0.0, score))

#3. CONTENT QUALITY SCORE
def _calc_content_score(
    text: str,
    action_verbs: List[str],
    grammar_results: Dict,
) -> float:
    
    score = 0.0

    score += _tier_score(len(action_verbs), [(15,10.0),(10,8.0),(7,6.0),(5,4.0),(3,2.0)])

    number_patterns = [
        r'\d+%',
        r'\$\d+',
        r'\d+[kKmMbB]',
        r'\d+\s*(?:users|customers|clients|projects|hours|days|months|years)',
        r'(?:increased|decreased|improved|reduced|grew|saved)\s+(?:by\s+)?\d+',
    ]
    achievement_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in number_patterns)
    score += _tier_score(achievement_count, [(10,5.0),(7,4.0),(5,3.0),(3,2.0),(1,1.0)])

    grammar_penalty = grammar_results.get('penalty_applied', 0.0)
    score += max(0.0, 10.0 - grammar_penalty / 2.0)

    return min(25.0, max(0.0, score))

#4. SKILL VALIDATION SCORE
def _calc_skill_validation_score(validation_results: Dict) -> float:
    return min(15.0, max(0.0, validation_results.get('validation_score', 0.0)))

#5. ATS COMPATIBILITY SCORE
def _calc_ats_compatibility_score(
    text: str,
    location_results: Dict,
    parsed_resume: Dict,
) -> float:

    score = 15.0

    #dedeuction01
    score -= location_results.get('penalty_applied', 0.0)

    #deduction02
    special_chars = len(re.findall(r'[│┤├┼┴┬╔╗╚╝═║╠╣╦╩╬]', text))
    if special_chars > 20:    score -= 2.0
    elif special_chars > 10:  score -= 1.0

    exp_entries  = [e for e in parsed_resume.get('experience', []) if isinstance(e, dict)]
    edu_entries  = [e for e in parsed_resume.get('education', [])  if isinstance(e, dict)]
    skills_count = len(parsed_resume.get('skills', []))

    exp_desc_len = sum(len(e.get('description', '')) for e in exp_entries)
    edu_desc_len = sum(len((e.get('degree') or '') + (e.get('institution') or '')) for e in edu_entries)  # Handle None to prevent string concatenation errors

    #deduction03
    short_sections = sum([
        bool(exp_entries) and exp_desc_len < 20,
        bool(edu_entries) and edu_desc_len < 20,
        bool(parsed_resume.get('skills')) and skills_count < 2,
    ])
    if short_sections >= 2:    score -= 2.0
    elif short_sections >= 1:  score -= 1.0

    if exp_entries and skills_count > 5:
        score += 1.0

    return min(15.0, max(0.0, score))

#Score aggregation and final interpretation
def calculate_overall_score(
    text: str,
    parsed_resume: Dict,
    skills: List[str],
    keywords: List[str],
    action_verbs: List[str],
    skill_validation_results: Dict,
    grammar_results: Dict,
    location_results: Dict,
    jd_keywords: Optional[List[str]] = None,
    experience_months: int = 0,
) -> Dict:

    formatting_score        = _calc_formatting_score(parsed_resume, text)
    keywords_score          = _calc_keywords_score(keywords, skills, jd_keywords)
    content_score           = _calc_content_score(text, action_verbs, grammar_results)
    skill_validation_score  = _calc_skill_validation_score(skill_validation_results)
    ats_compatibility_score = _calc_ats_compatibility_score(text, location_results, parsed_resume)

    COMPONENT_MAX = {
        'formatting': 20.0, 'keywords': 25.0, 'content': 25.0,
        'skill_validation': 15.0, 'ats_compatibility': 15.0,
    }

    formatting_pct        = (formatting_score        / COMPONENT_MAX['formatting'])        * 100.0
    keywords_pct          = (keywords_score          / COMPONENT_MAX['keywords'])          * 100.0
    content_pct           = (content_score           / COMPONENT_MAX['content'])           * 100.0
    skill_validation_pct  = (skill_validation_score  / COMPONENT_MAX['skill_validation'])  * 100.0
    ats_compatibility_pct = (ats_compatibility_score / COMPONENT_MAX['ats_compatibility']) * 100.0

    skills_keywords_pct = (keywords_pct * 0.6) + (skill_validation_pct * 0.4)

    base_score = (
        skills_keywords_pct   * 0.40 +
        content_pct           * 0.30 +
        formatting_pct        * 0.15 +
        ats_compatibility_pct * 0.15
    )

    penalties = {}
    bonuses   = {}
    score     = base_score

    if grammar_results.get('penalty_applied', 0.0) > 0:
        penalties['grammar'] = grammar_results['penalty_applied']

    if location_results.get('penalty_applied', 0.0) > 0:
        penalties['location_privacy'] = location_results['penalty_applied']

    validation_pct = skill_validation_results.get('validation_percentage', 0.0)
    if validation_pct >= 0.9:
        bonuses['excellent_skill_validation'] = 2.0
        score += 2.0
    elif validation_pct >= 0.8:
        bonuses['good_skill_validation'] = 1.0
        score += 1.0

    if grammar_results.get('total_errors', 0) == 0:
        bonuses['perfect_grammar'] = 1.0
        score += 1.0

    if jd_keywords and len(jd_keywords) > 0:
        all_resume_terms = list(set((keywords or []) + (skills or [])))
        fuzzy_result     = fuzzy_match_keywords(all_resume_terms, jd_keywords, threshold=80)
        missing_pct      = len(fuzzy_result['missing']) / len(jd_keywords)

        if missing_pct > 0.7:
            penalties['missing_jd_keywords'] = 15.0
            score -= 15.0
        elif missing_pct > 0.5:
            penalties['missing_jd_keywords'] = 10.0
            score -= 10.0
        elif missing_pct > 0.3:
            penalties['missing_jd_keywords'] = 5.0
            score -= 5.0

    overall_score = min(100.0, max(0.0, score))
    interpretation = _generate_score_interpretation(overall_score)

    return {
        'overall_score':           round(overall_score, 1),
        'formatting_score':        round(formatting_score, 1),
        'keywords_score':          round(keywords_score, 1),
        'content_score':           round(content_score, 1),
        'skill_validation_score':  round(skill_validation_score, 1),
        'ats_compatibility_score': round(ats_compatibility_score, 1),
        'overall_interpretation':  interpretation,
        'penalties':               penalties,
        'bonuses':                 bonuses,}

#Overall score calculation and interpretation
def generate_strengths(
    score_results: Dict,
    skill_validation_results: Dict,
    grammar_results: Dict,
) -> List[str]:

    strengths = []

    if score_results['formatting_score']       >= 16:
        strengths.append(' Well-structured with clear sections and bullet points')
    if score_results['keywords_score']          >= 20:
        strengths.append(' Strong keyword optimization and skills presence')
    if score_results['content_score']           >= 20:
        strengths.append(' Excellent use of action verbs and quantifiable achievements')
    if score_results['skill_validation_score']  >= 12:
        pct = skill_validation_results.get('validation_percentage', 0) * 100
        strengths.append(f' {pct:.0f}% of skills are validated by projects')
    if score_results['ats_compatibility_score'] >= 13:
        strengths.append(' Excellent ATS compatibility with clean formatting')
    if grammar_results.get('total_errors', 0)   == 0:
        strengths.append(' Error-free grammar and spelling')

    if not strengths:
        strengths.append('Your resume has potential - focus on the recommendations below')
    return strengths


#Critical issues that could cause ATS rejection
def generate_critical_issues(
    score_results: Dict,
    grammar_results: Dict,
    location_results: Dict,
) -> List[str]:
    issues = []

    critical_errors = len(grammar_results.get('critical_errors', []))
    if critical_errors > 0:
        issues.append(f' {critical_errors} critical grammar/spelling error(s) detected')
    if location_results.get('privacy_risk') == 'high':
        issues.append('High privacy risk: Remove detailed location information')
    if score_results['formatting_score']       < 10:
        issues.append(' Poor formatting: Add clear sections and bullet points')
    if score_results['keywords_score']         < 12:
        issues.append(' Insufficient keywords and skills')
    if score_results['skill_validation_score'] < 7:
        issues.append(' Most skills lack supporting evidence in projects')

    return issues


#Actionable improvements to enhance ATS performance
def generate_improvements(
    score_results: Dict,
    skill_validation_results: Dict,
) -> List[str]:
    improvements = []

    if 12 <= score_results['formatting_score']       < 16:
        improvements.append('Add more bullet points and improve section organization')
    if 14 <= score_results['keywords_score']          < 20:
        improvements.append('Include more relevant keywords and technical skills')
    if 14 <= score_results['content_score']           < 20:
        improvements.append('Add more quantifiable achievements and action verbs')
    if 7  <= score_results['skill_validation_score']  < 12:
        unvalidated_count = len(skill_validation_results.get('unvalidated_skills', []))
        improvements.append(f'Validate {unvalidated_count} skill(s) by adding relevant project details')
    if 9  <= score_results['ats_compatibility_score'] < 13:
        improvements.append('Simplify formatting for better ATS compatibility')

    return improvements

#Interpretation of overall score
def _generate_score_interpretation(overall_score: float) -> str:
    if overall_score >= 90:    return 'Excellent! Your resume is highly optimized for ATS systems.'
    elif overall_score >= 80:  return 'Great! Your resume should perform well with most ATS systems.'
    elif overall_score >= 70:  return 'Good! Your resume is ATS-friendly with room for minor improvements.'
    elif overall_score >= 60:  return 'Fair. Your resume needs some improvements to be fully ATS-compatible.'
    elif overall_score >= 50:  return 'Below Average. Significant improvements needed for ATS compatibility.'
    else:                      return 'Poor. Your resume requires major revisions to pass ATS screening.'