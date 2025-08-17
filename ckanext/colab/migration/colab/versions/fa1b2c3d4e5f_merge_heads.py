"""merge heads a0b1c2d3e4f5 and e9f0a1b2c3d4

Revision ID: fa1b2c3d4e5f
Revises: a0b1c2d3e4f5, e9f0a1b2c3d4
Create Date: 2025-08-17 18:00:00.000000

"""
from alembic import op  # noqa: F401  (kept for consistency)
import sqlalchemy as sa  # noqa: F401  (kept for consistency)


# revision identifiers, used by Alembic.
revision = 'fa1b2c3d4e5f'
down_revision = ('a0b1c2d3e4f5', 'e9f0a1b2c3d4')
branch_labels = None
depends_on = None


def upgrade():
    # No-op merge migration to unify parallel heads
    pass


def downgrade():
    # No-op merge migration
    pass


