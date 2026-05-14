"""
ML prediction service for is_a_buyer classification.

Loads 3 pre-trained models at startup and provides a predict() function
that preprocesses raw review text and returns a fused prediction.

Models (trained in Milestone I):
  1. BoW + Random Forest
  2. BoW + Logistic Regression
  3. Unweighted FastText + Logistic Regression

Fusion: soft voting (average of predicted probabilities).
"""

import logging
import os
import pickle
import re
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix

logger = logging.getLogger(__name__)

# --- Preprocessing constants ---
TOK_PATTERN = re.compile(r"[a-zA-Z]+(?:[-'][a-zA-Z]+)?")

# Use nltk for stemming/lemmatization (same as Milestone I)
try:
    from nltk.stem import PorterStemmer, WordNetLemmatizer
    import nltk
    nltk.download("wordnet", quiet=True)
    nltk.download("omw-1.4", quiet=True)
    _stemmer = PorterStemmer()
    _lemmatizer = WordNetLemmatizer()
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    logger.warning("nltk not available — stemming/lemmatization disabled")


# --- Global state (loaded once at startup) ---
_models_loaded = False
_vocab: dict[str, int] = {}
_stopwords: set[str] = set()
_bow_rf = None
_bow_lr = None
_ft_lr = None
_ft_vectors: dict[str, np.ndarray] = {}
_ft_dim: int = 300
_vocab_size: int = 0


def _get_models_dir() -> Path:
    """Locate the ml_models directory relative to this file."""
    return Path(__file__).parent / "ml_models"


def load_models() -> None:
    """Load all ML models and preprocessing artifacts from disk."""
    global _models_loaded, _vocab, _stopwords, _bow_rf, _bow_lr, _ft_lr
    global _ft_vectors, _ft_dim, _vocab_size

    if _models_loaded:
        return

    models_dir = _get_models_dir()
    if not models_dir.exists():
        logger.error("ML models directory not found: %s", models_dir)
        return

    try:
        with open(models_dir / "vocab.pkl", "rb") as f:
            _vocab = pickle.load(f)
        _vocab_size = len(_vocab)

        with open(models_dir / "stopwords.pkl", "rb") as f:
            _stopwords = pickle.load(f)

        with open(models_dir / "config.pkl", "rb") as f:
            config = pickle.load(f)
        _ft_dim = config.get("ft_dim", 300)

        bow_rf_path = models_dir / "bow_rf_model.pkl"
        if bow_rf_path.exists():
            with open(bow_rf_path, "rb") as f:
                _bow_rf = pickle.load(f)
        else:
            logger.warning("bow_rf_model.pkl not found — RF model will be skipped in fusion")

        with open(models_dir / "bow_lr_model.pkl", "rb") as f:
            _bow_lr = pickle.load(f)

        with open(models_dir / "ft_lr_model.pkl", "rb") as f:
            _ft_lr = pickle.load(f)

        with open(models_dir / "ft_vectors.pkl", "rb") as f:
            _ft_vectors = pickle.load(f)

        _models_loaded = True
        logger.info(
            "ML models loaded: vocab=%d, ft_vectors=%d, ft_dim=%d, rf=%s",
            _vocab_size, len(_ft_vectors), _ft_dim, _bow_rf is not None,
        )
    except Exception as e:
        logger.error("Failed to load ML models: %s", e)


def _preprocess(text: str) -> list[str]:
    """
    Preprocess raw review text using the same pipeline as Task 1:
    tokenize -> lowercase -> length filter -> stopword removal -> lemmatize + stem.
    """
    if not text or not isinstance(text, str):
        return []

    # Tokenize and lowercase
    tokens = [t.lower() for t in TOK_PATTERN.findall(text)]

    # Length filter (>= 2 chars)
    tokens = [t for t in tokens if len(t) >= 2]

    # Stopword removal
    tokens = [t for t in tokens if t not in _stopwords]

    # Lemmatize + stem (same order as Task 1)
    if NLTK_AVAILABLE:
        tokens = [_stemmer.stem(_lemmatizer.lemmatize(t)) for t in tokens]

    return tokens


def _text_to_bow(tokens: list[str]) -> csr_matrix:
    """Convert token list to sparse BoW vector aligned with vocab."""
    counts = Counter(t for t in tokens if t in _vocab)
    if not counts:
        return csr_matrix((1, _vocab_size), dtype=np.float32)

    cols = []
    vals = []
    for word, count in counts.items():
        cols.append(_vocab[word])
        vals.append(count)

    rows = [0] * len(cols)
    return csr_matrix((vals, (rows, cols)), shape=(1, _vocab_size), dtype=np.float32)


def _text_to_ft(tokens: list[str]) -> np.ndarray:
    """Convert token list to unweighted average FastText vector."""
    vecs = [_ft_vectors[t] for t in tokens if t in _ft_vectors]
    if not vecs:
        return np.zeros((1, _ft_dim), dtype=np.float32)
    return np.mean(vecs, axis=0, keepdims=True).astype(np.float32)


def predict(review_text: str) -> dict:
    """
    Predict is_a_buyer for a raw review text.

    Returns:
        {
            "predicted_is_buyer": bool,
            "confidence": float (0-1),
            "model_probabilities": {
                "bow_rf": float,
                "bow_lr": float,
                "ft_lr": float,
            },
            "fusion_method": "soft_voting",
        }
    """
    if not _models_loaded:
        load_models()

    if not _models_loaded:
        return {
            "predicted_is_buyer": True,
            "confidence": 0.5,
            "model_probabilities": {"bow_rf": 0.5, "bow_lr": 0.5, "ft_lr": 0.5},
            "fusion_method": "fallback",
        }

    # Preprocess
    tokens = _preprocess(review_text)

    # Generate features
    X_bow = _text_to_bow(tokens)
    X_ft = _text_to_ft(tokens)

    # Get probabilities from available models
    probs = []
    p_bow_rf = None
    if _bow_rf is not None:
        p_bow_rf = float(_bow_rf.predict_proba(X_bow)[0, 1])
        probs.append(p_bow_rf)

    p_bow_lr = float(_bow_lr.predict_proba(X_bow)[0, 1])
    p_ft_lr = float(_ft_lr.predict_proba(X_ft)[0, 1])
    probs.extend([p_bow_lr, p_ft_lr])

    # Soft voting: average of available probabilities
    fused_prob = sum(probs) / len(probs)
    predicted = fused_prob >= 0.5

    return {
        "predicted_is_buyer": bool(predicted),
        "confidence": round(float(fused_prob if predicted else 1 - fused_prob), 4),
        "model_probabilities": {
            "bow_rf": round(p_bow_rf, 4) if p_bow_rf is not None else 0.0,
            "bow_lr": round(p_bow_lr, 4),
            "ft_lr": round(p_ft_lr, 4),
        },
        "fusion_method": "soft_voting",
    }
