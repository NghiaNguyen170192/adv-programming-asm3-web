"""
Seed the database from dataset.csv (located at project root).

Run once during prestart to populate items, tags, and reviews
so every developer gets data on first `docker compose up`.
"""

import csv
import logging
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, func, select

from app.core.db import engine
from app.models import Item, ItemTag, Review, Tag, User

logger = logging.getLogger(__name__)

# Resolve CSV path – works both inside Docker (/app/dataset.csv)
# and locally (/Users/.../adv-programming-asm3-web/dataset.csv)
# __file__ = .../backend/app/seed_data.py → parents[2] = .../backend
# In Docker: /app/backend/app/seed_data.py → parents[3] = /app
_HERE = Path(__file__).resolve()
CSV_PATH = _HERE.parents[2] / "dataset.csv"
if not CSV_PATH.exists():
    CSV_PATH = _HERE.parents[3] / "dataset.csv"

IMAGE_CSV_PATH = _HERE.parents[2] / "image_urls.csv"
if not IMAGE_CSV_PATH.exists():
    IMAGE_CSV_PATH = _HERE.parents[3] / "image_urls.csv"


def _parse_float(val: str) -> float | None:
    try:
        return float(val) if val else None
    except ValueError:
        return None


def _parse_int(val: str) -> int | None:
    try:
        return int(float(val)) if val else None
    except ValueError:
        return None


def _parse_bool(val: str) -> bool:
    return val.strip().lower() == "true"


def _parse_datetime(val: str) -> datetime | None:
    if not val:
        return None
    try:
        return datetime.strptime(val.strip(), "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def seed(session: Session) -> None:
    """Import products, tags, and reviews from dataset.csv."""

    # Skip if items already exist (idempotent)
    count = session.exec(select(func.count()).select_from(Item)).one()
    if count > 0:
        logger.info("Database already has %d items – skipping seed.", count)
        return

    if not CSV_PATH.exists():
        logger.warning("dataset.csv not found at %s – skipping seed.", CSV_PATH)
        return

    # We need an owner for the seeded items – use the first superuser
    owner = session.exec(select(User).where(User.is_superuser)).first()
    if not owner:
        logger.warning("No superuser found – skipping seed.")
        return

    logger.info("Seeding database from %s …", CSV_PATH)

    # --- Load image URLs mapping ------------------------------------------
    image_map: dict[int, str] = {}
    if IMAGE_CSV_PATH.exists():
        with open(IMAGE_CSV_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                pid = _parse_int(row.get("product_id", ""))
                url = (row.get("image_url") or "").strip()
                if pid is not None and url:
                    image_map[pid] = url
        logger.info("Loaded %d image URLs.", len(image_map))

    # --- Pass 1: collect unique products and tags -------------------------
    products: dict[int, dict] = {}  # product_id -> product info
    all_tags: set[str] = set()
    reviews_raw: list[dict] = []

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = _parse_int(row.get("product_id", ""))
            if pid is None:
                continue

            # Collect product (deduplicate by product_id)
            if pid not in products:
                products[pid] = {
                    "product_id": pid,
                    "title": (row.get("product_title") or "").strip(),
                    "brand": (row.get("brand_name") or "").strip() or None,
                    "price": _parse_float(row.get("price", "")),
                    "product_rating": _parse_float(row.get("avg_product_rating", "")),
                    "product_rating_count": _parse_int(
                        row.get("product_rating_count", "")
                    ),
                    "product_url": (row.get("product_url") or "").strip() or None,
                    "tags": set(),
                }

            # Collect tags for this product
            raw_tags = (row.get("product_tags") or "").strip()
            if raw_tags:
                for t in raw_tags.split(","):
                    t = t.strip()
                    if t:
                        products[pid]["tags"].add(t)
                        all_tags.add(t)

            # Collect review
            reviews_raw.append(
                {
                    "product_id": pid,
                    "title": (row.get("review_title") or "").strip()[:255],
                    "description": (row.get("review_text") or "").strip()[:1000],
                    "rating": _parse_float(row.get("review_rating", "")),
                    "is_a_buyer": _parse_bool(row.get("is_a_buyer", "")),
                    "created_at": _parse_datetime(row.get("review_date", "")),
                }
            )

    logger.info(
        "Found %d unique products, %d tags, %d reviews.",
        len(products),
        len(all_tags),
        len(reviews_raw),
    )

    # --- Pass 2: create Tag rows -----------------------------------------
    tag_map: dict[str, uuid.UUID] = {}
    for tag_name in sorted(all_tags):
        tag = Tag(name=tag_name)
        session.add(tag)
        session.flush()
        tag_map[tag_name] = tag.id

    # --- Pass 3: create Item rows ----------------------------------------
    pid_to_uuid: dict[int, uuid.UUID] = {}
    for pid, info in products.items():
        item = Item(
            product_id=info["product_id"],
            title=info["title"] or f"Product {pid}",
            brand=info["brand"],
            price=info["price"],
            product_rating=info["product_rating"],
            product_rating_count=info["product_rating_count"],
            product_url=info["product_url"],
            image_url=image_map.get(pid) or (random.choice(list(image_map.values())) if image_map else None),
            owner_id=owner.id,
        )
        session.add(item)
        session.flush()
        pid_to_uuid[pid] = item.id

        # Link tags
        for t in info["tags"]:
            if t in tag_map:
                session.add(ItemTag(item_id=item.id, tag_id=tag_map[t]))

    # --- Pass 4: create Review rows --------------------------------------
    review_count = 0
    for r in reviews_raw:
        item_uuid = pid_to_uuid.get(r["product_id"])
        if not item_uuid:
            continue
        rating_val = r["rating"]
        rating_int = max(1, min(5, int(rating_val))) if rating_val else 3
        desc = r["description"] or "No description"
        review = Review(
            title=r["title"] or "Review",
            description=desc,
            rating=rating_int,
            is_a_buyer=r["is_a_buyer"],
            review_date=r["created_at"],
            item_id=item_uuid,
            owner_id=owner.id,
        )
        session.add(review)
        review_count += 1

    session.commit()
    logger.info(
        "Seed complete: %d items, %d tags, %d reviews inserted.",
        len(pid_to_uuid),
        len(tag_map),
        review_count,
    )


def run_seed() -> None:
    with Session(engine) as session:
        seed(session)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_seed()