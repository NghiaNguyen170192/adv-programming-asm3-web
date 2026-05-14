"""add cart item table

Revision ID: a3f1c8d2b5e4
Revises: 778b09ca48e8
Create Date: 2026-05-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision = 'a3f1c8d2b5e4'
down_revision = '778b09ca48e8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'cartitem',
        sa.Column('id', UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', UUID(as_uuid=False), nullable=False),
        sa.Column('item_id', UUID(as_uuid=False), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['item_id'], ['item.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_cartitem_item_id'), 'cartitem', ['item_id'], unique=False)
    op.create_index(op.f('ix_cartitem_user_id'), 'cartitem', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_cartitem_item_id'), table_name='cartitem')
    op.drop_index(op.f('ix_cartitem_user_id'), table_name='cartitem')
    op.drop_table('cartitem')
