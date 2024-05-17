"""MIGRATION MESSAGE

Revision ID: 788c822b8f6b
Revises: 
Create Date: 2024-01-31 23:29:01.583516

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '788c822b8f6b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'colab',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('fullname', sa.String),
        sa.Column('wins_username', sa.String),
        sa.Column('email', sa.String),
        sa.Column('title_within_organization', sa.String),
		sa.Column('approved', sa.String),
        sa.Column('approvedgroup', sa.String),
        sa.Column('estimated_space', sa.Integer),
        sa.Column('organization_name', sa.String), 
        sa.Column('new_organization_name', sa.Integer),
        sa.Column('new_organization_description', sa.String), 
		sa.Column('group', sa.Integer),
		sa.Column('new_group_name', sa.String),
		sa.Column('new_group_description', sa.String),
        # Add more columns as needed
    )

def downgrade():
    op.drop_table('colab')
