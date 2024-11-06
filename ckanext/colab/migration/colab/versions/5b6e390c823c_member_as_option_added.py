"""Add user_role column

Revision ID: 5b6e390c823c
Revises: 5e3b7c4d38c5
Create Date: 2024-11-06 17:11:16.152462

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5b6e390c823c'
down_revision = '5e3b7c4d38c5'
branch_labels = None
depends_on = None


def upgrade():
    #op.add_column('colab', sa.Column('user_role', sa.String))
    pass

def downgrade():
    #op.drop_column('colab', 'user_role')
    pass
