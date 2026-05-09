#!/usr/bin/env python
"""
Load cosmetics_beauty_products_reviews.csv into the database.

Creates users from the 'author' column, items from unique products,
reviews from every row, and tags from product_tags.

Email generation rules
----------------------
  author name            →  email
  ─────────────────────────────────────────────────────────────
  "Yogita Vaishnav"      →  yog.vai@gmail.com
  "Priyanka"             →  pri.pri@gmail.com   (single name → duplicate)
  "V V"                  →  v.v@gmail.com
  "M ."                  →  m.m@gmail.com       (dot-only token ignored)

Default password for every new user: aaaaaaaa

Usage (inside the running backend Docker container)
---------------------------------------------------
    docker compose exec backend python /app/scripts/load_data.py /data/cosmetics_beauty_products_reviews.csv

Usage with a local Python environment (DATABASE_URL must be set):
    cd adv-programming-asm3-web
    PYTHONPATH=backend python backend/scripts/load_data.py /path/to/cosmetics_beauty_products_reviews.csv
"""

import csv
import logging
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

# Allow running from repo root with PYTHONPATH=backend
from app.core.db import engine
from app.core.security import get_password_hash
from app.models import Item, ItemTag, Review, Tag, User

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_PASSWORD = "aaaaaaaa"
EMAIL_DOMAIN = "@gmail.com"
DATE_FMT = "%d/%m/%Y %H:%M"
ISO_DATE_FMT = "%Y-%m-%d %H:%M:%S"


# ─── Email helpers ────────────────────────────────────────────────────────────


def _alpha(token: str) -> str:
    """Strip every non-letter character and return lowercase."""
    return re.sub(r"[^a-z]", "", token.lower())


def _name_parts(author: str) -> tuple[str, str]:
    """
    Return (first_part, last_part) — each up to 3 lowercase letters — for an
    author string.  Non-alpha tokens (numbers, punctuation-only) are ignored.

    Examples:
        "Yogita Vaishnav" → ("yog", "vai")
        "Priyanka"        → ("pri", "pri")
        "V V"             → ("v",   "v")
        "M ."             → ("m",   "m")
        "ARUNDHATI GUHA ROY" → ("aru", "roy")   (last meaningful token)
    """
    tokens = author.strip().split()
    alpha_parts = [_alpha(t) for t in tokens if _alpha(t)]

    if not alpha_parts:
        return ("usr", "usr")

    first = alpha_parts[0][:3]
    last = alpha_parts[-1][:3]          # same as first when there is only one part
    return (first, last)


def _unique_email(first: str, last: str, taken: set[str]) -> str:
    base = f"{first}.{last}{EMAIL_DOMAIN}"
    if base not in taken:
        return base
    counter = 1
    while True:
        candidate = f"{first}.{last}{counter}{EMAIL_DOMAIN}"
        if candidate not in taken:
            return candidate
        counter += 1


# ─── Date helper ──────────────────────────────────────────────────────────────


def _parse_date(date_str: str) -> datetime | None:
    s = date_str.strip()
    if not s:
        return None
    # Try ISO format first (YYYY-MM-DD HH:MM:SS)
    try:
        return datetime.strptime(s, ISO_DATE_FMT).replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    # Try original format (DD/MM/YYYY HH:MM)
    try:
        return datetime.strptime(s, DATE_FMT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


# ─── Main ─────────────────────────────────────────────────────────────────────


def main(csv_path: str) -> None:
    path = Path(csv_path)
    if not path.exists():
        logger.error("File not found: %s", csv_path)
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    logger.info("Read %d rows from CSV", len(rows))

    with Session(engine) as session:

        # ── Superuser (item owner) ─────────────────────────────────────────
        superuser = session.exec(select(User).where(User.is_superuser == True)).first()
        if not superuser:
            logger.error("No superuser found — run `python -m app.initial_data` first.")
            sys.exit(1)
        logger.info("Using superuser '%s' as item owner", superuser.email)

        # ── 1. Users ──────────────────────────────────────────────────────
        taken_emails: set[str] = set(session.exec(select(User.email)).all())
        logger.info("Existing users: %d", len(taken_emails))

        hashed_pw = get_password_hash(DEFAULT_PASSWORD)

        # Map author_name → User (only newly created users)
        author_user_map: dict[str, User] = {}

        unique_authors = sorted({r["author"].strip() for r in rows if r["author"].strip()})
        logger.info("Unique authors in CSV: %d", len(unique_authors))

        for author in unique_authors:
            first, last = _name_parts(author)
            email = _unique_email(first, last, taken_emails)
            taken_emails.add(email)

            user = User(
                email=email,
                hashed_password=hashed_pw,
                full_name=author[:255],
                is_active=True,
                is_superuser=False,
            )
            session.add(user)
            author_user_map[author] = user

        session.flush()
        logger.info("Flushed %d new users", len(author_user_map))

        # ── 2. Tags ───────────────────────────────────────────────────────
        tag_map: dict[str, Tag] = {t.name: t for t in session.exec(select(Tag)).all()}

        all_tag_names: set[str] = set()
        for row in rows:
            for raw in row.get("product_tags", "").split(","):
                name = raw.strip()
                if name:
                    all_tag_names.add(name)

        for name in all_tag_names:
            if name not in tag_map:
                tag = Tag(name=name)
                session.add(tag)
                tag_map[name] = tag

        session.flush()
        logger.info("Tags ready: %d", len(tag_map))

        # ── 3. Items (one per unique product_id) ──────────────────────────
        item_map: dict[int, Item] = {}
        for ei in session.exec(select(Item)).all():
            if ei.product_id is not None:
                item_map[ei.product_id] = ei

        # Pick one representative row per product_id
        product_row: dict[int, dict] = {}
        for row in rows:
            try:
                pid = int(row["product_id"])
            except (ValueError, KeyError):
                continue
            if pid not in product_row:
                product_row[pid] = row

        new_items = 0
        for pid, row in product_row.items():
            if pid in item_map:
                continue

            def _float(val: str) -> float | None:
                v = val.strip()
                return float(v) if v else None

            def _int(val: str) -> int:
                v = val.strip()
                return int(v) if v else 0

            item = Item(
                title=(row.get("product_title") or "Untitled")[:255],
                product_id=pid,
                price=_float(row.get("price", "")),
                brand=(row.get("brand_name") or "")[:255] or None,
                product_url=(row.get("product_url") or "")[:1000] or None,
                product_rating=_float(row.get("avg_product_rating", "")),
                product_rating_count=_int(row.get("product_rating_count", "")),
                owner_id=superuser.id,
            )
            session.add(item)
            item_map[pid] = item
            new_items += 1

        session.flush()
        logger.info("Items ready: %d (%d new)", len(item_map), new_items)

        # ── 3b. Item–Tag associations ──────────────────────────────────────
        existing_assocs: set[tuple[uuid.UUID, uuid.UUID]] = {
            (a.item_id, a.tag_id) for a in session.exec(select(ItemTag)).all()
        }

        for pid, row in product_row.items():
            if pid not in item_map:
                continue
            item = item_map[pid]
            for raw in row.get("product_tags", "").split(","):
                name = raw.strip()
                if not name or name not in tag_map:
                    continue
                tag = tag_map[name]
                pair = (item.id, tag.id)
                if pair not in existing_assocs:
                    session.add(ItemTag(item_id=item.id, tag_id=tag.id))
                    existing_assocs.add(pair)

        session.flush()

        # ── 4. Reviews ────────────────────────────────────────────────────
        existing_review_ids: set[uuid.UUID] = set(
            session.exec(select(Review.review_id)).all()
        )

        inserted = 0
        skipped = 0
        BATCH = 5000

        for row in rows:
            author = row.get("author", "").strip()
            if author not in author_user_map:
                skipped += 1
                continue

            try:
                pid = int(row["product_id"])
            except (ValueError, KeyError):
                skipped += 1
                continue

            if pid not in item_map:
                skipped += 1
                continue

            # Map CSV review_id (integer) → deterministic UUID
            try:
                rid_int = int(row.get("review_id", "").strip())
                # Clamp to valid UUID int range; UUID int must be 0 ≤ n < 2**128
                review_uuid = uuid.UUID(int=abs(rid_int) % (2**128))
            except (ValueError, AttributeError):
                review_uuid = uuid.uuid4()

            if review_uuid in existing_review_ids:
                skipped += 1
                continue

            try:
                rating = max(1, min(5, int(row.get("review_rating", "3"))))
            except ValueError:
                rating = 3

            is_buyer = row.get("is_a_buyer", "").strip().upper() == "TRUE"
            title = (row.get("review_title") or "Review")[:255] or "Review"
            description = (row.get("review_text") or ".")[:2000] or "."
            review_label = (row.get("review_label") or "").strip()
            review_label = review_label[:255] if review_label else None

            review = Review(
                title=title,
                description=description,
                rating=rating,
                review_id=review_uuid,
                review_date=_parse_date(row.get("review_date", "")),
                is_a_buyer=is_buyer,
                review_label=review_label,
                item_id=item_map[pid].id,
                owner_id=author_user_map[author].id,
            )
            session.add(review)
            existing_review_ids.add(review_uuid)
            inserted += 1

            if inserted % BATCH == 0:
                session.commit()
                logger.info("  ... %d reviews committed", inserted)

        session.commit()

    logger.info(
        "Done!  Users: %d | Items: %d (new: %d) | Tags: %d | Reviews inserted: %d | skipped: %d",
        len(author_user_map),
        len(item_map),
        new_items,
        len(tag_map),
        inserted,
        skipped,
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {Path(sys.argv[0]).name} <path_to_csv>")
        sys.exit(1)
    main(sys.argv[1])
