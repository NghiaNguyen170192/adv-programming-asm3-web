"""Create missing tables (tag, itemtag, review) and item columns

Revision ID: b0a1c2d3e4f5
Revises: fe56fa70289e
Create Date: 2026-05-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = 'b0a1c2d3e4f5'
down_revision = 'fe56fa70289e'
branch_labels = None
depends_on = None


def upgrade():
    # --- Tag table ---
    op.create_table(
        'tag',
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- ItemTag junction table ---
    op.create_table(
        'itemtag',
        sa.Column('item_id', UUID(as_uuid=False), nullable=False),
        sa.Column('tag_id', UUID(as_uuid=False), nullable=False),
        sa.ForeignKeyConstraint(['item_id'], ['item.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tag.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('item_id', 'tag_id'),
    )

    # --- Review table (without predicted_is_a_buyer, prediction_confidence – added in next migration) ---
    op.create_table(
        'review',
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=2000), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('review_id', UUID(as_uuid=False), nullable=True),
        sa.Column('review_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_a_buyer', sa.Boolean(), nullable=True),
        sa.Column('review_label', sa.String(length=100), nullable=True),
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('item_id', UUID(as_uuid=False), nullable=False),
        sa.Column('owner_id', UUID(as_uuid=False), nullable=False),
        sa.ForeignKeyConstraint(['item_id'], ['item.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_review_review_id'), 'review', ['review_id'], unique=True)

    # --- Extra column on user table ---
    op.add_column('user', sa.Column('pro_user', sa.Boolean(), nullable=True))

    # --- Extra columns on item table ---
    op.add_column('item', sa.Column('product_id', sa.Integer(), nullable=True))
    op.add_column('item', sa.Column('price', sa.Float(), nullable=True))
    op.add_column('item', sa.Column('mrp', sa.Float(), nullable=True))
    op.add_column('item', sa.Column('brand', sa.String(length=255), nullable=True))
    op.add_column('item', sa.Column('product_url', sa.String(length=1000), nullable=True))
    op.add_column('item', sa.Column('image_url', sa.String(length=500), nullable=True))
    op.add_column('item', sa.Column('product_rating', sa.Float(), nullable=True))
    op.add_column('item', sa.Column('product_rating_count', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_item_product_id'), 'item', ['product_id'], unique=True)


def downgrade():
    op.drop_column('user', 'pro_user')
    op.drop_index(op.f('ix_item_product_id'), table_name='item')
    op.drop_column('item', 'product_rating_count')
    op.drop_column('item', 'product_rating')
    op.drop_column('item', 'image_url')
    op.drop_column('item', 'product_url')
    op.drop_column('item', 'brand')
    op.drop_column('item', 'mrp')
    op.drop_column('item', 'price')
    op.drop_column('item', 'product_id')
    op.drop_index(op.f('ix_review_review_id'), table_name='review')
    op.drop_table('review')
    op.drop_table('itemtag')
    op.drop_table('tag')
