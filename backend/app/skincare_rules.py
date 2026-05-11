"""
Smart Skincare Recommendation Engine — Rule-Based Expert System.

This module implements a domain-specific recommendation layer on top of
the generic collaborative-filtering recommender. It encodes dermatological
knowledge about ingredient interactions, skin-type compatibility, and
product-routine sequencing.

Architecture:
  1. **Auto-Tagger** — scans item titles/descriptions at startup and assigns
     taxonomy labels (ingredient, skin_type, concern, product_step).
  2. **Ingredient Synergy Rules** — "Perfect Pairs" cross-sell logic based
     on scientifically-backed ingredient combinations.
  3. **Routine Builder** — assembles a multi-step routine (cleanser → SPF)
     filtered by the user's skin-type tags.
  4. **Frequently Bought Together** — mines review co-occurrence to find
     items that real users purchased alongside the current item.
"""

import logging
import re
import uuid
from collections import Counter, defaultdict
from typing import Optional

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# 1.  TAGGING TAXONOMY — keyword → category mappings
# ═══════════════════════════════════════════════════════════════════════════════

INGREDIENT_KEYWORDS: dict[str, list[str]] = {
    "niacinamide": ["niacinamide"],
    "vitamin_c": ["vitamin c", "vit c", "ascorbic acid", "radiance", "brightening"],
    "retinol": ["retinol", "retinoid", "vitamin a", "anti-aging", "anti-ageing"],
    "hyaluronic_acid": ["hyaluronic acid", "hyaluronic", "hydration"],
    "salicylic_acid": ["salicylic acid", "salicylic"],
    "aha": ["aha", "glycolic acid", "lactic acid", "alpha hydroxy"],
    "bha": ["bha", "beta hydroxy"],
    "peptides": ["peptide", "pentapeptide", "peptides"],
    "ceramides": ["ceramide", "ceramides", "barrier repair"],
    "squalane": ["squalane", "squalene"],
    "spf": ["spf", "sunscreen", "sun protection", "uv protect"],
    "argan_oil": ["argan oil", "argan"],
    "aloe": ["aloe", "aloe vera"],
    "tea_tree": ["tea tree"],
    "centella": ["centella", "cica", "centella asiatica"],
    "panthenol": ["panthenol", "pro-vitamin b5", "provitamin b5"],
    "coconut": ["coconut", "coconut milk"],
    "cocoa_butter": ["cocoa butter"],
    "zinc": ["zinc"],
}

SKIN_TYPE_KEYWORDS: dict[str, list[str]] = {
    "oily": ["oily", "oil-free", "oil control", "matte", "mattifying", "shine control"],
    "dry": ["dry", "intense moisture", "rich cream", "nourishing"],
    "sensitive": ["sensitive", "gentle", "soothing", "calming", "fragrance-free"],
    "combination": ["combination"],
    "normal": ["all skin types", "normal skin"],
    "acne_prone": ["acne", "blemish", "spot", "breakout", "pimple"],
}

CONCERN_KEYWORDS: dict[str, list[str]] = {
    "anti_aging": ["anti-aging", "anti-ageing", "wrinkle", "fine lines", "ageing", "aging", "regenerist"],
    "acne": ["acne", "blemish", "spot treatment", "pimple"],
    "brightening": ["brightening", "radiance", "glow", "luminous", "white", "fairness", "whitening"],
    "hydration": ["hydrating", "hydration", "moisturizing", "moisture"],
    "redness": ["redness", "rosacea", "calming"],
    "dullness": ["dullness", "dull skin", "revitalizing"],
    "frizz": ["frizz", "frizzy", "frizz-free"],
    "hair_fall": ["hair fall", "hair loss", "strengthening"],
    "volume": ["volume", "volumin"],
    "dandruff": ["dandruff"],
}

PRODUCT_STEP_KEYWORDS: dict[str, list[str]] = {
    "cleanser": ["cleanser", "face wash", "cleansing", "micellar"],
    "toner": ["toner", "toning"],
    "serum": ["serum", "essence", "ampoule"],
    "treatment": ["treatment", "peel", "mask", "patch", "scrub", "exfoliat"],
    "moisturizer": ["moisturiser", "moisturizer", "cream", "day cream", "night cream",
                    "lotion", "gel cream", "gel moistur"],
    "spf_product": ["spf", "sunscreen", "sun protection"],
    "eye_care": ["eye cream", "eye gel", "under-eye", "under eye"],
    "lip": ["lipstick", "lip color", "lip crayon", "lip liner", "lip gloss", "lip balm"],
    "foundation": ["foundation", "concealer", "primer", "bb cream", "cc cream"],
    "blush": ["blush", "highlighter", "bronzer", "illuminating"],
    "eye_makeup": ["mascara", "eyeliner", "eye liner", "eyeshadow", "kajal", "kohl"],
    "nail": ["nail", "nail polish", "nail enamel"],
    "shampoo": ["shampoo"],
    "conditioner": ["conditioner"],
    "hair_serum": ["hair serum", "hair oil"],
}

# ═══════════════════════════════════════════════════════════════════════════════
# 2.  INGREDIENT SYNERGY RULES — "Perfect Pairs"
# ═══════════════════════════════════════════════════════════════════════════════

SYNERGY_RULES: list[dict] = [
    {
        "if_ingredient": "niacinamide",
        "recommend_ingredient": "vitamin_c",
        "reason": "Niacinamide strengthens the skin barrier while Vitamin C brightens — together they tackle hyperpigmentation effectively.",
    },
    {
        "if_ingredient": "vitamin_c",
        "recommend_ingredient": "niacinamide",
        "reason": "Vitamin C fights free-radical damage; Niacinamide calms inflammation and evens skin tone — a powerhouse duo.",
    },
    {
        "if_ingredient": "retinol",
        "recommend_ingredient": "peptides",
        "reason": "Retinol accelerates cell turnover but can irritate; peptides help repair and strengthen the skin barrier.",
    },
    {
        "if_ingredient": "retinol",
        "recommend_ingredient": "ceramides",
        "reason": "Retinol can compromise the moisture barrier; ceramides restore and seal it, reducing dryness and flaking.",
    },
    {
        "if_ingredient": "hyaluronic_acid",
        "recommend_ingredient": "squalane",
        "reason": "Hyaluronic acid pulls moisture into the skin; squalane acts as an occlusive to lock that hydration in.",
    },
    {
        "if_ingredient": "aha",
        "recommend_ingredient": "spf",
        "reason": "AHAs increase photosensitivity — SPF is a mandatory companion to prevent UV damage after exfoliation.",
    },
    {
        "if_ingredient": "bha",
        "recommend_ingredient": "spf",
        "reason": "BHAs make skin more sun-sensitive — always pair with broad-spectrum SPF 30+ protection.",
    },
    {
        "if_ingredient": "salicylic_acid",
        "recommend_ingredient": "niacinamide",
        "reason": "Salicylic acid clears pores; niacinamide reduces the inflammation and redness that often follows.",
    },
    {
        "if_ingredient": "aloe",
        "recommend_ingredient": "hyaluronic_acid",
        "reason": "Aloe vera soothes and calms; hyaluronic acid deeply hydrates — great for irritated or dehydrated skin.",
    },
    {
        "if_ingredient": "tea_tree",
        "recommend_ingredient": "centella",
        "reason": "Tea tree fights bacteria on acne-prone skin; centella asiatica calms the irritation and speeds healing.",
    },
]

# ═══════════════════════════════════════════════════════════════════════════════
# 3.  SKIN TYPE + CONCERN BUNDLE RULES — "Complete Your Routine"
# ═══════════════════════════════════════════════════════════════════════════════

ROUTINE_RULES: list[dict] = [
    {
        "if_skin_types": ["oily", "acne_prone"],
        "steps": ["cleanser", "serum", "moisturizer", "spf_product"],
        "prefer_ingredients": ["salicylic_acid", "niacinamide", "tea_tree"],
        "label": "Oily & Acne-Prone Routine",
    },
    {
        "if_skin_types": ["dry", "sensitive"],
        "steps": ["cleanser", "serum", "moisturizer"],
        "prefer_ingredients": ["centella", "panthenol", "ceramides", "hyaluronic_acid"],
        "label": "Dry & Sensitive Skin Routine",
    },
    {
        "if_skin_types": ["normal"],
        "steps": ["cleanser", "serum", "moisturizer", "spf_product"],
        "prefer_ingredients": ["niacinamide", "vitamin_c"],
        "label": "Everyday Glow Routine",
    },
    {
        "if_skin_types": ["oily"],
        "steps": ["cleanser", "toner", "moisturizer"],
        "prefer_ingredients": ["salicylic_acid", "niacinamide"],
        "label": "Oil Control Routine",
    },
    {
        "if_skin_types": ["dry"],
        "steps": ["cleanser", "serum", "moisturizer"],
        "prefer_ingredients": ["hyaluronic_acid", "squalane", "ceramides"],
        "label": "Deep Hydration Routine",
    },
]

# ═══════════════════════════════════════════════════════════════════════════════
# 4.  MODULE STATE — populated at startup
# ═══════════════════════════════════════════════════════════════════════════════

# item_id → set of taxonomy labels
_item_tags: dict[str, dict[str, set[str]]] = {}
# ingredient → list of item_ids that have it
_ingredient_index: dict[str, list[str]] = defaultdict(list)
# product_step → list of item_ids
_step_index: dict[str, list[str]] = defaultdict(list)
# skin_type → list of item_ids
_skin_type_index: dict[str, list[str]] = defaultdict(list)
# concern → list of item_ids
_concern_index: dict[str, list[str]] = defaultdict(list)
# "frequently bought together" — item_id → [(item_id, count)]
_cooccurrence: dict[str, list[tuple[str, int]]] = {}
_ready = False


def _tag_text(text: str) -> dict[str, set[str]]:
    """Scan text and return taxonomy labels across all categories."""
    text_lower = text.lower()
    tags: dict[str, set[str]] = {
        "ingredients": set(),
        "skin_types": set(),
        "concerns": set(),
        "product_steps": set(),
    }

    for label, keywords in INGREDIENT_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                tags["ingredients"].add(label)
                break

    for label, keywords in SKIN_TYPE_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                tags["skin_types"].add(label)
                break

    for label, keywords in CONCERN_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                tags["concerns"].add(label)
                break

    for label, keywords in PRODUCT_STEP_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                tags["product_steps"].add(label)
                break

    return tags


def build_skincare_index() -> None:
    """Auto-tag all items and build indices. Called at startup."""
    global _item_tags, _ingredient_index, _step_index, _skin_type_index
    global _concern_index, _cooccurrence, _ready

    from sqlmodel import Session, select
    from app.core.db import engine
    from app.models import Item, Review

    with Session(engine) as session:
        items = session.exec(select(Item)).all()
        if not items:
            logger.warning("No items — skincare index empty")
            return

        logger.info(f"Building skincare taxonomy for {len(items)} items")

        # ── Auto-tag each item ───────────────────────────────────────────
        for item in items:
            item_id = str(item.id)
            text = " ".join(filter(None, [item.title, item.brand, item.description]))
            tags = _tag_text(text)
            _item_tags[item_id] = tags

            for ingr in tags["ingredients"]:
                _ingredient_index[ingr].append(item_id)
            for step in tags["product_steps"]:
                _step_index[step].append(item_id)
            for st in tags["skin_types"]:
                _skin_type_index[st].append(item_id)
            for c in tags["concerns"]:
                _concern_index[c].append(item_id)

        tagged_count = sum(1 for t in _item_tags.values()
                          if any(len(v) > 0 for v in t.values()))
        logger.info(f"Tagged {tagged_count}/{len(items)} items with taxonomy labels")

        # ── Frequently Bought Together (review co-occurrence) ────────────
        reviews = session.exec(select(Review)).all()
        user_items: dict[str, list[str]] = defaultdict(list)
        for r in reviews:
            user_items[str(r.owner_id)].append(str(r.item_id))

        pair_counts: Counter = Counter()
        for uid, item_list in user_items.items():
            unique_items = list(set(item_list))
            if len(unique_items) < 2:
                continue
            for i in range(len(unique_items)):
                for j in range(i + 1, len(unique_items)):
                    pair = tuple(sorted([unique_items[i], unique_items[j]]))
                    pair_counts[pair] += 1

        # Build per-item co-occurrence sorted by count
        item_cooc: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for (a, b), count in pair_counts.items():
            if count >= 2:  # at least 2 users bought both
                item_cooc[a].append((b, count))
                item_cooc[b].append((a, count))

        for item_id in item_cooc:
            item_cooc[item_id].sort(key=lambda x: -x[1])

        _cooccurrence = dict(item_cooc)
        logger.info(f"Built co-occurrence index for {len(_cooccurrence)} items")

        _ready = True
        logger.info("Skincare recommendation engine ready")


# ═══════════════════════════════════════════════════════════════════════════════
# 5.  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def get_skincare_recommendations(item_id: str) -> dict:
    """
    Return skincare-specific recommendations for a given item.

    Returns:
        {
            "item_tags": { ingredients, skin_types, concerns, product_steps },
            "perfect_match": [ { item_id, reason } ],
            "complete_your_routine": { label, steps: [ { step, item_ids } ] },
            "frequently_bought_together": [ { item_id, co_purchase_count } ],
            "others_with_skin_type_liked": [ item_id ],
        }
    """
    if not _ready:
        return {}

    tags = _item_tags.get(item_id)
    if not tags:
        return {}

    result: dict = {
        "item_tags": {k: list(v) for k, v in tags.items()},
        "perfect_match": [],
        "complete_your_routine": None,
        "frequently_bought_together": [],
        "others_with_skin_type_liked": [],
    }

    # ── Perfect Match (ingredient synergies) ─────────────────────────────
    seen_items: set[str] = {item_id}
    for rule in SYNERGY_RULES:
        if rule["if_ingredient"] in tags["ingredients"]:
            target_ingr = rule["recommend_ingredient"]
            candidates = _ingredient_index.get(target_ingr, [])
            for cid in candidates:
                if cid not in seen_items:
                    result["perfect_match"].append({
                        "item_id": cid,
                        "reason": rule["reason"],
                        "synergy_ingredient": target_ingr,
                    })
                    seen_items.add(cid)
                    if len(result["perfect_match"]) >= 6:
                        break
        if len(result["perfect_match"]) >= 6:
            break

    # ── Complete Your Routine (skin type bundles) ────────────────────────
    item_skin_types = tags["skin_types"]
    best_rule = None
    best_overlap = 0
    for rule in ROUTINE_RULES:
        overlap = len(set(rule["if_skin_types"]) & item_skin_types)
        if overlap > best_overlap:
            best_overlap = overlap
            best_rule = rule

    if best_rule:
        routine_steps = []
        for step in best_rule["steps"]:
            step_candidates = _step_index.get(step, [])
            # Score candidates by how many preferred ingredients they have
            scored = []
            for cid in step_candidates:
                if cid == item_id:
                    continue
                ctags = _item_tags.get(cid, {})
                pref_overlap = len(
                    set(best_rule["prefer_ingredients"]) &
                    ctags.get("ingredients", set())
                )
                scored.append((cid, pref_overlap))
            scored.sort(key=lambda x: -x[1])
            top_ids = [s[0] for s in scored[:3]]
            routine_steps.append({"step": step, "item_ids": top_ids})

        result["complete_your_routine"] = {
            "label": best_rule["label"],
            "steps": routine_steps,
        }

    # ── Frequently Bought Together ───────────────────────────────────────
    cooc = _cooccurrence.get(item_id, [])
    for cid, count in cooc[:6]:
        result["frequently_bought_together"].append({
            "item_id": cid,
            "co_purchase_count": count,
        })

    # ── Others with [Skin Type] liked ────────────────────────────────────
    if item_skin_types:
        skin_candidates: Counter = Counter()
        for st in item_skin_types:
            for cid in _skin_type_index.get(st, []):
                if cid != item_id:
                    skin_candidates[cid] += 1
        top_skin = [cid for cid, _ in skin_candidates.most_common(8)]
        result["others_with_skin_type_liked"] = top_skin
        result["skin_type_label"] = ", ".join(
            s.replace("_", " ").title() for s in item_skin_types
        )

    return result
