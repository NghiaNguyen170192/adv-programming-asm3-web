"""Initial schema (consolidated)

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-15 00:00:00.000000

"""
import sqlalchemy as sa
import sqlmodel.sql.sqltypes
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ── user ──────────────────────────────────────────────────────────────────
    op.create_table(
        "user",
        sa.Column("email", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("full_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("hashed_password", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pro_user", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)

    # ── tag ───────────────────────────────────────────────────────────────────
    op.create_table(
        "tag",
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── item ──────────────────────────────────────────────────────────────────
    op.create_table(
        "item",
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("mrp", sa.Float(), nullable=True),
        sa.Column("brand", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("product_url", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("image_url", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_rating", sa.Float(), nullable=True),
        sa.Column("product_rating_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_item_product_id", "item", ["product_id"], unique=True)

    # ── itemtag ───────────────────────────────────────────────────────────────
    op.create_table(
        "itemtag",
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["item.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tag.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("item_id", "tag_id"),
    )

    # ── review ────────────────────────────────────────────────────────────────
    op.create_table(
        "review",
        sa.Column("title", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("review_id", sa.Uuid(), nullable=True),
        sa.Column("review_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_a_buyer", sa.Boolean(), nullable=True),
        sa.Column("predicted_is_a_buyer", sa.Boolean(), nullable=True),
        sa.Column("prediction_confidence", sa.Float(), nullable=True),
        sa.Column("review_label", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["item.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_review_id", "review", ["review_id"], unique=True)

    # ── cartitem ──────────────────────────────────────────────────────────────
    op.create_table(
        "cartitem",
        sa.Column("id", UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", UUID(as_uuid=False), nullable=False),
        sa.Column("item_id", UUID(as_uuid=False), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["item_id"], ["item.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cartitem_item_id"), "cartitem", ["item_id"], unique=False)
    op.create_index(op.f("ix_cartitem_user_id"), "cartitem", ["user_id"], unique=False)

    # ── item_rating_aggregate ─────────────────────────────────────────────────
    op.create_table(
        "item_rating_aggregate",
        sa.Column("item_id", sa.Uuid(), sa.ForeignKey("item.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rating_sum", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rating_avg", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("item_id"),
    )

    # ── PostgreSQL functions and triggers ─────────────────────────────────────
    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION refresh_item_rating_aggregate(p_item_id uuid)
            RETURNS void
            LANGUAGE plpgsql
            AS $$
            DECLARE
                v_count int;
                v_sum int;
                v_avg double precision;
            BEGIN
                SELECT
                    COUNT(*)::int,
                    COALESCE(SUM(rating), 0)::int,
                    AVG(rating)::float
                INTO v_count, v_sum, v_avg
                FROM review
                WHERE item_id = p_item_id;

                IF v_count = 0 THEN
                    DELETE FROM item_rating_aggregate WHERE item_id = p_item_id;
                    UPDATE item
                    SET product_rating_count = 0,
                        product_rating = NULL
                    WHERE id = p_item_id;
                ELSE
                    INSERT INTO item_rating_aggregate (item_id, rating_count, rating_sum, rating_avg)
                    VALUES (p_item_id, v_count, v_sum, v_avg)
                    ON CONFLICT (item_id) DO UPDATE
                    SET rating_count = EXCLUDED.rating_count,
                        rating_sum = EXCLUDED.rating_sum,
                        rating_avg = EXCLUDED.rating_avg;

                    UPDATE item
                    SET product_rating_count = v_count,
                        product_rating = v_avg
                    WHERE id = p_item_id;
                END IF;
            END;
            $$;
            """
        )
    )

    op.execute(
        sa.text(
            """
            CREATE OR REPLACE FUNCTION trg_refresh_item_rating_aggregate()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                IF TG_OP = 'INSERT' THEN
                    PERFORM refresh_item_rating_aggregate(NEW.item_id);
                    RETURN NEW;
                ELSIF TG_OP = 'UPDATE' THEN
                    IF NEW.item_id <> OLD.item_id THEN
                        PERFORM refresh_item_rating_aggregate(OLD.item_id);
                    END IF;
                    PERFORM refresh_item_rating_aggregate(NEW.item_id);
                    RETURN NEW;
                ELSIF TG_OP = 'DELETE' THEN
                    PERFORM refresh_item_rating_aggregate(OLD.item_id);
                    RETURN OLD;
                END IF;

                RETURN NULL;
            END;
            $$;
            """
        )
    )

    op.execute(
        sa.text(
            """
            DROP TRIGGER IF EXISTS review_rating_aggregate_trg ON review;
            CREATE TRIGGER review_rating_aggregate_trg
            AFTER INSERT OR UPDATE OF rating, item_id OR DELETE ON review
            FOR EACH ROW
            EXECUTE FUNCTION trg_refresh_item_rating_aggregate();
            """
        )
    )


def downgrade():
    op.execute(sa.text("DROP TRIGGER IF EXISTS review_rating_aggregate_trg ON review;"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS trg_refresh_item_rating_aggregate();"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS refresh_item_rating_aggregate(uuid);"))

    op.drop_table("item_rating_aggregate")
    op.drop_index(op.f("ix_cartitem_user_id"), table_name="cartitem")
    op.drop_index(op.f("ix_cartitem_item_id"), table_name="cartitem")
    op.drop_table("cartitem")
    op.drop_index("ix_review_review_id", table_name="review")
    op.drop_table("review")
    op.drop_table("itemtag")
    op.drop_index("ix_item_product_id", table_name="item")
    op.drop_table("item")
    op.drop_table("tag")
    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")
