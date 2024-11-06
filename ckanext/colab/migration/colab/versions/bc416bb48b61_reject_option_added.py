"""reject option added

Revision ID: bc416bb48b61
Revises: 0444ae481c98
Create Date: 2024-11-06 18:23:07.152829

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bc416bb48b61'
down_revision = '0444ae481c98'
branch_labels = None
depends_on = None


def upgrade():
    # Agregar las nuevas columnas a la tabla colab
    op.add_column('colab', sa.Column('rejected', sa.String))
    op.add_column('colab', sa.Column('rejection_reason', sa.String))


def downgrade():
    # Eliminar las columnas en caso de rollback
    op.drop_column('colab', 'rejected')
    op.drop_column('colab', 'rejection_reason')