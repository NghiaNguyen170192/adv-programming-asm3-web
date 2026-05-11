"""add predicted_is_a_buyer to review

Revision ID: 778b09ca48e8
Revises: 8f1d2b7c4a10
Create Date: 2026-05-10 03:43:14.146505

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '778b09ca48e8'
down_revision = '8f1d2b7c4a10'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('review', sa.Column('predicted_is_a_buyer', sa.Boolean(), nullable=True))
    op.add_column('review', sa.Column('prediction_confidence', sa.Float(), nullable=True))


def downgrade():
    op.drop_column('review', 'prediction_confidence')
    op.drop_column('review', 'predicted_is_a_buyer')
