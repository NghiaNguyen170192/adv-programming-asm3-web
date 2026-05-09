import uuid

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.models import Item, ItemTag, Tag, TagCreate, TagPublic

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/", response_model=list[TagPublic])
def get_all_tags(session: SessionDep) -> list[TagPublic]:
    """Get all available tags."""
    tags = session.exec(select(Tag)).all()
    return tags


@router.post("/", response_model=TagPublic)
def create_tag(
    tag_in: TagCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> TagPublic:
    """Create a new tag. Superuser only."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    existing = session.exec(select(Tag).where(Tag.name == tag_in.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tag already exists")

    tag = Tag(name=tag_in.name)
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


@router.post("/item/{item_id}/{tag_id}")
def add_tag_to_item(
    item_id: uuid.UUID,
    tag_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """Add a tag to an item."""
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    tag = session.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    existing = session.exec(
        select(ItemTag).where(ItemTag.item_id == item_id, ItemTag.tag_id == tag_id)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tag already added to this item")

    item_tag = ItemTag(item_id=item_id, tag_id=tag_id)
    session.add(item_tag)
    session.commit()
    return {"message": "Tag added to item successfully"}


@router.delete("/item/{item_id}/{tag_id}")
def remove_tag_from_item(
    item_id: uuid.UUID,
    tag_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """Remove a tag from an item."""
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    item_tag = session.exec(
        select(ItemTag).where(ItemTag.item_id == item_id, ItemTag.tag_id == tag_id)
    ).first()
    if not item_tag:
        raise HTTPException(status_code=404, detail="Tag not found on this item")

    session.delete(item_tag)
    session.commit()
    return {"message": "Tag removed from item successfully"}