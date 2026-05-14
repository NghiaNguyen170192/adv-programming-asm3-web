"""add item rating aggregate table

Revision ID: c3f0e1b9a4d2
Revises: 778b09ca48e8
Create Date: 2026-05-10 14:45:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c3f0e1b9a4d2"
down_revision = "778b09ca48e8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "item_rating_aggregate",
        sa.Column("item_id", sa.Uuid(), sa.ForeignKey("item.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rating_sum", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rating_avg", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("item_id"),
    )

    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            INSERT INTO item_rating_aggregate (item_id, rating_count, rating_sum, rating_avg)
            SELECT
                item_id,
                COUNT(*)::int AS rating_count,
                COALESCE(SUM(rating), 0)::int AS rating_sum,
                AVG(rating)::float AS rating_avg
            FROM review
            GROUP BY item_id
            """
        )
    )

    connection.execute(
        sa.text(
            """
            UPDATE item AS i
            SET
                product_rating_count = agg.rating_count,
                product_rating = agg.rating_avg
            FROM item_rating_aggregate AS agg
            WHERE i.id = agg.item_id
            """
        )
    )

    connection.execute(
        sa.text(
            """
            UPDATE item
            SET
                product_rating_count = 0,
                product_rating = NULL
            WHERE id NOT IN (SELECT item_id FROM item_rating_aggregate)
            """
        )
    )


def downgrade():
    op.drop_table("item_rating_aggregate")
