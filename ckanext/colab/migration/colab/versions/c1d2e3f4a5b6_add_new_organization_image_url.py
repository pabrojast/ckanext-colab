"""add new_organization_image_url field

Revision ID: c1d2e3f4a5b6
Revises: b1c2d3e4f5a6
Create Date: 2026-05-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4a5b6'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade():
    # Add the new_organization_image_url column to the colab table (idempotent).
    # Stores the uploaded logo filename for new organizations requested
    # through the registration form.
    try:
        op.add_column('colab', sa.Column('new_organization_image_url', sa.String))
    except Exception:
        # Column already exists, continue
        pass


def downgrade():
    # Remove the new_organization_image_url column
    try:
        op.drop_column('colab', 'new_organization_image_url')
    except Exception:
        # Column doesn't exist, continue
        pass
