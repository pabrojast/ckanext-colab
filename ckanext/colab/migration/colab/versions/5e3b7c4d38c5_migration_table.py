"""migration table

Revision ID: 5e3b7c4d38c5
Revises: 788c822b8f6b
Create Date: 2024-03-20 01:34:05.358224

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5e3b7c4d38c5'
down_revision = '788c822b8f6b'
branch_labels = None
depends_on = None


def upgrade():
        op.add_column('colab', sa.Column('age', sa.Integer))
        op.add_column('colab', sa.Column('organizationType', sa.String))
        op.add_column('colab', sa.Column('nationality', sa.String))
        op.add_column('colab', sa.Column('gender', sa.String))


def downgrade():
        op.drop_column('colab', 'new_group_description')
        op.drop_column('colab', 'new_group_name')
        op.drop_column('colab', 'group')
        op.drop_column('colab', 'estimated_space')
