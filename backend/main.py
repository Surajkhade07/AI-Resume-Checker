import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import (
    ALLOWED_ORIGINS,
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
    SPACY_MODEL_PRIMARY,
    SPACY_MODEL_SECONDARY,
    SENTENCE_TRANSFORMER_MODEL,
)
from backend.api.route import router

logger = logging.getLogger("ats resume scorer")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting ATS Resume Analysis API...")
    import asyncio
    import spacy
    from sentence_transformers import SentenceTransformer

    async def _load_spacy():
        logger.info(f"Loading spaCy NLP model: {SPACY_MODEL_PRIMARY}")
        try:
            nlp = await asyncio.to_thread(spacy.load, SPACY_MODEL_PRIMARY)
            logger.info(f"Loaded {SPACY_MODEL_PRIMARY}")
            return nlp
        except OSError:
            logger.warning(f"{SPACY_MODEL_PRIMARY} not found — falling back to {SPACY_MODEL_SECONDARY}")
            try:
                nlp = await asyncio.to_thread(spacy.load, SPACY_MODEL_SECONDARY)
                logger.info(f"Loaded {SPACY_MODEL_SECONDARY} (fallback)")
                return nlp
            except Exception as e:
                logger.error(f"Failed to load spaCy fallback: {e}. Using blank English model.")
                return spacy.blank("en")

    async def _load_embedder():
        logger.info(f"Loading Sentence Transformer: {SENTENCE_TRANSFORMER_MODEL}")
        try:
            embedder = await asyncio.to_thread(SentenceTransformer, SENTENCE_TRANSFORMER_MODEL, device="cpu")
            logger.info(f"Loaded {SENTENCE_TRANSFORMER_MODEL}")
            return embedder
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer: {e}")
            return None

    # Load sequentially instead of in parallel — avoids both models
    # peaking in memory at the same time during startup.
    nlp_model = await _load_spacy()
    app.state.nlp = nlp_model

    embedder_model = await _load_embedder()
    app.state.embedder = embedder_model

    # In-memory job store for short-lived job tracking (job_id -> result/status)
    app.state._job_results = {}

    logger.info("All models loaded. API is ready to serve requests.")

    yield
    logger.info("Shutting down the API...")

app=FastAPI(
        title=APP_NAME,
        description=APP_DESCRIPTION,
        version=APP_VERSION,
        lifespan=lifespan,
        docs_url='/docs',
        redoc_url='/redoc'
    )


app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(router)

if __name__=='__main__':
        import uvicorn
        uvicorn.run(
            'backend.main:app',
            host='0.0.0.0',
            port=8000,
            reload=True              #Auto restart on code changes
        )