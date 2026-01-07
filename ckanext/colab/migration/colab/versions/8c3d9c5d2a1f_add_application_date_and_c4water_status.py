"""add application date and c4water status

Revision ID: 8c3d9c5d2a1f
Revises: yq7tn3l3cgof
Create Date: 2025-12-19 13:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8c3d9c5d2a1f'
down_revision = 'yq7tn3l3cgof'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('colab', sa.Column('created_date', sa.DateTime(), nullable=True))
    op.add_column('colab', sa.Column('c4water_status', sa.String(), nullable=True))

    # Backfill existing rows so the new fields are populated
    op.execute("UPDATE colab SET created_date = NOW() WHERE created_date IS NULL")
    op.execute("UPDATE colab SET c4water_status = 'auto_approved' WHERE c4water_status IS NULL")


def downgrade():
    op.drop_column('colab', 'c4water_status')
    op.drop_column('colab', 'created_date')
