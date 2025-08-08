"""add citizens4water field

Revision ID: d7e8f9a1b2c3
Revises: f3d4e5a6b7c8
Create Date: 2025-08-08 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7e8f9a1b2c3'
down_revision = 'f3d4e5a6b7c8'
branch_labels = None
depends_on = None


def upgrade():
    # Agregar la nueva columna citizens4water a la tabla colab
    op.add_column('colab', sa.Column('citizens4water', sa.String))


def downgrade():
    # Eliminar la columna en caso de rollback
    op.drop_column('colab', 'citizens4water')
