"""
Advanced ATS Resume Analyzer API — Main Application Entry Point.
Initializes FastAPI with middleware, model loading, and startup validation.
"""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core.config import (
    ALLOWED_ORIGINS,
    APP_DESCRIPTION,
    APP_ENVIRONMENT,
    APP_TITLE,
    APP_VERSION,
    LOG_LEVEL,
    LOG_FORMAT,
    BERT_MODEL_ENABLED,
    validate_config,
)
from backend.api.routes import router
from backend.core.middleware import register_middleware
from backend.services.model_loader import initialize_model_state

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
log_dir = Path(__file__).resolve().parent / 'logs'
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / 'ats_scorer.log'

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            log_file,
            delay=True,
        ),
    ],
)
logger = logging.getLogger('ats_resume_scorer')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler — runs on startup and shutdown.
    Loads NLP models, validates configuration, and initializes services.
    """
    # ---- STARTUP ----
    logger.info(f"{'='*50}")
    logger.info(f"Starting {APP_TITLE} v{APP_VERSION} ({APP_ENVIRONMENT} mode)")
    logger.info(f"{'='*50}")
    
    # Validate configuration
    config_warnings = validate_config()
    for warning in config_warnings:
        logger.warning(f"Config: {warning}")
    if not config_warnings:
        logger.info("Configuration validation passed")
    
    # Initialize lightweight app state. Heavier NLP models load lazily on demand.
    initialize_model_state(app.state)
    logger.info("Model loading deferred until a request needs NLP or embedding features")

    # Load BERT model (if enabled and available)
    if BERT_MODEL_ENABLED:
        from backend.services.bert_skill_extractor import get_model_info
        model_info = get_model_info()
        if model_info.get('model_exists'):
            logger.info(f"BERT model found at: {model_info['model_path']}")
        else:
            logger.info("BERT model not found — skill extraction will use spaCy only")
    
    logger.info("API is ready to serve requests; heavy NLP models will load on demand.")
    logger.info(f"{'='*50}")
    
    yield  # Application runs here
    
    # ---- SHUTDOWN ----
    logger.info("Shutting down API server...")
    logger.info("Goodbye!")


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url='/docs',
    redoc_url='/redoc',
    contact={
        "name": "ATS Resume Analyzer",
    },
   
)

# ---------------------------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
    expose_headers=['X-API-Key', 'X-RateLimit-Limit', 'X-RateLimit-Remaining'],
)

# ---------------------------------------------------------------------------
# Custom Middleware (rate limiting, logging, security headers)
# ---------------------------------------------------------------------------
register_middleware(app)

# ---------------------------------------------------------------------------
# Global Exception Handler
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred. Please try again later.",
            "error_type": type(exc).__name__,
            "path": request.url.path,
        },
    )

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
app.include_router(router)

# ---------------------------------------------------------------------------
# Root Endpoints & Cloud Health Probes (Render / Railway / AWS)
# ---------------------------------------------------------------------------
@app.get('/health')
async def root_health():
    """
    Root health check endpoint for cloud platforms (Render, Railway, Kubernetes).
    Returns HTTP 200 to confirm the application process is alive.
    """
    return {
        "status": "healthy",
        "service": APP_TITLE,
        "version": APP_VERSION,
    }


@app.get('/ready')
async def root_ready():
    """
    Root readiness check endpoint.
    """
    return {
        "status": "ready",
        "models_ready": True,
        "version": APP_VERSION,
    }


@app.get('/')
async def root():
    """Root endpoint with API overview."""
    return {
        'name': APP_TITLE,
        'version': APP_VERSION,
        'environment': APP_ENVIRONMENT,
        'endpoints': {
            'GET    /health':                         'Cloud health check (Render / Liveness probe)',
            'GET    /ready':                          'Readiness check',
            'POST   /api/v1/analyze-resume':          'Analyze a single resume',
            'POST   /api/v1/analyze-base64':          'Analyze resume from base64 data',
            'POST   /api/v1/batch-analyze':           'Analyze multiple resumes',
            'GET    /api/v1/batch/{job_id}':          'Get batch analysis status',
            'GET    /api/v1/batch-jobs':              'List all batch jobs',
            'GET    /api/v1/history':                 'Get user analysis history',
            'DELETE /api/v1/history/{id}':            'Delete a history entry',
            'GET    /api/v1/health':                  'Health check with detailed status',
            'POST   /api/v1/generate-pdf':            'Generate PDF report from data',
            'POST   /api/v1/generate-html-report':    'Generate HTML report from data',
            'POST   /api/v1/auth/login':              'Login and get JWT token',
            'POST   /api/v1/auth/api-key':            'Generate API key',
            'GET    /api/v1/cache/stats':             'Get cache statistics',
            'GET    /api/v1/models/bert':             'Get BERT model information',
            'GET    /api/v1/config':                  'Get current configuration',
        },
    }


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        'backend.main:app',
        host='0.0.0.0',
        port=8000,
        reload=(APP_ENVIRONMENT == 'development'),
        log_level=LOG_LEVEL.lower(),
    )