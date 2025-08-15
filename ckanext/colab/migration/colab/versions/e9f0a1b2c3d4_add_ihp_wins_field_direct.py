"""add ihp_wins field direct

Revision ID: e9f0a1b2c3d4
Revises: e8f9a0b1c2d4
Create Date: 2025-08-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e9f0a1b2c3d4'
down_revision = 'e8f9a0b1c2d4'
branch_labels = None
depends_on = None


def upgrade():
    # Add the ihp_wins column to the colab table (idempotent)
    try:
        op.add_column('colab', sa.Column('ihp_wins', sa.String))
    except Exception:
        # Column already exists, continue
        pass


def downgrade():
    # Remove the ihp_wins column
    try:
        op.drop_column('colab', 'ihp_wins')
    except Exception:
        # Column doesn't exist, continue
        pass


