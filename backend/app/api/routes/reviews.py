import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Item,
    Review,
    ReviewCreate,
    ReviewPublic,
    ReviewsPublic,
    ReviewUpdate,
    User,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _build_review_public(session: Any, review: Review) -> ReviewPublic:
    owner = session.get(User, review.owner_id)
    item = session.get(Item, review.item_id)
    owner_name = (owner.full_name or owner.email) if owner else None
    item_title = item.title if item else None
    review_public = ReviewPublic.model_validate(review)
    review_public.owner_name = owner_name
    review_public.item_title = item_title
    return review_public


def _sync_item_rating_metrics(session, item_id: uuid.UUID) -> None:

    avg_rating, rating_count = session.exec(
        select(func.avg(Review.rating), func.count(Review.id)).where(
            Review.item_id == item_id
        )
    ).one()

    item = session.get(Item, item_id)
    if not item:
        return

    item.product_rating = float(avg_rating) if avg_rating is not None else None
    item.product_rating_count = int(rating_count or 0)
    session.add(item)


@router.get("/item/{item_id}", response_model=ReviewsPublic)
def get_reviews_by_item(
    item_id: uuid.UUID,
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
) -> ReviewsPublic:
    """Get all reviews for a specific item."""
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    count = session.exec(select(func.count()).where(Review.item_id == item_id)).one()

    reviews = session.exec(
        select(Review).where(Review.item_id == item_id).offset(skip).limit(limit)
    ).all()

    reviews_public = [_build_review_public(session, review) for review in reviews]
    return ReviewsPublic(data=reviews_public, count=count)


@router.get("/", response_model=ReviewsPublic)
def read_reviews(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> ReviewsPublic:
    """Get all reviews (superuser) or own reviews (regular user)."""
    if current_user.is_superuser:
        count = session.exec(select(func.count()).select_from(Review)).one()
        reviews = session.exec(select(Review).offset(skip).limit(limit)).all()
    else:
        count = session.exec(
            select(func.count()).where(Review.owner_id == current_user.id)
        ).one()
        reviews = session.exec(
            select(Review)
            .where(Review.owner_id == current_user.id)
            .offset(skip)
            .limit(limit)
        ).all()

    reviews_public = [_build_review_public(session, review) for review in reviews]
    return ReviewsPublic(data=reviews_public, count=count)


@router.post("/item/{item_id}", response_model=ReviewPublic)
def create_review(
    item_id: uuid.UUID,
    review_in: ReviewCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> ReviewPublic:
    """Create a new review for an item."""
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    review_data = review_in.model_dump(exclude_unset=True, exclude={"item_id"})
    review = Review.model_validate(
        review_data,
        update={
            "item_id": item_id,
            "owner_id": current_user.id,
        },
    )
    session.add(review)
    session.flush()
    _sync_item_rating_metrics(session, item_id)
    session.commit()
    session.refresh(review)
    return _build_review_public(session, review)


@router.put("/{review_id}", response_model=ReviewPublic)
def update_review(
    review_id: uuid.UUID,
    review_in: ReviewUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> ReviewPublic:
    """Update a review."""
    review = session.exec(select(Review).where(Review.review_id == review_id)).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    update_data = review_in.model_dump(exclude_unset=True)
    review.sqlmodel_update(update_data)
    session.add(review)
    session.flush()
    _sync_item_rating_metrics(session, review.item_id)
    session.commit()
    session.refresh(review)
    return _build_review_public(session, review)


@router.delete("/{review_id}")
def delete_review(
    review_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """Delete a review."""
    review = session.exec(select(Review).where(Review.review_id == review_id)).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    item_id = review.item_id
    session.delete(review)
    session.flush()
    _sync_item_rating_metrics(session, item_id)
    session.commit()
    return {"message": "Review deleted successfully"}
