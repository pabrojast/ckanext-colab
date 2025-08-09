"""add organization requests table

Revision ID: f3d4e5a6b7c8
Revises: bc416bb48b61
Create Date: 2025-07-03 20:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3d4e5a6b7c8'
down_revision = 'bc416bb48b61'
branch_labels = None
depends_on = None


def upgrade():
    # Create the organization requests table only if it doesn't exist
    try:
        op.create_table(
            'colab_organization_requests',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('requester_username', sa.String, nullable=False),
            sa.Column('organization_name', sa.String, nullable=False),
            sa.Column('organization_description', sa.String),
            sa.Column('organization_image_url', sa.String),
            sa.Column('admin_username', sa.String, nullable=False),
            sa.Column('organization_type', sa.String),
            sa.Column('status', sa.String, default='pending'),
            sa.Column('created_date', sa.DateTime),
            sa.Column('approved_by', sa.String),
            sa.Column('approved_date', sa.DateTime),
            sa.Column('rejected_by', sa.String),
            sa.Column('rejected_date', sa.DateTime),
            sa.Column('rejection_reason', sa.String)
        )
    except Exception as e:
        # If table already exists, skip creation
        if "already exists" in str(e) or "duplicate" in str(e).lower():
            pass
        else:
            raise


def downgrade():
    # Drop the organization requests table only if it exists
    try:
        op.drop_table('colab_organization_requests')
    except Exception as e:
        # If table doesn't exist, skip deletion
        if "does not exist" in str(e) or "no such table" in str(e).lower():
            pass
        else:
            raise