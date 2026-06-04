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
    #
    # Check existence with the inspector before issuing DDL. The column may
    # already exist because ensure_colab_schema() adds it at runtime; relying
    # on try/except around ALTER TABLE is unsafe on PostgreSQL, where a failed
    # statement aborts the whole migration transaction and breaks the alembic
    # version update.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('colab')]
    if 'new_organization_image_url' not in columns:
        op.add_column('colab', sa.Column('new_organization_image_url', sa.String))


def downgrade():
    # Remove the new_organization_image_url column
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns('colab')]
    if 'new_organization_image_url' in columns:
        op.drop_column('colab', 'new_organization_image_url')
