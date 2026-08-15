"""Resume and job description parsing using Groq LLM, with a local fallback parser."""
import os
import re
import json
import time
import logging
from typing import Dict, Optional

import httpx
from groq import Groq
from groq import (
    APIError,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
)

from backend.core.config import (
    GROQ_API_KEY,
    GROQ_TIMEOUT_SECONDS,
    GROQ_CONNECT_TIMEOUT_SECONDS,
    GROQ_MAX_RETRIES,
    GROQ_RETRY_BACKOFF_FACTOR,
    GROQ_APP_RETRIES,
    GROQ_FALLBACK_ENABLED,
)

logger = logging.getLogger('ats_resume_scorer')

GROQ_MODEL = 'llama-3.3-70b-versatile'

_client = None


def _get_client() -> Groq:
    """Get or create a singleton Groq client with explicit timeouts."""
    global _client
    if _client is None:
        api_key = os.getenv('GROQ_API_KEY') or GROQ_API_KEY

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable not set — "
                "add it to backend/.env (or export it) and restart the server"
            )

        timeout = httpx.Timeout(
            timeout=GROQ_TIMEOUT_SECONDS,
            connect=GROQ_CONNECT_TIMEOUT_SECONDS,
            read=GROQ_TIMEOUT_SECONDS,
            write=GROQ_TIMEOUT_SECONDS,
            pool=GROQ_TIMEOUT_SECONDS,
        )

        _client = Groq(
            api_key=api_key,
            timeout=timeout,
            max_retries=max(GROQ_MAX_RETRIES, 1),
        )
    return _client


RESUME_SYSTEM_PROMPT = (
    "You are a resume parser. Extract information from the resume "
    "and return ONLY a valid JSON object. No explanation, no markdown."
)

RESUME_USER_PROMPT = """Extract the following from this resume and return as JSON:
{{
  "name": "full name",
  "email": "email address",
  "phone": "phone number",
  "linkedin": "LinkedIn URL if present, otherwise null",
  "github": "GitHub URL if present, otherwise null",
  "professional_summary": "the full text of the Summary, Profile, About Me, Objective, or Professional Summary section at the top of the resume. Copy the ENTIRE paragraph exactly as written. If no such section exists, return an empty string.",
  "skills": ["list", "of", "skills"],
  "experience": [
    {{
      "job_title": "",
      "company": "",
      "start_date": "",
      "end_date": "",
      "duration_months": 0,
      "description": ""
    }}
  ],
  "education": [
    {{
      "degree": "",
      "institution": "",
      "year": ""
    }}
  ],
  "certifications": ["list of certifications"],
  "projects": [
    {{
      "title": "project name",
      "description": "what the project does and how it was built",
      "technologies": ["tech", "used"]
    }}
  ],
  "action_verbs": ["strong action verbs used in bullet points, e.g. developed, implemented, designed"],
  "keywords": ["important keywords and phrases from the resume for ATS matching"]
}}

Important instructions:
- For duration_months, calculate the number of months between start_date and end_date. If end_date is "Present" or "Current", calculate from start_date to now.
- For skills, extract ALL technical and soft skills mentioned anywhere in the resume.
- For action_verbs, find verbs that start bullet points or describe achievements.
- For keywords, extract noun phrases and technical terms relevant to ATS matching.
- Return ONLY valid JSON. No markdown code fences, no explanation.

Resume Text:
{raw_text}"""


_TRANSIENT_ERRORS = (
    APITimeoutError,
    APIConnectionError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.NetworkError,
    RateLimitError,
)


def _is_transient(exc: BaseException) -> bool:
    """Return True if the exception is a transient network/API error worth retrying."""
    return isinstance(exc, _TRANSIENT_ERRORS)


def _is_retryable_status(exc: APIError) -> bool:
    """Return True for API status codes that are generally retryable (429/5xx)."""
    status = getattr(exc, 'status_code', None)
    if status is None:
        return True
    return status in (429, 500, 502, 503, 504)


def _call_groq(client: Groq, system_prompt: str, user_prompt: str) -> str:
    """Call the Groq API with application-level retries and exponential backoff."""
    max_attempts = 1 + GROQ_APP_RETRIES
    last_exc: Optional[BaseException] = None

    for attempt in range(max_attempts):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt}
                ],
                temperature=0.0,
                max_tokens=4096,
            )
            return response.choices[0].message.content.strip()

        except _TRANSIENT_ERRORS as exc:
            last_exc = exc
            if isinstance(exc, APIError) and not _is_retryable_status(exc):
                raise
            if attempt < max_attempts - 1:
                backoff = min(
                    GROQ_RETRY_BACKOFF_FACTOR * (2 ** attempt),
                    30.0,
                )
                logger.warning(
                    "Groq API request failed (attempt %d/%d) — retrying in %.1fs. Error: %s",
                    attempt + 1, max_attempts, backoff, exc,
                )
                time.sleep(backoff)
            else:
                logger.error(
                    "Groq API request failed after %d attempts: %s",
                    max_attempts, exc,
                )
                raise

    if last_exc:
        raise last_exc
    raise APIError(message="Unknown error contacting Groq API")


# ---------------------------------------------------------------------------
# Local fallback parsers (used when the Groq API is unreachable)
# ---------------------------------------------------------------------------

_COMMON_SKILLS: list = [
    'python', 'java', 'c++', 'c#', 'javascript', 'typescript', 'html', 'css',
    'sass', 'scss', 'react', 'angular', 'vue.js', 'vue', 'nodejs', 'node.js',
    'express', 'django', 'flask', 'fastapi', 'spring boot', 'spring',
    'aws', 'amazon web services', 'azure', 'microsoft azure', 'gcp',
    'google cloud', 'containerization', 'terraform', 'jenkins',
    'git', 'github', 'gitlab', 'ci/cd', 'linux', 'unix', 'windows',
    'sql', 'postgresql', 'postgres', 'mysql', 'mongodb', 'redis',
    'elasticsearch', 'oracle', 'sqlite',
    'machine learning', 'deep learning', 'nlp', 'tensorflow', 'keras',
    'pytorch', 'scikit-learn', 'pandas', 'numpy', 'matplotlib', 'opencv',
    'rest api', 'restful', 'graphql', 'microservices', 'serverless',
    'power bi', 'tableau', 'excel', 'word', 'powerpoint',
    'agile', 'scrum', 'jira', 'trello', 'confluence',
    'data analysis', 'data science', 'data engineering',
    'devops', 'sre', 'qa', 'testing', 'selenium', 'pytest', 'jest',
    'communication', 'teamwork', 'leadership', 'problem solving',
    'critical thinking', 'time management', 'adaptability',
]

_ACTION_VERBS: list = [
    'developed', 'implemented', 'designed', 'created', 'built', 'deployed',
    'managed', 'led', 'coordinated', 'analyzed', 'optimized', 'improved',
    'reduced', 'increased', 'enhanced', 'configured', 'maintained',
    'tested', 'debugged', 'integrated', 'automated', 'streamlined',
    'established', 'facilitated', 'collaborated', 'mentored', 'trained',
    'engineered', 'architected', 'orchestrated', 'migrated', 'scaled',
    'refactored', 'troubleshot', 'assembled', 'documented', 'evaluated',
    'generated', 'recommended', 'resolved', 'spearheaded', 'oversaw',
    'supervised', 'coached', 'directed', 'administered', 'prepared',
]

_DEGREE_KEYWORDS = [
    'bachelor', 'master', 'b.tech', 'm.tech', 'b.e', 'm.e', 'b.sc', 'm.sc',
    'mba', 'ph.d', 'phd', 'associate', 'diploma', 'degree',
]

_SECTION_HEADERS = re.compile(
    r'(?:^|\n)\s*(experience|work\s+history|employment|professional\s+experience|'
    r'education|academic|skills|technical\s+skills|certifications|projects|'
    r'project\s+experience|summary|professional\s+summary|profile|about|'
    r'objective|achievements)\s*(?::|\n|\s* — |\s*-\s*\n)',
    re.IGNORECASE,
)


def _extract_email(text: str) -> Optional[str]:
    match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> Optional[str]:
    match = re.search(
        r'\+?\(?\d[\d\s().-]{7,}\d\b',
        text,
    )
    if match:
        phone = match.group(0).strip()
        digits = re.sub(r'\D', '', phone)
        if 7 <= len(digits) <= 15:
            return phone
    return None


def _extract_urls(text: str) -> Dict[str, Optional[str]]:
    urls = re.findall(r'https?://[^\s<>"\']+|www\.[^\s<>"\']+', text)
    linkedin = next((u for u in urls if 'linkedin' in u.lower()), None)
    github = next((u for u in urls if 'github' in u.lower()), None)
    return {'linkedin': linkedin, 'github': github}


def _find_skills(text: str) -> list:
    lowered = text.lower()
    found = []
    for skill in _COMMON_SKILLS:
        if skill in lowered and skill not in found:
            found.append(skill)
    return found


def _find_action_verbs(text: str) -> list:
    lowered = text.lower()
    found = []
    for verb in _ACTION_VERBS:
        if re.search(r'\b' + re.escape(verb) + r'\b', lowered) and verb not in found:
            found.append(verb)
    return found


def _split_sections(text: str) -> Dict[str, str]:
    """Split resume text into labelled sections using known headers."""
    sections: Dict[str, str] = {}
    matches = list(_SECTION_HEADERS.finditer(text))
    for i, m in enumerate(matches):
        header = m.group(1).strip().lower().replace(' ', '_')
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if header in ('experience', 'work_history', 'employment', 'professional_experience'):
            key = 'experience'
        elif header in ('education', 'academic'):
            key = 'education'
        elif header in ('skills', 'technical_skills'):
            key = 'skills'
        elif header in ('certifications',):
            key = 'certifications'
        elif header in ('projects', 'project_experience'):
            key = 'projects'
        elif header in ('summary', 'professional_summary', 'profile', 'about', 'objective', 'achievements'):
            key = 'summary'
        else:
            key = header
        sections[key] = sections.get(key, '') + '\n' + body

    if not sections:
        sections['summary'] = text

    sections.setdefault('_full_text', text)
    return sections


_DATE_RE = re.compile(
    r'(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b'
    r'|\b\d{1,2}/\d{4}\b|\b\d{4}\b)',
    re.IGNORECASE,
)


def _parse_experience(exp_text: str) -> list:
    """Extract experience entries from the experience section."""
    entries = []
    blocks = re.split(r'\n\s*\n|\n\s*[•\*-]\s*', exp_text)
    for block in blocks:
        block = block.strip()
        if not block or len(block) < 10:
            continue
        lines = [ln.strip() for ln in block.split('\n') if ln.strip()]
        title = lines[0] if lines else ''
        company = ''
        job_title = title
        m = re.search(r'^(.*?)\s+(?:at|—|-)\s+(.+)$', title, re.IGNORECASE)
        if m:
            job_title = m.group(1).strip()
            company = m.group(2).strip()
        dates = _DATE_RE.findall(block)
        start_date = dates[0] if dates else ''
        end_date = dates[1] if len(dates) > 1 else ''
        if 'present' in block.lower() and not end_date:
            end_date = 'Present'
        description = '\n'.join(lines[1:]) if len(lines) > 1 else ''
        entries.append({
            'job_title': job_title,
            'company': company,
            'start_date': start_date,
            'end_date': end_date,
            'duration_months': 0,
            'description': description,
        })
    return entries


def _parse_education(edu_text: str) -> list:
    entries = []
    blocks = re.split(r'\n\s*\n|\n\s*[•\*-]\s*', edu_text)
    for block in blocks:
        block = block.strip()
        if not block or len(block) < 5:
            continue
        lines = [ln.strip() for ln in block.split('\n') if ln.strip()]
        degree = ''
        institution = ''
        year = ''
        for line in lines:
            if not degree and re.search(r'\b(' + '|'.join(_DEGREE_KEYWORDS) + r')\b', line, re.IGNORECASE):
                degree = line
            elif not institution:
                institution = line
        dates = _DATE_RE.findall(block)
        if dates:
            year = dates[-1]
        if degree or institution:
            entries.append({
                'degree': degree or '',
                'institution': institution or '',
                'year': year,
            })
    return entries


def _parse_projects(proj_text: str) -> list:
    entries = []
    blocks = re.split(r'\n\s*\n|\n\s*[•\*-]\s*', proj_text)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = [ln.strip() for ln in block.split('\n') if ln.strip()]
        title = lines[0] if lines else ''
        description = '\n'.join(lines[1:]) if len(lines) > 1 else ''
        technologies = []
        tech_match = re.search(r'(?:tech(?:nolog(?:y|ies))?|stack|tools)[:\-]?\s*(.+)', block, re.IGNORECASE)
        if tech_match:
            technologies = [t.strip() for t in re.split(r'[,\n]', tech_match.group(1)) if t.strip()]
        if title or description:
            entries.append({
                'title': title,
                'description': description,
                'technologies': technologies,
            })
    return entries


def _parse_resume_locally(raw_text: str, nlp=None) -> Dict:
    """Regex-based resume parser used as a fallback when the Groq API is unreachable."""
    sections = _split_sections(raw_text)

    email = _extract_email(raw_text)
    phone = _extract_phone(raw_text)
    urls = _extract_urls(raw_text)

    name = ''
    for line in raw_text.splitlines():
        line = line.strip()
        if line and not line.lower().startswith(('email', 'phone', 'linkedin', 'github')):
            name = line
            break

    skills = _find_skills(raw_text)
    action_verbs = _find_action_verbs(raw_text)

    if sections.get('skills'):
        skills.extend(_find_skills(sections['skills']))
        seen = set()
        skills = [s for s in skills if not (s in seen or seen.add(s))]

    summary = sections.get('summary', '').strip()
    if not summary:
        summary = raw_text[:500].strip()

    experience = _parse_experience(sections.get('experience', ''))
    education = _parse_education(sections.get('education', ''))

    certs = []
    cert_section = sections.get('certifications', '')
    if cert_section:
        certs = [c.strip().lstrip('•-* ') for c in re.split(r',\n|;\n', cert_section) if c.strip()]
    if not certs:
        cert_keywords = ['aws', 'azure', 'gcp', 'google', 'python institute',
                         'cisco', 'comptia', 'pmp', 'six sigma', 'scrum master']
        for kw in cert_keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', raw_text, re.IGNORECASE):
                certs.append(kw.title())

    projects = _parse_projects(sections.get('projects', ''))

    keywords = list(skills)
    for verb in action_verbs:
        if verb not in keywords:
            keywords.append(verb)

    result = {
        'name': name,
        'email': email,
        'phone': phone,
        'linkedin': urls['linkedin'],
        'github': urls['github'],
        'professional_summary': summary,
        'skills': skills,
        'experience': experience,
        'education': education,
        'certifications': certs,
        'projects': projects,
        'action_verbs': action_verbs,
        'keywords': keywords,
        'parsed_via': 'local_fallback',
    }
    logger.warning("Resume parsing used the local fallback parser (Groq API unavailable).")
    return result


def _try_parse_json(text: str) -> Optional[dict]:
    """Parse JSON from the LLM response, stripping markdown code fences if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.index("\n") if "\n" in cleaned else len(cleaned)
        cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _safe_groq_parse(client: Groq, system_prompt: str, user_prompt: str) -> Dict:
    """Call the Groq API with retries."""
    return _call_groq(client, system_prompt, user_prompt)


def parse_resume(raw_text: str) -> Dict:
    """Parse a resume using Groq LLM, falling back to the local parser if necessary."""
    client = _get_client()
    prompt = RESUME_USER_PROMPT.format(raw_text=raw_text)

    try:
        raw_response = _call_groq(client, RESUME_SYSTEM_PROMPT, prompt)
        result = _try_parse_json(raw_response)
        if result is not None:
            return _validate_resume_result(result)

        logger.warning("Groq resume parse: first attempt returned invalid JSON, retrying...")
        strict_prompt = (
            "Your previous response was not valid JSON. "
            "Return ONLY the raw JSON object, no markdown, no explanation, no code fences.\n\n"
            + prompt
        )
        raw_response = _call_groq(client, RESUME_SYSTEM_PROMPT, strict_prompt)
        result = _try_parse_json(raw_response)
        if result is not None:
            return _validate_resume_result(result)

        logger.warning("Groq returned unparseable JSON after retry. Using local fallback parser.")
        if GROQ_FALLBACK_ENABLED:
            result = _parse_resume_locally(raw_text)
            return _validate_resume_result(result)
        raise ValueError(
            f"Groq returned unparseable response after retry. Raw response:\n{raw_response[:500]}"
        )

    except (APITimeoutError, APIConnectionError, httpx.TimeoutException,
            httpx.NetworkError, RateLimitError, APIError) as exc:
        logger.warning(
            "Groq API request failed with %s: %s. Falling back to local parser.",
            type(exc).__name__, exc,
        )
        if not GROQ_FALLBACK_ENABLED:
            raise
        result = _parse_resume_locally(raw_text)
        return _validate_resume_result(result)


JD_SYSTEM_PROMPT = (
    "You are a job description parser. Extract information and "
    "return ONLY a valid JSON object. No explanation, no markdown."
)

JD_USER_PROMPT = """Extract the following from this job description and return as JSON:
{{
  "job_title": "",
  "required_skills": ["list of must-have skills"],
  "preferred_skills": ["list of nice-to-have skills"],
  "experience_required": "",
  "education_required": "",
  "key_responsibilities": ["list of responsibilities"],
  "keywords": ["important keywords and phrases for ATS matching"]
}}

Important instructions:
- required_skills: skills explicitly stated as required or must-have.
- preferred_skills: skills stated as preferred, nice-to-have, or bonus.
- keywords: extract ALL important terms an ATS system would match against,
  including skills, technologies, certifications, and domain terms.
- Return ONLY valid JSON. No markdown code fences, no explanation.

Job Description Text:
{raw_text}"""

_REQUIRED_SIGNAL = re.compile(
    r'\b(?:required|must have|must-have|mandatory|prerequisite|prerequisites)\b',
    re.IGNORECASE,
)
_PREFERRED_SIGNAL = re.compile(
    r'\b(?:preferred|nice.to.have|nice to have|bonus|desirable|desired)\b',
    re.IGNORECASE,
)


def _parse_jd_locally(raw_text: str) -> Dict:
    """Regex-based job-description parser used as a fallback when the Groq API is unreachable."""
    job_title = ''
    title_match = re.search(
        r'(?:job\s*title|position|role)\s*[:—-]\s*(.+)', raw_text, re.IGNORECASE,
    )
    if title_match:
        job_title = title_match.group(1).strip()
    if not job_title:
        for line in raw_text.splitlines():
            line = line.strip()
            if line and len(line) < 100:
                job_title = line
                break

    all_skills_found = _find_skills(raw_text)

    required_skills = []
    preferred_skills = []
    for skill in all_skills_found:
        pattern = re.compile(re.escape(skill), re.IGNORECASE)
        for m in pattern.finditer(raw_text):
            start = max(0, m.start() - 200)
            context = raw_text[start:m.start()]
            if _PREFERRED_SIGNAL.search(context):
                if skill not in preferred_skills:
                    preferred_skills.append(skill)
                break
            elif _REQUIRED_SIGNAL.search(context):
                if skill not in required_skills:
                    required_skills.append(skill)
                break
        else:
            if skill not in required_skills:
                required_skills.append(skill)

    responsibilities = []
    for line in raw_text.splitlines():
        stripped = line.strip().lstrip('•-*  ')
        if stripped and re.search(
            r'\b(' + '|'.join(_ACTION_VERBS) + r')\b', stripped, re.IGNORECASE,
        ):
            responsibilities.append(stripped)
        if len(responsibilities) >= 8:
            break

    exp_match = re.search(
        r'(\d+\+?\s*years?\s*(?:of)?\s*(?:experience)?)', raw_text, re.IGNORECASE,
    )
    experience_required = exp_match.group(1).strip() if exp_match else ''

    education_required = ''
    edu_match = re.search(
        r'(bachelor[\'s]?|master[\'s]?|ph\.?d|mba|degree).{0,40}', raw_text, re.IGNORECASE,
    )
    if edu_match:
        education_required = edu_match.group(0).strip()

    keywords = list(all_skills_found)
    for term in re.findall(r'[A-Z][a-zA-Z+#]+', raw_text):
        term = term.strip()
        if term not in keywords and len(term) > 3:
            keywords.append(term)
        if len(keywords) >= 20:
            break

    logger.warning("JD parsing used the local fallback parser (Groq API unavailable).")
    return {
        'job_title': job_title,
        'required_skills': required_skills,
        'preferred_skills': preferred_skills,
        'experience_required': experience_required,
        'education_required': education_required,
        'key_responsibilities': responsibilities,
        'keywords': keywords,
        'parsed_via': 'local_fallback',
    }


def parse_job_description(raw_text: str) -> Dict:
    """Parse a job description using Groq LLM, falling back to the local parser."""
    client = _get_client()
    prompt = JD_USER_PROMPT.format(raw_text=raw_text)

    try:
        raw_response = _call_groq(client, JD_SYSTEM_PROMPT, prompt)
        result = _try_parse_json(raw_response)
        if result is not None:
            return _validate_jd_result(result)

        logger.warning("Groq JD parse: first attempt returned invalid JSON, retrying...")
        strict_prompt = (
            "Your previous response was not valid JSON. "
            "Return ONLY the raw JSON object, no markdown, no explanation, no code fences.\n\n"
            + prompt
        )
        raw_response = _call_groq(client, JD_SYSTEM_PROMPT, strict_prompt)
        result = _try_parse_json(raw_response)
        if result is not None:
            return _validate_jd_result(result)

        logger.warning("Groq returned unparseable JSON for JD after retry. Using local fallback parser.")
        if GROQ_FALLBACK_ENABLED:
            result = _parse_jd_locally(raw_text)
            return _validate_jd_result(result)
        raise ValueError(
            f"Groq returned unparseable response after retry. Raw response:\n{raw_response[:500]}"
        )

    except (APITimeoutError, APIConnectionError, httpx.TimeoutException,
            httpx.NetworkError, RateLimitError, APIError) as exc:
        logger.warning(
            "Groq API request failed with %s: %s. Falling back to local JD parser.",
            type(exc).__name__, exc,
        )
        if not GROQ_FALLBACK_ENABLED:
            raise
        result = _parse_jd_locally(raw_text)
        return _validate_jd_result(result)


def _validate_jd_result(result: dict) -> dict:
    """Validate and normalize the job description parsing result."""
    defaults = {
        "job_title": "",
        "required_skills": [],
        "preferred_skills": [],
        "experience_required": "",
        "education_required": "",
        "key_responsibilities": [],
        "keywords": [],
    }

    for key, default in defaults.items():
        if key not in result or result[key] is None:
            result[key] = default
        if isinstance(default, list) and not isinstance(result[key], list):
            result[key] = default
    return result


def _validate_resume_result(result: dict) -> dict:
    """Validate and normalize the resume parsing result."""
    defaults = {
        "name": "",
        "email": None,
        "phone": None,
        "linkedin": None,
        "github": None,
        "professional_summary": "",
        "skills": [],
        "experience": [],
        "education": [],
        "certifications": [],
        "projects": [],
        "action_verbs": [],
        "keywords": [],
    }
    for key, default in defaults.items():
        if key not in result or result[key] is None:
            result[key] = default
        if isinstance(default, list) and not isinstance(result[key], list):
            result[key] = default

    for exp in result.get("experience", []):
        if not isinstance(exp, dict):
            continue
        exp.setdefault("job_title", "")
        exp.setdefault("company", "")
        exp.setdefault("start_date", "")
        exp.setdefault("end_date", "")
        exp.setdefault("duration_months", 0)
        exp.setdefault("description", "")
        try:
            exp["duration_months"] = int(exp["duration_months"])
        except (ValueError, TypeError):
            exp["duration_months"] = 0

    for proj in result.get("projects", []):
        if not isinstance(proj, dict):
            continue
        proj.setdefault("title", "")
        proj.setdefault("description", "")
        proj.setdefault("technologies", [])

    return result