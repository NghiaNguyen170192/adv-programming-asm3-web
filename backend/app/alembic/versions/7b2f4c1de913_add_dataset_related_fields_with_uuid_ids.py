"""add dataset related fields with uuid ids

Revision ID: 7b2f4c1de913
Revises: 6e4a228e6fb9
Create Date: 2026-05-10 10:20:00.000000

"""

import uuid

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = "7b2f4c1de913"
down_revision = "6e4a228e6fb9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user", sa.Column("pro_user", sa.Boolean(), nullable=True))

    op.add_column("item", sa.Column("product_id", sa.Uuid(), nullable=True))
    op.add_column("item", sa.Column("mrp", sa.Float(), nullable=True))
    op.add_column("item", sa.Column("product_rating", sa.Float(), nullable=True))
    op.add_column("item", sa.Column("product_rating_count", sa.Integer(), nullable=True))
    op.add_column("item", sa.Column("product_url", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True))

    op.add_column("review", sa.Column("review_id", sa.Uuid(), nullable=True))
    op.add_column("review", sa.Column("review_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("review", sa.Column("is_a_buyer", sa.Boolean(), nullable=True))
    op.add_column("review", sa.Column("author", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True))
    op.add_column("review", sa.Column("review_label", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True))

    connection = op.get_bind()

    item_rows = connection.execute(sa.text("SELECT id FROM item")).fetchall()
    for row in item_rows:
        connection.execute(
            sa.text("UPDATE item SET product_id = :product_id WHERE id = :id"),
            {"product_id": uuid.uuid4(), "id": row.id},
        )

    review_rows = connection.execute(sa.text("SELECT id FROM review")).fetchall()
    for row in review_rows:
        connection.execute(
            sa.text("UPDATE review SET review_id = :review_id WHERE id = :id"),
            {"review_id": uuid.uuid4(), "id": row.id},
        )

    op.alter_column("item", "product_id", nullable=False)
    op.alter_column("review", "review_id", nullable=False)

    op.create_index("ix_item_product_id", "item", ["product_id"], unique=True)
    op.create_index("ix_review_review_id", "review", ["review_id"], unique=True)


def downgrade():
    op.drop_index("ix_review_review_id", table_name="review")
    op.drop_index("ix_item_product_id", table_name="item")

    op.drop_column("review", "review_label")
    op.drop_column("review", "author")
    op.drop_column("review", "is_a_buyer")
    op.drop_column("review", "review_date")
    op.drop_column("review", "review_id")

    op.drop_column("item", "product_url")
    op.drop_column("item", "product_rating_count")
    op.drop_column("item", "product_rating")
    op.drop_column("item", "mrp")
    op.drop_column("item", "product_id")

    op.drop_column("user", "pro_user")
