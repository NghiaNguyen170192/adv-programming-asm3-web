"""
Hybrid item recommendation service using collaborative filtering + content fallback.

PRIMARY — Item-based Collaborative Filtering:
  - Builds a user-item rating matrix from the review table.
  - Computes pairwise cosine similarity between item rating vectors.
  - Items that tend to be rated similarly by the same users are considered similar.
  - Works well because the item space is small (295 items → 295×295 matrix).

FALLBACK — Content-based TF-IDF similarity:
  - For cold-start items with no/few reviews, falls back to text similarity.
  - Combines item title, brand, and description into TF-IDF vectors.
  - Uses cosine similarity on TF-IDF vectors.

HYBRID — The final similarity score blends both signals when available:
  score = α * collab_sim + (1 - α) * content_sim     (α = 0.7 by default)
"""

import logging
import uuid
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ── Module state ─────────────────────────────────────────────────────────────

_item_ids: list[str] = []                # ordered list of item UUIDs (as str)
_id_to_idx: dict[str, int] = {}          # item UUID → index in the matrix
_collab_sim: Optional[np.ndarray] = None # (n_items, n_items) collaborative sim
_content_sim: Optional[np.ndarray] = None # (n_items, n_items) content sim
_hybrid_sim: Optional[np.ndarray] = None  # blended similarity matrix
_item_brands: dict[str, str] = {}         # item_id → brand (lowered)
_brand_index: dict[str, list[str]] = {}   # brand (lowered) → list of item_ids
_popularity_ranked: list[str] = []        # item_ids sorted by review count desc
_ready = False

ALPHA = 0.7           # weight for collaborative filtering (vs content)
MIN_REVIEWS_CF = 3    # minimum reviews for an item to trust CF signal


def build_index() -> None:
    """
    Build the recommendation index from the database.
    Called once at application startup.
    """
    global _item_ids, _id_to_idx, _collab_sim, _content_sim, _hybrid_sim, _ready

    from sqlmodel import Session, select, col
    from app.core.db import engine
    from app.models import Item, Review

    with Session(engine) as session:
        # ── Load items ───────────────────────────────────────────────────
        items = session.exec(select(Item).order_by(col(Item.created_at))).all()
        if not items:
            logger.warning("No items found — recommendation index empty")
            return

        _item_ids = [str(item.id) for item in items]
        _id_to_idx = {uid: idx for idx, uid in enumerate(_item_ids)}
        n_items = len(_item_ids)
        logger.info(f"Building recommendation index for {n_items} items")

        # ── Brand index (for fallback) ────────────────────────────────
        from collections import defaultdict as _defaultdict
        brand_buckets: dict[str, list[str]] = _defaultdict(list)
        for item in items:
            brand = (item.brand or "").strip().lower()
            sid = str(item.id)
            _item_brands[sid] = brand
            if brand:
                brand_buckets[brand].append(sid)
        _brand_index.update(brand_buckets)

        # ── Content-based similarity (TF-IDF) ───────────────────────────
        corpus = []
        for item in items:
            text_parts = [item.title or ""]
            if item.brand:
                text_parts.append(item.brand)
            if item.description:
                text_parts.append(item.description)
            corpus.append(" ".join(text_parts).lower())

        tfidf = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
        )
        tfidf_matrix = tfidf.fit_transform(corpus)
        _content_sim = cosine_similarity(tfidf_matrix)
        logger.info("Content-based TF-IDF similarity matrix built")

        # ── Collaborative filtering (item-based) ────────────────────────
        reviews = session.exec(select(Review)).all()

        # Build user→index mapping for sparse representation
        user_ids = sorted(set(str(r.owner_id) for r in reviews))
        user_to_idx = {uid: idx for idx, uid in enumerate(user_ids)}
        n_users = len(user_ids)

        # Build user-item rating matrix (dense, items are small)
        rating_matrix = np.zeros((n_users, n_items), dtype=np.float32)
        for r in reviews:
            uid_idx = user_to_idx.get(str(r.owner_id))
            iid_idx = _id_to_idx.get(str(r.item_id))
            if uid_idx is not None and iid_idx is not None:
                rating_matrix[uid_idx, iid_idx] = float(r.rating)

        # Mean-center per user (subtract user's mean from nonzero ratings)
        for u in range(n_users):
            user_ratings = rating_matrix[u]
            mask = user_ratings > 0
            if mask.sum() > 0:
                mean_r = user_ratings[mask].mean()
                user_ratings[mask] -= mean_r

        # Item-item cosine similarity on the mean-centered rating columns
        # Each column is an item's rating vector across all users
        item_vectors = rating_matrix.T  # (n_items, n_users)
        norms = np.linalg.norm(item_vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        item_vectors_normed = item_vectors / norms
        _collab_sim = item_vectors_normed @ item_vectors_normed.T
        logger.info("Collaborative filtering similarity matrix built")

        # ── Count reviews per item for blending ──────────────────────────
        review_counts = np.zeros(n_items, dtype=np.int32)
        for r in reviews:
            iid_idx = _id_to_idx.get(str(r.item_id))
            if iid_idx is not None:
                review_counts[iid_idx] += 1

        # ── Hybrid blending ──────────────────────────────────────────────
        _hybrid_sim = np.zeros((n_items, n_items), dtype=np.float32)
        for i in range(n_items):
            for j in range(n_items):
                # If both items have enough reviews, blend; else use content only
                if review_counts[i] >= MIN_REVIEWS_CF and review_counts[j] >= MIN_REVIEWS_CF:
                    _hybrid_sim[i, j] = (
                        ALPHA * _collab_sim[i, j]
                        + (1 - ALPHA) * _content_sim[i, j]
                    )
                else:
                    _hybrid_sim[i, j] = _content_sim[i, j]

        # ── Popularity ranking (for last-resort fallback) ────────────
        item_review_map: dict[str, int] = {}
        for r in reviews:
            sid = str(r.item_id)
            item_review_map[sid] = item_review_map.get(sid, 0) + 1
        _popularity_ranked.clear()
        _popularity_ranked.extend(
            sorted(_item_ids, key=lambda x: item_review_map.get(x, 0), reverse=True)
        )

        _ready = True
        logger.info("Hybrid recommendation index ready")


def get_similar_items(item_id: str, top_n: int = 8) -> list[dict]:
    """
    Return top_n most similar items for the given item_id.

    Returns a list of dicts: [{"item_id": str, "score": float}, ...]
    sorted by descending similarity score. Excludes the query item itself.

    Falls back to content-only similarity when hybrid scores are all <= 0
    (cold-start items with few reviews or sparse descriptions).
    """
    if not _ready:
        return []

    idx = _id_to_idx.get(str(item_id))
    if idx is None:
        return []

    sim_scores = _hybrid_sim[idx]
    # Get indices sorted by descending similarity, exclude self
    ranked = np.argsort(sim_scores)[::-1]

    results = []
    for r_idx in ranked:
        if r_idx == idx:
            continue
        score = float(sim_scores[r_idx])
        if score <= 0:
            break
        results.append({
            "item_id": _item_ids[r_idx],
            "score": round(score, 4),
        })
        if len(results) >= top_n:
            break

    # Fallback 1: if hybrid returned nothing, use content-only similarity
    if not results and _content_sim is not None:
        content_scores = _content_sim[idx]
        content_ranked = np.argsort(content_scores)[::-1]
        for r_idx in content_ranked:
            if r_idx == idx:
                continue
            score = float(content_scores[r_idx])
            if score <= 0:
                break
            results.append({
                "item_id": _item_ids[r_idx],
                "score": round(score, 4),
            })
            if len(results) >= top_n:
                break

    # Fallback 2: same brand, then most popular items
    if not results:
        seen = {item_id}
        brand = _item_brands.get(item_id, "")
        if brand:
            for bid in _brand_index.get(brand, []):
                if bid not in seen:
                    results.append({"item_id": bid, "score": 0.0})
                    seen.add(bid)
                    if len(results) >= top_n:
                        break
        # Fill remaining slots with most popular items
        for pid in _popularity_ranked:
            if len(results) >= top_n:
                break
            if pid not in seen:
                results.append({"item_id": pid, "score": 0.0})
                seen.add(pid)

    return results
