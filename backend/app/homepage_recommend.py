"""
Homepage Recommendation Engine.

Three recommendation sections for the homepage:

1. CHOSEN FOR YOU — adaptive hierarchy:
   - Cold Start (new user, no reviews):
       Score = Avg_Rating × 0.7 + log(Review_Count + 1) × 0.3
   - Warm Start (returning user with reviews):
       User-Based Collaborative Filtering — find users with similar
       rating profiles, recommend items they rated highly.
   - Hot Start (user has active cart):
       60% User-Item matrix (long-term preference)
       40% Item-Item similarity (cosine similarity of cart item tags)

2. NEW — items created in last 30 days:
   - Ranked by similarity to user's tag profile.
   - Sorted ascending by review_count (solve exposure problem).

3. BEST OFFER — "laggard" items (rating < 3.0) with 20% discount:
   - Only shown to price-sensitive users (who mention "expensive",
     "sale", "cheap", "price", "discount", "budget" in reviews).
"""

import logging
import math
import re
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine

logger = logging.getLogger(__name__)

# ── Module state (built at startup) ──────────────────────────────────────────

_user_item_matrix: Optional[np.ndarray] = None   # (n_users, n_items)
_user_ids: list[str] = []
_user_to_idx: dict[str, int] = {}
_item_ids: list[str] = []
_item_to_idx: dict[str, int] = {}
_item_ratings: dict[str, float] = {}              # item_id → avg rating
_item_review_counts: dict[str, int] = {}          # item_id → review count
_item_created: dict[str, datetime] = {}           # item_id → created_at
_item_prices: dict[str, float] = {}               # item_id → price
_item_mrps: dict[str, float] = {}                 # item_id → mrp
_user_review_texts: dict[str, list[str]] = defaultdict(list)  # user_id → review texts
_ready = False

PRICE_SENSITIVE_KEYWORDS = {
    "expensive", "sale", "cheap", "price", "discount", "budget",
    "costly", "overpriced", "affordable", "value for money", "worth",
    "not worth", "pricey", "bargain",
}


def build_homepage_index() -> None:
    """Build all data structures needed for homepage recommendations."""
    global _user_item_matrix, _user_ids, _user_to_idx
    global _item_ids, _item_to_idx, _item_ratings, _item_review_counts
    global _item_created, _item_prices, _item_mrps, _user_review_texts, _ready

    from sqlmodel import Session, select
    from app.core.db import engine
    from app.models import Item, Review

    with Session(engine) as session:
        items = session.exec(select(Item)).all()
        if not items:
            logger.warning("No items — homepage recommendation index empty")
            return

        _item_ids = [str(it.id) for it in items]
        _item_to_idx = {uid: idx for idx, uid in enumerate(_item_ids)}

        for it in items:
            sid = str(it.id)
            _item_ratings[sid] = it.product_rating or 0.0
            _item_review_counts[sid] = it.product_rating_count or 0
            _item_created[sid] = it.created_at or datetime.now(timezone.utc)
            _item_prices[sid] = it.price or 0.0
            _item_mrps[sid] = it.mrp or 0.0

        reviews = session.exec(select(Review)).all()
        user_id_set = sorted(set(str(r.owner_id) for r in reviews))
        _user_ids = user_id_set
        _user_to_idx = {uid: idx for idx, uid in enumerate(_user_ids)}

        n_users = len(_user_ids)
        n_items = len(_item_ids)

        # Build user-item rating matrix
        _user_item_matrix = np.zeros((n_users, n_items), dtype=np.float32)
        for r in reviews:
            u_idx = _user_to_idx.get(str(r.owner_id))
            i_idx = _item_to_idx.get(str(r.item_id))
            if u_idx is not None and i_idx is not None:
                _user_item_matrix[u_idx, i_idx] = float(r.rating)

        # Collect review texts per user (for price sensitivity)
        for r in reviews:
            text = f"{r.title or ''} {r.description or ''}".lower()
            _user_review_texts[str(r.owner_id)].append(text)

        _ready = True
        logger.info(
            f"Homepage recommendation index ready: "
            f"{n_items} items, {n_users} users, {len(reviews)} reviews"
        )


# ═════════════════════════════════════════════════════════════════════════════
#  SCORING HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _cold_start_scores() -> list[tuple[str, float]]:
    """
    Cold Start: Score = Avg_Rating × 0.7 + log(Review_Count + 1) × 0.3
    Returns all items sorted by score descending.
    """
    scored = []
    for iid in _item_ids:
        avg_r = _item_ratings.get(iid, 0.0)
        rc = _item_review_counts.get(iid, 0)
        score = avg_r * 0.7 + math.log(rc + 1) * 0.3
        scored.append((iid, score))
    scored.sort(key=lambda x: -x[1])
    return scored


def _warm_start_scores(user_id: str) -> list[tuple[str, float]]:
    """
    Warm Start: User-Based Collaborative Filtering.
    Find users with similar rating profiles, recommend items they liked
    but the current user hasn't rated.
    """
    u_idx = _user_to_idx.get(user_id)
    if u_idx is None or _user_item_matrix is None:
        return _cold_start_scores()

    user_vec = _user_item_matrix[u_idx].reshape(1, -1)

    # If user has no ratings, fall back to cold start
    if user_vec.sum() == 0:
        return _cold_start_scores()

    # Compute similarity between this user and all others
    user_sims = sk_cosine(user_vec, _user_item_matrix)[0]  # (n_users,)
    user_sims[u_idx] = 0  # exclude self

    # Get top-K similar users
    top_k = min(20, len(_user_ids))
    top_user_idxs = np.argsort(user_sims)[::-1][:top_k]

    # Weighted sum of similar users' ratings for items current user hasn't rated
    items_rated = set(np.where(user_vec[0] > 0)[0])
    item_scores: dict[int, float] = {}

    for other_idx in top_user_idxs:
        sim = user_sims[other_idx]
        if sim <= 0:
            continue
        for i_idx in range(len(_item_ids)):
            if i_idx in items_rated:
                continue
            rating = _user_item_matrix[other_idx, i_idx]
            if rating > 0:
                item_scores[i_idx] = item_scores.get(i_idx, 0) + sim * rating

    scored = [(_item_ids[i], s) for i, s in item_scores.items()]
    scored.sort(key=lambda x: -x[1])
    return scored


def _hot_start_scores(user_id: str, cart_item_ids: list[str]) -> list[tuple[str, float]]:
    """
    Hot Start: 60% user-item matrix + 40% item-item similarity from cart.
    """
    from app.skincare_rules import _item_tags

    # --- 60% component: User preference from warm start ---
    warm_scores = _warm_start_scores(user_id)
    warm_dict = {iid: score for iid, score in warm_scores}
    max_warm = max(warm_dict.values()) if warm_dict else 1.0
    if max_warm > 0:
        warm_dict = {k: v / max_warm for k, v in warm_dict.items()}

    # --- 40% component: Item-Item tag similarity from cart ---
    # Build a "cart profile" from the tags of items in cart
    cart_tags: Counter = Counter()
    for cid in cart_item_ids:
        tags = _item_tags.get(cid, {})
        for category in ["ingredients", "skin_types", "concerns", "product_steps"]:
            for tag in tags.get(category, set()):
                cart_tags[tag] += 1

    # Score each item by tag overlap with cart profile
    tag_scores: dict[str, float] = {}
    cart_set = set(cart_item_ids)
    for iid in _item_ids:
        if iid in cart_set:
            continue
        tags = _item_tags.get(iid, {})
        overlap = 0
        for category in ["ingredients", "skin_types", "concerns", "product_steps"]:
            for tag in tags.get(category, set()):
                overlap += cart_tags.get(tag, 0)
        tag_scores[iid] = float(overlap)

    max_tag = max(tag_scores.values()) if tag_scores else 1.0
    if max_tag > 0:
        tag_scores = {k: v / max_tag for k, v in tag_scores.items()}

    # --- Blend: 60/40 ---
    combined: dict[str, float] = {}
    all_ids = set(list(warm_dict.keys()) + list(tag_scores.keys())) - cart_set
    for iid in all_ids:
        w = warm_dict.get(iid, 0.0)
        t = tag_scores.get(iid, 0.0)
        combined[iid] = 0.6 * w + 0.4 * t

    scored = list(combined.items())
    scored.sort(key=lambda x: -x[1])
    return scored


# ═════════════════════════════════════════════════════════════════════════════
#  PRICE SENSITIVITY
# ═════════════════════════════════════════════════════════════════════════════

def _is_price_sensitive(user_id: str) -> bool:
    """Check if user mentions price-related keywords in their reviews."""
    texts = _user_review_texts.get(user_id, [])
    if not texts:
        return False
    combined = " ".join(texts)
    hits = sum(1 for kw in PRICE_SENSITIVE_KEYWORDS if kw in combined)
    return hits >= 2  # at least 2 price-related keyword mentions


# ═════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═════════════════════════════════════════════════════════════════════════════

def get_chosen_for_you(
    user_id: str,
    cart_item_ids: list[str],
    limit: int = 12,
) -> list[dict]:
    """
    Chosen For You — adaptive 3-tier hierarchy.
    Returns list of {"item_id": str, "score": float, "strategy": str}.
    """
    if not _ready:
        return []

    has_reviews = user_id in _user_to_idx
    has_cart = len(cart_item_ids) > 0

    if has_cart:
        # Hot Start
        scored = _hot_start_scores(user_id, cart_item_ids)
        strategy = "hot_start"
    elif has_reviews:
        # Warm Start
        scored = _warm_start_scores(user_id)
        strategy = "warm_start"
    else:
        # Cold Start
        scored = _cold_start_scores()
        strategy = "cold_start"

    results = []
    seen = set(cart_item_ids)
    for iid, score in scored:
        if iid in seen:
            continue
        seen.add(iid)
        results.append({
            "item_id": iid,
            "score": round(score, 4),
            "strategy": strategy,
        })
        if len(results) >= limit:
            break

    return results


def get_new_items(user_id: str, limit: int = 8) -> list[dict]:
    """
    NEW — items created in last 30 days.
    Ranked by similarity to user's profile tags, sorted ascending by
    review_count to solve the "exposure" problem for new products.
    """
    if not _ready:
        return []

    from app.skincare_rules import _item_tags

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    new_ids = [
        iid for iid in _item_ids
        if _item_created.get(iid, datetime.min.replace(tzinfo=timezone.utc)) >= cutoff
    ]

    if not new_ids:
        # Fallback: show most recent items regardless of 30-day cutoff
        by_date = sorted(
            _item_ids,
            key=lambda x: _item_created.get(x, datetime.min.replace(tzinfo=timezone.utc)),
            reverse=True,
        )
        new_ids = by_date[:limit * 2]

    # Build user profile from items they've reviewed
    user_tags: Counter = Counter()
    u_idx = _user_to_idx.get(user_id)
    if u_idx is not None and _user_item_matrix is not None:
        for i_idx in range(len(_item_ids)):
            if _user_item_matrix[u_idx, i_idx] > 0:
                tags = _item_tags.get(_item_ids[i_idx], {})
                for cat in ["ingredients", "skin_types", "concerns", "product_steps"]:
                    for tag in tags.get(cat, set()):
                        user_tags[tag] += 1

    # Score each new item by tag similarity to user profile
    scored = []
    for iid in new_ids:
        tags = _item_tags.get(iid, {})
        sim_score = 0.0
        for cat in ["ingredients", "skin_types", "concerns", "product_steps"]:
            for tag in tags.get(cat, set()):
                sim_score += user_tags.get(tag, 0)

        review_count = _item_review_counts.get(iid, 0)
        scored.append((iid, sim_score, review_count))

    # Primary sort: similarity descending, secondary: review_count ascending (exposure)
    scored.sort(key=lambda x: (-x[1], x[2]))

    return [
        {"item_id": iid, "similarity_score": round(sim, 4), "review_count": rc}
        for iid, sim, rc in scored[:limit]
    ]


def get_best_offers(user_id: str, limit: int = 6) -> list[dict]:
    """
    BEST OFFER — laggard items (rating < 3.0) with a hard-coded 20% discount.
    Only shown to price-sensitive users.
    """
    if not _ready:
        return []

    if not _is_price_sensitive(user_id):
        return []

    laggards = []
    for iid in _item_ids:
        avg_r = _item_ratings.get(iid, 0.0)
        price = _item_prices.get(iid, 0.0)
        if avg_r > 0 and avg_r < 3.0 and price > 0:
            discounted = round(price * 0.8, 2)
            laggards.append({
                "item_id": iid,
                "original_price": price,
                "discounted_price": discounted,
                "discount_pct": 20,
                "rating": round(avg_r, 2),
            })

    # Sort by rating ascending (worst first → biggest opportunity)
    laggards.sort(key=lambda x: x["rating"])
    return laggards[:limit]
