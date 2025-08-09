"""add citizens4water field direct

Revision ID: e8f9a0b1c2d4
Revises: bc416bb48b61
Create Date: 2025-08-09 16:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e8f9a0b1c2d4'
down_revision = 'bc416bb48b61'
branch_labels = None
depends_on = None


def upgrade():
    # First ensure the organization requests table exists
    try:
        # Check if table exists by trying to create it
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
    except Exception:
        # Table already exists, continue
        pass

    # Now add the citizens4water column to the colab table
    try:
        op.add_column('colab', sa.Column('citizens4water', sa.String))
    except Exception:
        # Column already exists, continue
        pass


def downgrade():
    # Remove the citizens4water column
    try:
        op.drop_column('colab', 'citizens4water')
    except Exception:
        # Column doesn't exist, continue
        pass
    
    # Optionally drop the organization requests table
    try:
        op.drop_table('colab_organization_requests')
    except Exception:
        # Table doesn't exist, continue
        pass
