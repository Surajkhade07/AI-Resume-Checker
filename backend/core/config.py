import os
from pathlib import Path
from dotenv import load_dotenv

try:
    from dotenv import load_dotenv   # load all environment variables from .env file and store them 
    load_dotenv()
except ImportError:                  # if not found code not crash and continue execution
    pass

# app information 
APP_NAME="AI Resume Checker"
APP_VERSION="1.0.0"
APP_DESCRIPTION="A web application that uses AI to analyze and evaluate resumes."

ALLOWED_ORIGINS = [
    "https://ats-resume-scorer-kappa.vercel.app"
]


#file
MAX_FILE_SIZE_MB = 5  # 5 MB
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # Maximum file size in bytes
MAX_FILE_COUNT = 5  # Maximum number of files allowed per upload

#supported MIME types for file uploads and their names
SUPPORTED_MIME_TYPES = {
    "application/pdf": "PDF",
    "application/msword": "DOC",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
    "text/plain": "TXT"
}

SUPPORTED_FILE_EXTENSIONS = {
    ".pdf",".doc",".docx",".txt"     # file extensions accepted for upload
}

SPACY_MODEL_PRIMARY = os.getenv("SPACY_MODEL_PRIMARY", "en_core_web_sm")    # py library for NLP tasks
SPACY_MODEL_SECONDARY = "en_core_web_sm"

SENTENCE_TRANSFORMER_MODEL = os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")
JD_KEYWORD_WEIGHT=0.6      # weight for keyword matching
JD_SEMANTIC_WEIGHT=0.4     # weight for semantic similarity

#score commponents weights
SCORE_COMPONENTS_WEIGHTS = {
    "formatting":20,
    "keywords":25,
    "content":25,
    "skill_validation":15,
    "ats_compliance":15

}

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
