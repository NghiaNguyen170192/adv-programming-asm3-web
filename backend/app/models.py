import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore[assignment]
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: Optional[datetime] = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    items:   list["Item"]   = Relationship(back_populates="owner", cascade_delete=True)
    reviews: list["Review"] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: Optional[datetime] = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title:       str            = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    price:       Optional[float] = Field(default=None, ge=0)
    brand:       Optional[str]  = Field(default=None, max_length=255)
    image_url:   Optional[str]  = Field(default=None, max_length=500)


class ItemCreate(ItemBase):
    pass


class ItemUpdate(ItemBase):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)  # type: ignore[assignment]


# ─── Tag base (defined before ItemTag and Item) ───────────────────────────────

class TagBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)


class TagCreate(TagBase):
    pass


class TagPublic(TagBase):
    id: uuid.UUID


# ─── ItemTag (junction table, must be defined before Item and Tag) ────────────

class ItemTag(SQLModel, table=True):
    item_id: uuid.UUID = Field(foreign_key="item.id", primary_key=True, ondelete="CASCADE")
    tag_id:  uuid.UUID = Field(foreign_key="tag.id",  primary_key=True, ondelete="CASCADE")


# ─── Tag database model ───────────────────────────────────────────────────────

class Tag(TagBase, table=True):
    id:    uuid.UUID    = Field(default_factory=uuid.uuid4, primary_key=True)
    items: list["Item"] = Relationship(back_populates="tags", link_model=ItemTag)


# ─── Item database model ──────────────────────────────────────────────────────

class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: Optional[datetime] = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    owner_id: uuid.UUID       = Field(foreign_key="user.id", nullable=False, ondelete="CASCADE")
    owner:    Optional[User]  = Relationship(back_populates="items")
    reviews:  list["Review"]  = Relationship(back_populates="item", cascade_delete=True)
    tags:     list[Tag]       = Relationship(back_populates="items", link_model=ItemTag)


class ItemPublic(ItemBase):
    id:         uuid.UUID
    owner_id:   uuid.UUID
    created_at: Optional[datetime] = None


class ItemsPublic(SQLModel):
    data:  list[ItemPublic]
    count: int


# ─── Review ──────────────────────────────────────────────────────────────────

class ReviewBase(SQLModel):
    title:       str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=2000)
    rating:      int = Field(ge=1, le=5)


class ReviewCreate(ReviewBase):
    item_id: uuid.UUID


class ReviewUpdate(SQLModel):
    title:         Optional[str]  = Field(default=None, max_length=255)
    description:   Optional[str]  = Field(default=None, max_length=2000)
    rating:        Optional[int]  = Field(default=None, ge=1, le=5)
    user_override: Optional[bool] = None


class Review(ReviewBase, table=True):
    id:              uuid.UUID       = Field(default_factory=uuid.uuid4, primary_key=True)
    recommend_label: Optional[bool]  = None
    user_override:   Optional[bool]  = None
    created_at:      Optional[datetime] = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    item_id:  uuid.UUID       = Field(foreign_key="item.id", nullable=False, ondelete="CASCADE")
    owner_id: uuid.UUID       = Field(foreign_key="user.id", nullable=False, ondelete="CASCADE")
    item:     Optional[Item]  = Relationship(back_populates="reviews")
    owner:    Optional["User"] = Relationship(back_populates="reviews")


class ReviewPublic(ReviewBase):
    id:              uuid.UUID
    recommend_label: Optional[bool]
    user_override:   Optional[bool]
    owner_id:        uuid.UUID
    item_id:         uuid.UUID
    created_at:      Optional[datetime] = None


class ReviewsPublic(SQLModel):
    data:  list[ReviewPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)