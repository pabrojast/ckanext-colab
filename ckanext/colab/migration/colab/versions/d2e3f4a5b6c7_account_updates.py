"""Durable administrator account edits and Toolbox delivery receipts."""
from alembic import op
import sqlalchemy as sa

revision = 'd2e3f4a5b6c7'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    if 'colab_account_updates' in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table('colab_account_updates',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('ckan_id', sa.String, nullable=False),
        sa.Column('actor_id', sa.String, nullable=False),
        sa.Column('before_json', sa.Text, nullable=False),
        sa.Column('after_json', sa.Text, nullable=False),
        sa.Column('toolbox_expected', sa.String, nullable=False),
        sa.Column('status', sa.String, nullable=False),
        sa.Column('error', sa.String),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('synced_at', sa.DateTime))
    op.create_index('ix_colab_account_updates_ckan_id', 'colab_account_updates', ['ckan_id'])
    op.create_index('ix_colab_account_updates_status_id', 'colab_account_updates', ['status', 'id'])


def downgrade():
    pass  # Preserve audit/delivery receipts on a code rollback.
