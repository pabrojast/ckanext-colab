"""replace age with date_of_birth

Revision ID: a0b1c2d3e4f5
Revises: e8f9a0b1c2d4
Create Date: 2025-08-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a0b1c2d3e4f5'
down_revision = 'e8f9a0b1c2d4'
branch_labels = None
depends_on = None


def upgrade():
    # Add new date_of_birth column (nullable for safe migration)
    try:
        op.add_column('colab', sa.Column('date_of_birth', sa.Date))
    except Exception:
        # Column might already exist
        pass

    # Optional: try to backfill date_of_birth approximately from existing age
    # This uses a database-specific expression; skip if it fails
    try:
        op.execute(
            """
            UPDATE colab
            SET date_of_birth = (
                CURRENT_DATE - (INTERVAL '1 year' * age)
            )
            WHERE date_of_birth IS NULL AND age IS NOT NULL
            """
        )
    except Exception:
        # Ignore if DB doesn't support the expression
        pass

    # Drop old age column
    try:
        op.drop_column('colab', 'age')
    except Exception:
        # Column might have been removed already
        pass


def downgrade():
    # Recreate age as Integer (no backfill from date_of_birth)
    try:
        op.add_column('colab', sa.Column('age', sa.Integer))
    except Exception:
        pass

    # Remove date_of_birth
    try:
        op.drop_column('colab', 'date_of_birth')
    except Exception:
        pass


