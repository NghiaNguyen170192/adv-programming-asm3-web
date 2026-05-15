"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-15 00:00:00.000000

Consolidated from all previous migrations:
  e2412789c190 → 9c0a54914c78 → d98dd8ec85a3 → 1a31ce608336
  → fe56fa70289e → b0a1c2d3e4f5 → 778b09ca48e8 → a3f1c8d2b5e4
"""

import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ── user ──────────────────────────────────────────────────────────────────
    op.create_table(
        "user",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("pro_user", sa.Boolean(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("hashed_password", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)

    # ── tag ───────────────────────────────────────────────────────────────────
    op.create_table(
        "tag",
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── item ──────────────────────────────────────────────────────────────────
    op.create_table(
        "item",
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("mrp", sa.Float(), nullable=True),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("product_url", sa.String(length=1000), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("product_rating", sa.Float(), nullable=True),
        sa.Column("product_rating_count", sa.Integer(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_item_product_id"), "item", ["product_id"], unique=True)

    # ── itemtag ───────────────────────────────────────────────────────────────
    op.create_table(
        "itemtag",
        sa.Column("item_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["item.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tag.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("item_id", "tag_id"),
    )

    # ── review ────────────────────────────────────────────────────────────────
    op.create_table(
        "review",
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("review_id", sa.UUID(), nullable=True),
        sa.Column("review_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_a_buyer", sa.Boolean(), nullable=True),
        sa.Column("predicted_is_a_buyer", sa.Boolean(), nullable=True),
        sa.Column("prediction_confidence", sa.Float(), nullable=True),
        sa.Column("review_label", sa.String(length=255), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("item_id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["item.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_review_review_id"), "review", ["review_id"], unique=True)

    # ── cartitem ──────────────────────────────────────────────────────────────
    op.create_table(
        "cartitem",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("item_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["item_id"], ["item.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cartitem_item_id"), "cartitem", ["item_id"], unique=False)
    op.create_index(op.f("ix_cartitem_user_id"), "cartitem", ["user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_cartitem_user_id"), table_name="cartitem")
    op.drop_index(op.f("ix_cartitem_item_id"), table_name="cartitem")
    op.drop_table("cartitem")
    op.drop_index(op.f("ix_review_review_id"), table_name="review")
    op.drop_table("review")
    op.drop_table("itemtag")
    op.drop_index(op.f("ix_item_product_id"), table_name="item")
    op.drop_table("item")
    op.drop_table("tag")
    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")
