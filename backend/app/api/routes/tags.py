import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Tag, TagCreate, TagPublic, Message

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/", response_model=list[TagPublic])
def read_tags(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    statement = select(Tag).offset(skip).limit(limit)
    tags = session.exec(statement).all()
    return tags


@router.get("/{id}", response_model=TagPublic)
def read_tag(session: SessionDep, id: uuid.UUID) -> Any:
    tag = session.get(Tag, id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.post("/", response_model=TagPublic)
def create_tag(*, session: SessionDep, current_user: CurrentUser, tag_in: TagCreate) -> Any:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    tag = Tag.model_validate(tag_in)
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag


@router.delete("/{id}")
def delete_tag(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Message:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    tag = session.get(Tag, id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    session.delete(tag)
    session.commit()
    return Message(message="Tag deleted successfully")
