"""add review rating aggregate triggers

Revision ID: f1c92a77b3de
Revises: c3f0e1b9a4d2
Create Date: 2026-05-10 16:05:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f1c92a77b3de"
down_revision = "c3f0e1b9a4d2"
branch_labels = None
depends_on = None


def upgrade():
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
