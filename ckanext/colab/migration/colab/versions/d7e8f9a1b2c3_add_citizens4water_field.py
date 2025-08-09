"""add citizens4water field

Revision ID: d7e8f9a1b2c3
Revises: f3d4e5a6b7c8
Create Date: 2025-08-09 16:20:00.000000

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
    try:
        op.add_column('colab', sa.Column('citizens4water', sa.String))
    except Exception as e:
        # Si la columna ya existe, no hacer nada
        if "already exists" in str(e) or "duplicate column" in str(e).lower():
            pass
        else:
            raise


def downgrade():
    # Eliminar la columna en caso de rollback
    try:
        op.drop_column('colab', 'citizens4water')
    except Exception as e:
        # Si la columna no existe, no hacer nada
        if "does not exist" in str(e) or "no such column" in str(e).lower():
            pass
        else:
            raise
