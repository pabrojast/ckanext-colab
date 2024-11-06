"""member as option added

Revision ID: 0444ae481c98
Revises: 5b6e390c823c
Create Date: 2024-11-06 17:26:37.113826

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0444ae481c98'
down_revision = '5b6e390c823c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('colab', sa.Column('user_role', sa.String))

def downgrade():
    op.drop_column('colab', 'user_role')
