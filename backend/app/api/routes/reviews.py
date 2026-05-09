import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import Item, Review, ReviewCreate, ReviewPublic, ReviewsPublic, ReviewUpdate

router = APIRouter(prefix="/reviews", tags=["reviews"])


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

    count = session.exec(
        select(func.count()).where(Review.item_id == item_id)
    ).one()

    reviews = session.exec(
        select(Review).where(Review.item_id == item_id).offset(skip).limit(limit)
    ).all()

    return ReviewsPublic(data=reviews, count=count)


@router.post("/item/{item_id}", response_model=ReviewPublic)
def create_review(
    item_id: uuid.UUID,
    review_in: ReviewCreate,
    session: SessionDep,
    current_user: CurrentUser,
) -> ReviewPublic:
    """Create a new review for an item. recommend_label will be set by ML model later."""
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Placeholder for ML model prediction
    # TODO: teammate integrates ML model here to predict recommend_label
    predicted_label: Optional[bool] = None

    review = Review(
        title=review_in.title,
        description=review_in.description,
        rating=review_in.rating,
        item_id=item_id,
        owner_id=current_user.id,
        recommend_label=predicted_label,
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    return review


@router.put("/{review_id}", response_model=ReviewPublic)
def update_review(
    review_id: uuid.UUID,
    review_in: ReviewUpdate,
    session: SessionDep,
    current_user: CurrentUser,
) -> ReviewPublic:
    """Update a review. Allows user to override the ML model label."""
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    update_data = review_in.model_dump(exclude_unset=True)
    review.sqlmodel_update(update_data)
    session.add(review)
    session.commit()
    session.refresh(review)
    return review


@router.delete("/{review_id}")
def delete_review(
    review_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict:
    """Delete a review."""
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    if review.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")

    session.delete(review)
    session.commit()
    return {"message": "Review deleted successfully"}







