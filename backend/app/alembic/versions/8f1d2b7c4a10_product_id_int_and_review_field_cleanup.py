"""product id int and review field cleanup

Revision ID: 8f1d2b7c4a10
Revises: 7b2f4c1de913
Create Date: 2026-05-10 02:05:00.000000

"""

import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8f1d2b7c4a10"
down_revision = "7b2f4c1de913"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("item", sa.Column("product_id_int", sa.Integer(), nullable=True))

    op.execute(
        sa.text(
            """
            WITH numbered AS (
                SELECT id, row_number() OVER (ORDER BY created_at NULLS LAST, id) AS rn
                FROM item
            )
            UPDATE item
            SET product_id_int = numbered.rn
            FROM numbered
            WHERE item.id = numbered.id
            """
        )
    )

    op.drop_index("ix_item_product_id", table_name="item")
    op.drop_column("item", "product_id")
    op.alter_column("item", "product_id_int", new_column_name="product_id")
    op.create_index("ix_item_product_id", "item", ["product_id"], unique=True)

    op.drop_column("review", "recommend_label")
    op.drop_column("review", "user_override")
    op.drop_column("review", "author")


def downgrade():
    op.add_column("review", sa.Column("author", sa.String(length=255), nullable=True))
    op.add_column("review", sa.Column("user_override", sa.Boolean(), nullable=True))
    op.add_column("review", sa.Column("recommend_label", sa.Boolean(), nullable=True))

    op.add_column("item", sa.Column("product_id_uuid", sa.Uuid(), nullable=True))

    connection = op.get_bind()
    item_rows = connection.execute(sa.text("SELECT id FROM item ORDER BY created_at NULLS LAST, id")).fetchall()
    for row in item_rows:
        connection.execute(
            sa.text("UPDATE item SET product_id_uuid = :product_id WHERE id = :id"),
            {"product_id": uuid.uuid4(), "id": row.id},
        )

    op.drop_index("ix_item_product_id", table_name="item")
    op.drop_column("item", "product_id")
    op.alter_column("item", "product_id_uuid", new_column_name="product_id")
    op.create_index("ix_item_product_id", "item", ["product_id"], unique=True)
