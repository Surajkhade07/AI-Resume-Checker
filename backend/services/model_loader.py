"""Helpers for lazy-loading NLP and embedding models."""
import logging
import time
from typing import Any, Dict

logger = logging.getLogger("ats_resume_scorer")


def initialize_model_state(app_state: Any) -> Dict[str, str]:
    """Ensure the app state has the expected model-tracking attributes."""
    if not hasattr(app_state, "model_status"):
        app_state.model_status = {"nlp": "idle", "embedder": "idle"}
    if not hasattr(app_state, "nlp"):
        app_state.nlp = None
    if not hasattr(app_state, "embedder"):
        app_state.embedder = None
    if not hasattr(app_state, "_nlp_loading"):
        app_state._nlp_loading = False
    if not hasattr(app_state, "_embedder_loading"):
        app_state._embedder_loading = False
    if not hasattr(app_state, "model_errors"):
        app_state.model_errors = {}
    return app_state.model_status


def ensure_nlp_model(app_state: Any):
    """Load the spaCy NLP model on demand, reusing a cached instance."""
    initialize_model_state(app_state)
    if app_state.nlp is not None:
        app_state.model_status["nlp"] = "ready"
        return app_state.nlp

    if app_state._nlp_loading:
        return None

    app_state._nlp_loading = True
    app_state.model_status["nlp"] = "loading"
    try:
        import spacy

        from backend.core.config import SPACY_MODEL_PRIMARY, SPACY_MODEL_SECONDARY

        start_time = time.time()
        try:
            app_state.nlp = spacy.load(SPACY_MODEL_PRIMARY)
            logger.info(f"Loaded {SPACY_MODEL_PRIMARY} in {time.time() - start_time:.2f}s")
        except OSError:
            logger.warning(
                f"{SPACY_MODEL_PRIMARY} not found - falling back to {SPACY_MODEL_SECONDARY}"
            )
            app_state.nlp = spacy.load(SPACY_MODEL_SECONDARY)
            logger.info(f"Loaded {SPACY_MODEL_SECONDARY} (fallback) in {time.time() - start_time:.2f}s")

        app_state.model_status["nlp"] = "ready"
        app_state.model_errors.pop("nlp", None)
        return app_state.nlp
    except Exception as exc:  # pragma: no cover - defensive path
        app_state.model_status["nlp"] = "unavailable"
        app_state.model_errors["nlp"] = str(exc)
        logger.warning(f"spaCy model not available ({exc}). NLP features will be disabled.")
        app_state.nlp = None
        return None
    finally:
        app_state._nlp_loading = False


def ensure_embedder(app_state: Any):
    """Load the SentenceTransformer on demand, reusing a cached instance."""
    initialize_model_state(app_state)
    if app_state.embedder is not None:
        app_state.model_status["embedder"] = "ready"
        return app_state.embedder

    if app_state._embedder_loading:
        return None

    app_state._embedder_loading = True
    app_state.model_status["embedder"] = "loading"
    try:
        from sentence_transformers import SentenceTransformer

        from backend.core.config import SENTENCE_TRANSFORMER_MODEL

        start_time = time.time()
        app_state.embedder = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
        logger.info(f"Loaded {SENTENCE_TRANSFORMER_MODEL} in {time.time() - start_time:.2f}s")
        app_state.model_status["embedder"] = "ready"
        app_state.model_errors.pop("embedder", None)
        return app_state.embedder
    except Exception as exc:  # pragma: no cover - defensive path
        app_state.model_status["embedder"] = "unavailable"
        app_state.model_errors["embedder"] = str(exc)
        logger.warning(f"SentenceTransformer not available ({exc}). Embedding features will be disabled.")
        app_state.embedder = None
        return None
    finally:
        app_state._embedder_loading = False
