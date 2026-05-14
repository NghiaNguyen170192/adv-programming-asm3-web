import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.models import CartItem, CartItemPublic, CartPublic, Item, ItemPublic, Message, User

router = APIRouter(prefix="/cart", tags=["cart"])


def _build_cart_public(session: SessionDep, user_id: uuid.UUID) -> CartPublic:
    cart_items = session.exec(
        select(CartItem).where(CartItem.user_id == user_id)
    ).all()
    items_public = []
    total = 0.0
    for ci in cart_items:
        item = session.get(Item, ci.item_id)
        if not item:
            continue
        price = item.price or 0.0
        total += price * ci.quantity
        items_public.append(CartItemPublic(
            id=ci.id,
            item_id=ci.item_id,
            quantity=ci.quantity,
            added_at=ci.added_at,
            title=item.title,
            brand=item.brand,
            image_url=item.image_url,
            price=item.price,
            mrp=item.mrp,
        ))
    return CartPublic(items=items_public, total=round(total, 2))


@router.get("/", response_model=CartPublic)
def get_cart(session: SessionDep, current_user: CurrentUser) -> Any:
    return _build_cart_public(session, current_user.id)


@router.get("/recommendations")
def get_cart_recommendations(
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    """
    Return Perfect Match skincare recommendations based on all items in the cart.
    Aggregates ingredient-synergy matches across cart items, excluding duplicates
    and items already in the cart.
    """
    from app.skincare_rules import get_skincare_recommendations as get_recs

    cart_items = session.exec(
        select(CartItem).where(CartItem.user_id == current_user.id)
    ).all()

    cart_item_ids = {str(ci.item_id) for ci in cart_items}
    if not cart_item_ids:
        return {"perfect_match": []}

    seen: set[str] = set(cart_item_ids)
    perfect_match: list[dict] = []

    for ci in cart_items:
        recs = get_recs(str(ci.item_id))
        for entry in recs.get("perfect_match", []):
            iid = entry["item_id"]
            if iid in seen:
                continue
            it = session.get(Item, uuid.UUID(iid))
            if not it:
                continue
            seen.add(iid)
            owner = session.get(User, it.owner_id)
            owner_name = (owner.full_name or owner.email) if owner else None
            pub = ItemPublic.model_validate(it)
            pub.owner_name = owner_name
            perfect_match.append({
                **pub.model_dump(),
                "reason": entry["reason"],
                "synergy_ingredient": entry["synergy_ingredient"],
            })
            if len(perfect_match) >= 8:
                break
        if len(perfect_match) >= 8:
            break

    return {"perfect_match": perfect_match}


@router.post("/{item_id}", response_model=CartPublic)
def add_to_cart(
    item_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
    quantity: int = 1,
) -> Any:
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    existing = session.exec(
        select(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.item_id == item_id,
        )
    ).first()

    if existing:
        existing.quantity += quantity
        session.add(existing)
    else:
        cart_item = CartItem(user_id=current_user.id, item_id=item_id, quantity=quantity)
        session.add(cart_item)

    session.commit()
    return _build_cart_public(session, current_user.id)


@router.patch("/{item_id}", response_model=CartPublic)
def update_cart_item(
    item_id: uuid.UUID,
    quantity: int,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    if quantity < 1:
        raise HTTPException(status_code=422, detail="Quantity must be at least 1")

    ci = session.exec(
        select(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.item_id == item_id,
        )
    ).first()
    if not ci:
        raise HTTPException(status_code=404, detail="Item not in cart")

    ci.quantity = quantity
    session.add(ci)
    session.commit()
    return _build_cart_public(session, current_user.id)


@router.delete("/clear", response_model=Message)
def clear_cart(session: SessionDep, current_user: CurrentUser) -> Message:
    cart_items = session.exec(
        select(CartItem).where(CartItem.user_id == current_user.id)
    ).all()
    for ci in cart_items:
        session.delete(ci)
    session.commit()
    return Message(message="Cart cleared")


@router.delete("/{item_id}", response_model=CartPublic)
def remove_from_cart(
    item_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> Any:
    ci = session.exec(
        select(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.item_id == item_id,
        )
    ).first()
    if not ci:
        raise HTTPException(status_code=404, detail="Item not in cart")

    session.delete(ci)
    session.commit()
    return _build_cart_public(session, current_user.id)
