"""merge heads

Revision ID: ztanx25m7u8r
Revises: bc416bb48b61, f3d4e5a6b7c8
Create Date: 2025-08-17 17:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ztanx25m7u8r'
down_revision = ('bc416bb48b61', 'f3d4e5a6b7c8')
branch_labels = None
depends_on = None


def upgrade():
    # Esta migración solo fusiona las dos ramas, no hace cambios en la base de datos
    pass


def downgrade():
    # No hay cambios para revertir
    pass
