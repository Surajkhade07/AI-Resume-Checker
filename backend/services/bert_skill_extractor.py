"""
BERT-based skill extraction service using the fine-tuned model.
Integrates the fine-tuned BERT model from backend/bert_finetuned_model/
for advanced skill extraction and classification from resume text.
"""
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import torch
from transformers import (
    AutoConfig,
    AutoModelForTokenClassification,
    AutoTokenizer,
    pipeline,
)

from backend.core.cache import nlp_model_cache

logger = logging.getLogger('ats_resume_scorer')

# Path to the fine-tuned BERT model
BERT_MODEL_PATH = Path(__file__).resolve().parent.parent / 'bert_finetuned_model'


def _load_bert_pipeline() -> Optional[pipeline]:
    """
    Load the fine-tuned BERT model for token classification (NER).
    Uses caching to avoid reloading on every request.
    
    Returns:
        HuggingFace pipeline for token classification, or None if loading fails
    """
    cache_key = "bert_ner_pipeline"
    cached_pipeline = nlp_model_cache.get(cache_key)
    if cached_pipeline is not None:
        return cached_pipeline
    
    # Check if the fine-tuned model exists
    if not BERT_MODEL_PATH.exists():
        logger.warning(f"Fine-tuned BERT model not found at {BERT_MODEL_PATH}")
        return None
    
    required_files = ['config.json', 'model.safetensors', 'tokenizer.json']
    missing_files = [f for f in required_files if not (BERT_MODEL_PATH / f).exists()]
    
    if missing_files:
        logger.warning(f"BERT model missing files: {missing_files}")
        return None
    
    try:
        logger.info(f"Loading fine-tuned BERT model from {BERT_MODEL_PATH}")
        
        # Load tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained(str(BERT_MODEL_PATH))
        model = AutoModelForTokenClassification.from_pretrained(str(BERT_MODEL_PATH))
        
        # Create NER pipeline
        ner_pipeline = pipeline(
            "token-classification",
            model=model,
            tokenizer=tokenizer,
            aggregation_strategy="simple",  # Group sub-tokens into words
            device=-1,  # Use CPU (change to 0 for GPU)
        )
        
        # Cache the pipeline (1 hour TTL)
        nlp_model_cache.set(cache_key, ner_pipeline, ttl_seconds=3600)
        
        logger.info("BERT model loaded and cached successfully")
        return ner_pipeline
        
    except Exception as e:
        logger.error(f"Failed to load BERT model: {e}")
        return None


def get_model_info() -> Dict[str, Any]:
    """
    Get information about the loaded BERT model.
    
    Returns:
        Dict with model status, path, and configuration
    """
    model_exists = BERT_MODEL_PATH.exists()
    model_info = {
        'model_path': str(BERT_MODEL_PATH),
        'model_exists': model_exists,
        'is_loaded': nlp_model_cache.get("bert_ner_pipeline") is not None,
    }
    
    if model_exists:
        config_path = BERT_MODEL_PATH / 'config.json'
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = json.load(f)
                model_info['model_type'] = config.get('model_type', 'unknown')
                model_info['num_labels'] = config.get('num_labels', 0)
            except Exception:
                pass
    
    return model_info