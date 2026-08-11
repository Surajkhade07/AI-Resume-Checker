import asyncio
import logging
import os
from contextlib import asynccontextmanager

import spacy
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentence_transformers import SentenceTransformer

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


# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("ats resume scorer")


# ---------------------------------------------------------
# spaCy loader
# ---------------------------------------------------------

async def _load_spacy():
    logger.info(
        "Loading spaCy NLP model: %s",
        SPACY_MODEL_PRIMARY,
    )

    try:
        nlp = await asyncio.to_thread(
            spacy.load,
            SPACY_MODEL_PRIMARY,
        )

        logger.info(
            "Successfully loaded spaCy model: %s",
            SPACY_MODEL_PRIMARY,
        )

        return nlp

    except OSError:
        logger.warning(
            "%s not found. Falling back to %s",
            SPACY_MODEL_PRIMARY,
            SPACY_MODEL_SECONDARY,
        )

        try:
            nlp = await asyncio.to_thread(
                spacy.load,
                SPACY_MODEL_SECONDARY,
            )

            logger.info(
                "Successfully loaded fallback spaCy model: %s",
                SPACY_MODEL_SECONDARY,
            )

            return nlp

        except Exception as e:
            logger.exception(
                "Failed to load spaCy fallback: %s",
                e,
            )

            logger.warning(
                "Using blank English spaCy model instead."
            )

            return spacy.blank("en")

    except Exception as e:
        logger.exception(
            "Unexpected error loading spaCy model: %s",
            e,
        )

        logger.warning(
            "Using blank English spaCy model instead."
        )

        return spacy.blank("en")


# ---------------------------------------------------------
# Sentence Transformer loader
# ---------------------------------------------------------

async def _load_embedder():
    logger.info(
        "Loading Sentence Transformer: %s",
        SENTENCE_TRANSFORMER_MODEL,
    )

    try:
        embedder = await asyncio.to_thread(
            SentenceTransformer,
            SENTENCE_TRANSFORMER_MODEL,
            device="cpu",
        )

        logger.info(
            "Successfully loaded Sentence Transformer: %s",
            SENTENCE_TRANSFORMER_MODEL,
        )

        return embedder

    except Exception as e:
        logger.exception(
            "Failed to load Sentence Transformer: %s",
            e,
        )

        # Don't crash the entire API if the embedding model fails.
        return None


# ---------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("========================================")
    logger.info("Starting ATS Resume Analysis API")
    logger.info("========================================")

    # In-memory job store
    app.state._job_results = {}

    # -----------------------------------------------------
    # Load spaCy
    # -----------------------------------------------------

    logger.info("STEP 1/2: Starting spaCy model loading...")

    nlp_model = await _load_spacy()

    app.state.nlp = nlp_model

    logger.info("STEP 1/2: spaCy loading completed.")

    # -----------------------------------------------------
    # Load Sentence Transformer
    # -----------------------------------------------------

    logger.info("STEP 2/2: Starting Sentence Transformer loading...")

    embedder_model = await _load_embedder()

    app.state.embedder = embedder_model

    if embedder_model is None:
        logger.warning(
            "Sentence Transformer is unavailable. "
            "Embedding functionality may not work."
        )
    else:
        logger.info(
            "STEP 2/2: Sentence Transformer loading completed."
        )

    # -----------------------------------------------------
    # Startup complete
    # -----------------------------------------------------

    logger.info("========================================")
    logger.info("ALL MODELS LOADED")
    logger.info("API IS READY TO SERVE REQUESTS")
    logger.info("========================================")

    yield

    # -----------------------------------------------------
    # Shutdown
    # -----------------------------------------------------

    logger.info("Shutting down ATS Resume Analysis API...")

    # Release model references
    app.state.nlp = None
    app.state.embedder = None
    app.state._job_results = {}

    logger.info("API shutdown complete.")


# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------

app.include_router(router)


# ---------------------------------------------------------
# Local development
# ---------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )