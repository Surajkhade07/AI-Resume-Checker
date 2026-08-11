import asyncio
import logging
import os
from contextlib import asynccontextmanager

import spacy
from fastapi import FastAPI
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


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("ats_resume_scorer")


async def _load_spacy():
    logger.info(
        "Loading spaCy model: %s",
        SPACY_MODEL_PRIMARY,
    )

    try:
        nlp = await asyncio.to_thread(
            spacy.load,
            SPACY_MODEL_PRIMARY,
        )

        logger.info(
            "spaCy model loaded: %s",
            SPACY_MODEL_PRIMARY,
        )

        return nlp

    except OSError:
        logger.warning(
            "spaCy model %s not found. Trying %s",
            SPACY_MODEL_PRIMARY,
            SPACY_MODEL_SECONDARY,
        )

        try:
            nlp = await asyncio.to_thread(
                spacy.load,
                SPACY_MODEL_SECONDARY,
            )

            logger.info(
                "Fallback spaCy model loaded: %s",
                SPACY_MODEL_SECONDARY,
            )

            return nlp

        except Exception as exc:
            logger.exception(
                "Fallback spaCy model failed: %s",
                exc,
            )

            return spacy.blank("en")

    except Exception as exc:
        logger.exception(
            "Unexpected spaCy loading error: %s",
            exc,
        )

        return spacy.blank("en")


async def _load_embedder():
    logger.info(
        "Loading Sentence Transformer: %s",
        SENTENCE_TRANSFORMER_MODEL,
    )

    try:
        from sentence_transformers import SentenceTransformer

        embedder = await asyncio.to_thread(
            SentenceTransformer,
            SENTENCE_TRANSFORMER_MODEL,
            device="cpu",
        )

        try:
            embedder.max_seq_length = 256
        except Exception:
            pass

        logger.info(
            "Sentence Transformer loaded: %s",
            SENTENCE_TRANSFORMER_MODEL,
        )

        return embedder

    except Exception as exc:
        logger.exception(
            "Sentence Transformer loading failed: %s",
            exc,
        )

        return None


async def initialize_models(app: FastAPI):
    app.state.models_ready = False
    app.state.models_error = None

    try:
        logger.info("STEP 1/2: Loading spaCy")

        app.state.nlp = await _load_spacy()

        logger.info("STEP 1/2 completed")

        logger.info(
            "STEP 2/2: Loading Sentence Transformer"
        )

        app.state.embedder = await _load_embedder()

        if app.state.embedder is None:
            app.state.models_error = (
                "Sentence Transformer failed to load."
            )

            app.state.models_ready = False

            logger.error(
                "AI models are not ready."
            )

            return

        app.state.models_ready = True
        app.state.models_error = None

        logger.info(
            "========================================"
        )
        logger.info(
            "ALL MODELS LOADED"
        )
        logger.info(
            "API IS READY"
        )
        logger.info(
            "========================================"
        )

    except Exception as exc:
        logger.exception(
            "Model initialization failed: %s",
            exc,
        )

        app.state.models_error = str(exc)
        app.state.models_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "========================================"
    )
    logger.info(
        "Starting ATS Resume Analysis API"
    )
    logger.info(
        "========================================"
    )

    app.state._job_results = {}

    app.state.nlp = None
    app.state.embedder = None

    app.state.models_ready = False
    app.state.models_error = None

    app.state.analysis_semaphore = asyncio.Semaphore(1)

    model_task = asyncio.create_task(
        initialize_models(app)
    )

    logger.info(
        "FastAPI server startup completed"
    )

    yield

    logger.info(
        "Shutting down ATS Resume Analysis API"
    )

    if not model_task.done():
        model_task.cancel()

        try:
            await model_task
        except asyncio.CancelledError:
            pass

    app.state.nlp = None
    app.state.embedder = None
    app.state._job_results = {}

    logger.info(
        "API shutdown complete"
    )


app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=(
        r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)


@app.get("/health")
async def root_health():
    return {
        "status": "healthy",
        "service": APP_NAME,
    }


@app.get("/ready")
async def root_ready():
    if not getattr(
        app.state,
        "models_ready",
        False,
    ):
        return {
            "status": "starting",
            "models_ready": False,
            "error": getattr(
                app.state,
                "models_error",
                None,
            ),
        }

    return {
        "status": "ready",
        "models_ready": True,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(
        os.getenv("PORT", "8000")
    )

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )