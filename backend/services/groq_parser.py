import os
import re
import json
import logging
from typing import Dict, Optional

from groq import Groq

logger = logging.getLogger('ats_resume_scorer')

GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')

_client = None

def _get_client() -> Optional[Groq]:
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        logger.warning("GROQ_API_KEY environment variable not set. Fallback parser will be used.")
        return None
    try:
        _client = Groq(api_key=api_key)
        return _client
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}")
        return None

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


def _call_groq(client: Groq, system_prompt: str, user_prompt: str) -> str:
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ],
        temperature=0.0,
        max_tokens=4096
    )
    return response.choices[0].message.content.strip()


def _try_parse_json(text: str) -> Optional[dict]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.index("\n") if "\n" in cleaned else len(cleaned)
        cleaned = cleaned[first_newline + 1:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON object substring
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            pass

    return None


def parse_resume(raw_text: str) -> Dict:
    client = _get_client()
    if client is not None:
        try:
            prompt = RESUME_USER_PROMPT.format(raw_text=raw_text[:12000])
            raw_response = _call_groq(client, RESUME_SYSTEM_PROMPT, prompt)
            result = _try_parse_json(raw_response)

            if result is not None:
                return _validate_resume_result(result)

            logger.warning("Groq resume parser: first attempt returned non-JSON, retrying...")
            strict_prompt = (
                "Your previous response was not valid JSON. "
                "Return ONLY the raw JSON object, no markdown, no explanation, no code fences.\n\n"
                + prompt
            )
            raw_response = _call_groq(client, RESUME_SYSTEM_PROMPT, strict_prompt)
            result = _try_parse_json(raw_response)
            if result is not None:
                return _validate_resume_result(result)

            logger.warning("Groq parser failed to produce JSON. Using fallback heuristic parser.")
        except Exception as exc:
            logger.error(f"Groq API error during resume parse: {exc}. Using fallback parser.")

    return _fallback_parse_resume(raw_text)


def parse_job_description(raw_text: str) -> Dict:
    client = _get_client()
    if client is not None:
        try:
            prompt = JD_USER_PROMPT.format(raw_text=raw_text[:12000])
            raw_response = _call_groq(client, JD_SYSTEM_PROMPT, prompt)
            result = _try_parse_json(raw_response)

            if result is not None:
                return _validate_jd_result(result)

            logger.warning("Groq JD parser: first attempt returned non-JSON, retrying...")
            strict_prompt = (
                "Your previous response was not valid JSON. "
                "Return ONLY the raw JSON object, no markdown, no explanation, no code fences.\n\n"
                + prompt
            )
            raw_response = _call_groq(client, JD_SYSTEM_PROMPT, strict_prompt)
            result = _try_parse_json(raw_response)
            if result is not None:
                return _validate_jd_result(result)

            logger.warning("Groq JD parser failed. Using fallback parser.")
        except Exception as exc:
            logger.error(f"Groq API error during JD parse: {exc}. Using fallback parser.")

    return _fallback_parse_jd(raw_text)


def _validate_jd_result(result: dict) -> dict:
    defaults = {
        "job_title": "",
        "required_skills": [],
        "preferred_skills": [],
        "experience_required": "",
        "education_required": "",
        "key_responsibilities": [],
        "keywords": [],
    }

    if not isinstance(result, dict):
        result = {}

    for key, default in defaults.items():
        if key not in result or result[key] is None:
            result[key] = default
        if isinstance(default, list) and not isinstance(result[key], list):
            result[key] = [str(result[key])] if result[key] else []

    return result


def _validate_resume_result(result: dict) -> dict:
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

    if not isinstance(result, dict):
        result = {}

    for key, default in defaults.items():
        if key not in result or result[key] is None:
            result[key] = default
        if isinstance(default, list) and not isinstance(result[key], list):
            result[key] = [str(result[key])] if result[key] else []

    # Validate experience entries
    valid_exp = []
    for exp in result.get("experience", []):
        if isinstance(exp, dict):
            exp.setdefault("job_title", "")
            exp.setdefault("company", "")
            exp.setdefault("start_date", "")
            exp.setdefault("end_date", "")
            exp.setdefault("description", "")
            try:
                exp["duration_months"] = int(exp.get("duration_months", 0))
            except (ValueError, TypeError):
                exp["duration_months"] = 0
            valid_exp.append(exp)
    result["experience"] = valid_exp

    # Validate project entries
    valid_proj = []
    for proj in result.get("projects", []):
        if isinstance(proj, dict):
            proj.setdefault("title", "")
            proj.setdefault("description", "")
            proj.setdefault("technologies", [])
            valid_proj.append(proj)
    result["projects"] = valid_proj

    return result


def _fallback_parse_resume(raw_text: str) -> Dict:
    """Fast regex-based fallback parser when Groq is unavailable or fails."""
    email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', raw_text)
    email = email_match.group(0) if email_match else None

    phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', raw_text)
    phone = phone_match.group(0) if phone_match else None

    linkedin_match = re.search(r'https?://(?:www\.)?linkedin\.com/in/[\w-]+', raw_text, re.IGNORECASE)
    linkedin = linkedin_match.group(0) if linkedin_match else None

    github_match = re.search(r'https?://(?:www\.)?github\.com/[\w-]+', raw_text, re.IGNORECASE)
    github = github_match.group(0) if github_match else None

    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    name = lines[0] if lines and len(lines[0]) < 50 else ""

    common_skills = [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "PHP", "Ruby", "Swift", "Kotlin",
        "React", "React.js", "Node.js", "Express", "Next.js", "Vue", "Angular", "HTML", "CSS", "Tailwind", "Bootstrap",
        "FastAPI", "Flask", "Django", "Spring Boot", ".NET", "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQLite",
        "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Git", "GitHub", "CI/CD", "Linux", "REST API", "GraphQL",
        "Machine Learning", "Deep Learning", "NLP", "Pandas", "NumPy", "Scikit-Learn", "TensorFlow", "PyTorch",
        "Agile", "Scrum", "Jira", "SQL", "NoSQL", "Microservices", "TDD", "System Design"
    ]
    detected_skills = [s for s in common_skills if re.search(r'\b' + re.escape(s) + r'\b', raw_text, re.IGNORECASE)]

    action_verb_list = [
        "developed", "built", "designed", "implemented", "created", "led", "managed", "optimized",
        "architected", "engineered", "integrated", "deployed", "scaled", "automated", "improved",
        "maintained", "orchestrated", "collaborated", "spearheaded", "reduced", "increased"
    ]
    detected_verbs = [v for v in action_verb_list if re.search(r'\b' + v + r'\b', raw_text, re.IGNORECASE)]

    experience = []
    projects = []

    lines = raw_text.split('\n')
    in_projects = False
    in_experience = False

    proj_text = []
    exp_text = []

    for line in lines:
        l = line.strip()
        lower = l.lower()
        if any(h in lower for h in ['project', 'personal projects', 'key projects']):
            in_projects = True
            in_experience = False
            continue
        elif any(h in lower for h in ['experience', 'work history', 'employment', 'internship']):
            in_experience = True
            in_projects = False
            continue
        elif any(h in lower for h in ['education', 'skills', 'certifications', 'summary', 'contact']):
            in_projects = False
            in_experience = False

        if in_projects and l:
            proj_text.append(l)
        if in_experience and l:
            exp_text.append(l)

    if proj_text:
        projects.append({
            "title": "Projects Section",
            "description": " ".join(proj_text[:10]),
            "technologies": detected_skills[:5]
        })

    if exp_text:
        experience.append({
            "job_title": "Professional Role",
            "company": "Company",
            "start_date": "",
            "end_date": "",
            "duration_months": 12,
            "description": " ".join(exp_text[:15])
        })
    elif len(raw_text) > 100:
        experience.append({
            "job_title": "Role",
            "company": "",
            "start_date": "",
            "end_date": "",
            "duration_months": 6,
            "description": raw_text[:500]
        })

    summary = ""
    summary_match = re.search(r'(?:summary|profile|about me|objective)[:\s\n]+(.*?)(?=\n\s*(?:skills|experience|education|projects)|\Z)', raw_text, re.IGNORECASE | re.DOTALL)
    if summary_match:
        summary = summary_match.group(1).strip()[:500]

    keywords = list(set(detected_skills + detected_verbs + ["Software", "Development", "Engineering", "Analysis"]))

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
        "github": github,
        "professional_summary": summary,
        "skills": detected_skills,
        "experience": experience,
        "education": [{"degree": "Degree", "institution": "University", "year": ""}],
        "certifications": [],
        "projects": projects,
        "action_verbs": detected_verbs,
        "keywords": keywords
    }


def _fallback_parse_jd(raw_text: str) -> Dict:
    """Fast regex-based fallback for JD parsing."""
    common_skills = [
        "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "React",
        "Node.js", "Next.js", "Vue", "Angular", "FastAPI", "Flask", "Django", "PostgreSQL",
        "MySQL", "MongoDB", "Redis", "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Git",
        "CI/CD", "Linux", "REST API", "GraphQL", "Machine Learning", "SQL"
    ]
    detected_skills = [s for s in common_skills if re.search(r'\b' + re.escape(s) + r'\b', raw_text, re.IGNORECASE)]

    return {
        "job_title": "Target Role",
        "required_skills": detected_skills[:10],
        "preferred_skills": detected_skills[10:15],
        "experience_required": "2+ years",
        "education_required": "Bachelor's Degree",
        "key_responsibilities": [],
        "keywords": list(set(detected_skills + ["Development", "Design", "Implementation", "Architecture"]))
    }