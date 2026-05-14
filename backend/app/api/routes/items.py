import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, or_, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Item, ItemCreate, ItemPublic, ItemsPublic, ItemUpdate, Message, User

router = APIRouter(prefix="/items", tags=["items"])


def _build_item_public(session: SessionDep, item: Item) -> ItemPublic:
    owner = session.get(User, item.owner_id)
    owner_name = (owner.full_name or owner.email) if owner else None
    item_public = ItemPublic.model_validate(item)
    item_public.owner_name = owner_name
    return item_public


@router.get("/search", response_model=ItemsPublic)
def search_items(
    keyword: str,
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Search items by keyword in title, brand, or description.

    Uses a two-pass strategy:
      1. Exact substring match (case-insensitive) on any keyword token.
      2. Fuzzy trigram match (pg_trgm) for handling typos and similar forms
         e.g. "Maybeline" matches "Maybelline New York".

    Results are ordered by relevance (trigram similarity score).
    """
    from sqlalchemy import text as sa_text

    keyword = keyword.strip()
    if not keyword:
        return ItemsPublic(data=[], count=0)

    kw_lower = keyword.lower()
    tokens = kw_lower.split()

    # Build exact substring filters (any token matches any field)
    exact_conditions = []
    for token in tokens:
        exact_conditions.append(func.lower(Item.title).contains(token))
        exact_conditions.append(func.lower(Item.brand).contains(token))
        exact_conditions.append(func.lower(Item.description).contains(token))
    exact_filter = or_(*exact_conditions)

    # Fuzzy trigram filter: similarity > 0.15 on brand or title
    TRGM_THRESHOLD = 0.15
    fuzzy_filter = or_(
        func.similarity(func.lower(func.coalesce(Item.brand, "")), kw_lower) > TRGM_THRESHOLD,
        func.similarity(func.lower(Item.title), kw_lower) > TRGM_THRESHOLD,
    )

    # Combine: exact OR fuzzy
    combined_filter = or_(exact_filter, fuzzy_filter)

    count_statement = select(func.count()).select_from(Item).where(combined_filter)
    count = session.exec(count_statement).one()

    # Order by relevance: highest trigram similarity first
    relevance = (
        func.similarity(func.lower(func.coalesce(Item.brand, "")), kw_lower)
        + func.similarity(func.lower(Item.title), kw_lower)
    )

    statement = (
        select(Item)
        .where(combined_filter)
        .order_by(relevance.desc())
        .offset(skip)
        .limit(limit)
    )
    items = session.exec(statement).all()
    items_public = [_build_item_public(session, item) for item in items]
    return ItemsPublic(data=items_public, count=count)


@router.get("/", response_model=ItemsPublic)
def read_items(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve items.
    """
    if current_user.is_superuser:
        count_statement = select(func.count()).select_from(Item)
        count = session.exec(count_statement).one()
        statement = (
            select(Item).order_by(col(Item.created_at).desc()).offset(skip).limit(limit)
        )
        items = session.exec(statement).all()
    else:
        count_statement = (
            select(func.count())
            .select_from(Item)
            .where(Item.owner_id == current_user.id)
        )
        count = session.exec(count_statement).one()
        statement = (
            select(Item)
            .where(Item.owner_id == current_user.id)
            .order_by(col(Item.created_at).desc())
            .offset(skip)
            .limit(limit)
        )
        items = session.exec(statement).all()

    items_public = [_build_item_public(session, item) for item in items]
    return ItemsPublic(data=items_public, count=count)


@router.get("/homepage-recommendations")
def homepage_recommendations(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Homepage recommendation feed with three sections:
    - Chosen For You (cold/warm/hot start)
    - New (recent items ranked for exposure)
    - Best Offer (discounted laggards for price-sensitive users)
    """
    from app.homepage_recommend import get_chosen_for_you, get_new_items, get_best_offers
    from app.models import CartItem

    # Get user's cart item IDs
    cart_items = session.exec(
        select(CartItem).where(CartItem.user_id == current_user.id)
    ).all()
    cart_item_ids = [str(ci.item_id) for ci in cart_items]

    user_id = str(current_user.id)

    # ── Chosen For You ────────────────────────────────────────────────────
    chosen_raw = get_chosen_for_you(user_id, cart_item_ids, limit=12)
    chosen_resolved = []
    strategy = chosen_raw[0]["strategy"] if chosen_raw else "cold_start"
    for entry in chosen_raw:
        it = session.get(Item, uuid.UUID(entry["item_id"]))
        if it:
            pub = _build_item_public(session, it)
            chosen_resolved.append({
                **pub.model_dump(),
                "score": entry["score"],
            })

    # ── New ───────────────────────────────────────────────────────────────
    new_raw = get_new_items(user_id, limit=8)
    new_resolved = []
    for entry in new_raw:
        it = session.get(Item, uuid.UUID(entry["item_id"]))
        if it:
            pub = _build_item_public(session, it)
            new_resolved.append({
                **pub.model_dump(),
                "review_count": entry["review_count"],
            })

    # ── Best Offer ────────────────────────────────────────────────────────
    offers_raw = get_best_offers(user_id, limit=6)
    offers_resolved = []
    for entry in offers_raw:
        it = session.get(Item, uuid.UUID(entry["item_id"]))
        if it:
            pub = _build_item_public(session, it)
            offers_resolved.append({
                **pub.model_dump(),
                "original_price": entry["original_price"],
                "discounted_price": entry["discounted_price"],
                "discount_pct": entry["discount_pct"],
            })

    return {
        "chosen_for_you": chosen_resolved,
        "chosen_strategy": strategy,
        "new_arrivals": new_resolved,
        "best_offers": offers_resolved,
    }


@router.get("/{id}/similar", response_model=ItemsPublic)
def get_similar_items(
    id: uuid.UUID,
    session: SessionDep,
    limit: int = 8,
) -> Any:
    """
    Get similar items using hybrid collaborative filtering + content-based similarity.
    """
    from app.recommend_service import get_similar_items as recommend

    item = session.get(Item, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    similar = recommend(str(id), top_n=limit)
    items = []
    for entry in similar:
        sim_item = session.get(Item, uuid.UUID(entry["item_id"]))
        if sim_item:
            items.append(sim_item)

    items_public = [_build_item_public(session, i) for i in items]
    return ItemsPublic(data=items_public, count=len(items_public))


@router.get("/{id}/skincare-recommendations")
def get_skincare_recommendations(
    id: uuid.UUID,
    session: SessionDep,
) -> Any:
    """
    Get smart skincare recommendations: ingredient synergies, routine bundles,
    frequently bought together, and skin-type community picks.
    """
    from app.skincare_rules import get_skincare_recommendations as get_recs

    item = session.get(Item, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    recs = get_recs(str(id))

    # Resolve item_ids to full item objects for each section
    def resolve_items(item_ids: list[str]) -> list[dict]:
        results = []
        for iid in item_ids:
            it = session.get(Item, uuid.UUID(iid))
            if it:
                pub = _build_item_public(session, it)
                results.append(pub.model_dump())
        return results

    response: dict[str, Any] = {"item_tags": recs.get("item_tags", {})}

    # Perfect Match
    pm = recs.get("perfect_match", [])
    pm_resolved = []
    for entry in pm:
        it = session.get(Item, uuid.UUID(entry["item_id"]))
        if it:
            pub = _build_item_public(session, it)
            pm_resolved.append({
                **pub.model_dump(),
                "reason": entry["reason"],
                "synergy_ingredient": entry["synergy_ingredient"],
            })
    response["perfect_match"] = pm_resolved

    # Complete Your Routine
    routine = recs.get("complete_your_routine")
    if routine:
        resolved_steps = []
        for step_info in routine["steps"]:
            resolved_steps.append({
                "step": step_info["step"],
                "items": resolve_items(step_info["item_ids"]),
            })
        response["complete_your_routine"] = {
            "label": routine["label"],
            "steps": resolved_steps,
        }
    else:
        response["complete_your_routine"] = None

    # Frequently Bought Together
    fbt = recs.get("frequently_bought_together", [])
    fbt_resolved = []
    for entry in fbt:
        it = session.get(Item, uuid.UUID(entry["item_id"]))
        if it:
            pub = _build_item_public(session, it)
            fbt_resolved.append({
                **pub.model_dump(),
                "co_purchase_count": entry["co_purchase_count"],
            })
    response["frequently_bought_together"] = fbt_resolved

    # Others with skin type liked
    others_ids = recs.get("others_with_skin_type_liked", [])
    response["others_with_skin_type_liked"] = resolve_items(others_ids)
    response["skin_type_label"] = recs.get("skin_type_label", "")

    return response


@router.get("/{id}", response_model=ItemPublic)
def read_item(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get item by ID.
    """
    item = session.get(Item, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return _build_item_public(session, item)


@router.post("/", response_model=ItemPublic)
def create_item(
    *, session: SessionDep, current_user: CurrentUser, item_in: ItemCreate
) -> Any:
    """
    Create new item.
    """
    item = Item.model_validate(item_in, update={"owner_id": current_user.id})
    session.add(item)
    session.commit()
    session.refresh(item)
    return _build_item_public(session, item)


@router.put("/{id}", response_model=ItemPublic)
def update_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    item_in: ItemUpdate,
) -> Any:
    """
    Update an item.
    """
    item = session.get(Item, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    update_dict = item_in.model_dump(exclude_unset=True)
    item.sqlmodel_update(update_dict)
    session.add(item)
    session.commit()
    session.refresh(item)
    return _build_item_public(session, item)


@router.delete("/{id}")
def delete_item(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete an item.
    """
    item = session.get(Item, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    session.delete(item)
    session.commit()
    return Message(message="Item deleted successfully")