"""
Configuration management for the ATS Resume Analyzer API.
"""
import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Load .env from backend/ (canonical) → project root → /app (container runtime)
try:
    from dotenv import load_dotenv

    _HERE = Path(__file__).resolve().parent
    _BACKEND_DIR = _HERE.parent
    _PROJECT_ROOT = _BACKEND_DIR.parent
    _ENV_CANDIDATES = [
        _BACKEND_DIR / '.env',
        _PROJECT_ROOT / '.env',
        Path('/app/.env'),
    ]
    _ENV_PATH = next((p for p in _ENV_CANDIDATES if p.is_file()), None)
    if _ENV_PATH:
        load_dotenv(_ENV_PATH, override=True)
        print(f"Loaded environment from: {_ENV_PATH}")
    else:
        print("Warning: No .env file found — relying on system environment variables")
except ImportError:
    print("dotenv not installed, relying on system environment variables")
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")

# ---------------------------------------------------------------------------
# API Metadata
# ---------------------------------------------------------------------------
APP_TITLE = os.getenv("APP_TITLE", "ATS RESUME ANALYZER API")
APP_VERSION = os.getenv("APP_VERSION", "2.0.0")
APP_DESCRIPTION = os.getenv(
    "APP_DESCRIPTION",
    "Advanced resume analysis against job descriptions using NLP + ML",
)
APP_ENVIRONMENT = os.getenv("APP_ENVIRONMENT", "development")

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
] or [
    "https://ats-resume-scorer-kappa.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
    "*" if APP_ENVIRONMENT == "development" else "",
]
ALLOWED_ORIGINS = [o for o in ALLOWED_ORIGINS if o]

# ---------------------------------------------------------------------------
# File Upload Limits
# ---------------------------------------------------------------------------
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "5"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

SUPPORTED_MIME_TYPES: Dict[str, str] = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

SUPPORTED_EXTENSIONS: Set[str] = {".pdf", ".doc", ".docx"}

# ---------------------------------------------------------------------------
# NLP / ML Models
# ---------------------------------------------------------------------------
SPACY_MODEL_PRIMARY = os.getenv("SPACY_MODEL_PRIMARY", "en_core_web_md")
SPACY_MODEL_SECONDARY = os.getenv("SPACY_MODEL_SECONDARY", "en_core_web_sm")
SENTENCE_TRANSFORMER_MODEL = os.getenv(
    "SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2"
)

BERT_MODEL_ENABLED = os.getenv("BERT_MODEL_ENABLED", "true").lower() == "true"
BERT_MODEL_PATH = os.getenv(
    "BERT_MODEL_PATH",
    str(Path(__file__).resolve().parent.parent / "bert_finetuned_model"),
)

# ---------------------------------------------------------------------------
# Scoring Weights
# ---------------------------------------------------------------------------
SCORE_WEIGHTS: Dict[str, float] = {
    "formatting": float(os.getenv("WEIGHT_FORMATTING", "20")),
    "keywords": float(os.getenv("WEIGHT_KEYWORDS", "25")),
    "content": float(os.getenv("WEIGHT_CONTENT", "25")),
    "skill_validation": float(os.getenv("WEIGHT_SKILL_VALIDATION", "15")),
    "ats_compatibility": float(os.getenv("WEIGHT_ATS_COMPATIBILITY", "15")),
}

JD_KEYWORD_WEIGHT = float(os.getenv("JD_KEYWORD_WEIGHT", "0.6"))
JD_SEMANTIC_WEIGHT = float(os.getenv("JD_SEMANTIC_WEIGHT", "0.4"))

# ---------------------------------------------------------------------------
# External API Keys
# ---------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = (
    os.getenv("SUPABASE_KEY", "")
    or os.getenv("SUPABASE_SERVICE_KEY", "")
    or os.getenv("SUPABASE_API_KEY", "")
)
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# ---------------------------------------------------------------------------
# Groq LLM Settings
# ---------------------------------------------------------------------------
GROQ_TIMEOUT_SECONDS = float(os.getenv("GROQ_TIMEOUT_SECONDS", "60"))
GROQ_CONNECT_TIMEOUT_SECONDS = float(os.getenv("GROQ_CONNECT_TIMEOUT_SECONDS", "30"))
GROQ_MAX_RETRIES = int(os.getenv("GROQ_MAX_RETRIES", "3"))
GROQ_RETRY_BACKOFF_FACTOR = float(os.getenv("GROQ_RETRY_BACKOFF_FACTOR", "1.0"))
GROQ_APP_RETRIES = int(os.getenv("GROQ_APP_RETRIES", "2"))
GROQ_FALLBACK_ENABLED = os.getenv("GROQ_FALLBACK_ENABLED", "true").lower() == "true"

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
JWT_SECRET = os.getenv("JWT_SECRET", SUPABASE_JWT_SECRET or "ats-resume-analyzer-secret-key")

# Google OAuth 2.0
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/auth/google/callback")
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "1000"))

# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def validate_config() -> List[str]:
    """Return a list of configuration warnings to surface on startup."""
    warnings: List[str] = []

    if not SUPABASE_URL:
        warnings.append("SUPABASE_URL is not set — database features will be unavailable")
    if not SUPABASE_KEY:
        warnings.append("SUPABASE_KEY is not set — database write operations will fail")
    if not GROQ_API_KEY:
        warnings.append("GROQ_API_KEY is not set — LLM resume parsing will fall back to local mode")

    if MAX_FILE_SIZE_MB < 1:
        warnings.append(f"MAX_FILE_SIZE_MB is {MAX_FILE_SIZE_MB}, which is too small. Using 5MB default.")
    elif MAX_FILE_SIZE_MB > 50:
        warnings.append(f"MAX_FILE_SIZE_MB is {MAX_FILE_SIZE_MB}, which is very large. Consider reducing.")

    total_weight = sum(SCORE_WEIGHTS.values())
    if abs(total_weight - 100.0) > 0.01:
        warnings.append(f"SCORE_WEIGHTS total is {total_weight}, expected 100. Scores may be skewed.")

    if APP_ENVIRONMENT not in ("development", "staging", "production"):
        warnings.append(f"APP_ENVIRONMENT is '{APP_ENVIRONMENT}', expected dev/staging/prod")

    return warnings