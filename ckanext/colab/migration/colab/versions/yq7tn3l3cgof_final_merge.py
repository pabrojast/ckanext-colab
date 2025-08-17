"""final merge - consolidate all migration branches

Revision ID: yq7tn3l3cgof
Revises: ztanx25m7u8r, t6u2xso41umk
Create Date: 2025-08-17 19:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'yq7tn3l3cgof'
down_revision = ('ztanx25m7u8r', 't6u2xso41umk')
branch_labels = None
depends_on = None


def upgrade():
    # Esta migración consolida todas las ramas de migración
    # Funciona tanto para el entorno local como para el servidor
    # No realiza cambios en la base de datos, solo unifica el historial
    pass


def downgrade():
    # No hay cambios para revertir en esta migración de consolidación
    pass
