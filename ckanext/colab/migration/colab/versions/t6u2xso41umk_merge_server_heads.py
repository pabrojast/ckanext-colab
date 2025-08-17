"""merge server heads - resolve multiple heads issue for server deployment

Revision ID: t6u2xso41umk
Revises: e9f0a1b2c3d4, a0b1c2d3e4f5
Create Date: 2025-08-17 19:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 't6u2xso41umk'
down_revision = ('e9f0a1b2c3d4', 'a0b1c2d3e4f5')
branch_labels = None
depends_on = None


def upgrade():
    # Esta migración fusiona las ramas divergentes del servidor
    # No realiza cambios en la base de datos, solo resuelve el conflicto de historial
    pass


def downgrade():
    # No hay cambios para revertir en esta migración de merge
    pass
