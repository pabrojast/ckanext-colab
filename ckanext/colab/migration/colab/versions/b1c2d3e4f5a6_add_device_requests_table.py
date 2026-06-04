"""add device_requests table

Revision ID: b1c2d3e4f5a6
Revises: fa1b2c3d4e5f
Create Date: 2026-03-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5a6'
down_revision = 'fa1b2c3d4e5f'
branch_labels = None
depends_on = None


def upgrade():
    # Idempotent and transaction-safe: check existence with the inspector
    # before issuing DDL. Relying on try/except around CREATE statements is
    # unsafe on PostgreSQL because a failed statement aborts the whole
    # migration transaction, which then breaks the alembic version update.
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if 'device_requests' not in inspector.get_table_names():
        op.create_table(
            'device_requests',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('organization_id', sa.String),
            sa.Column('created_by_user_id', sa.String, nullable=False),
            sa.Column('reviewed_by_user_id', sa.String),
            sa.Column('status', sa.String, server_default='DRAFT'),
            # Device info
            sa.Column('device_name', sa.String),
            sa.Column('device_label', sa.String),
            sa.Column('device_profile_name', sa.String),
            sa.Column('serial_number', sa.String),
            sa.Column('site_code', sa.String),
            # Installation info
            sa.Column('installer_name', sa.String),
            sa.Column('install_date', sa.Date),
            sa.Column('owner_name', sa.String),
            sa.Column('firmware_version', sa.String),
            # Location
            sa.Column('latitude', sa.Float),
            sa.Column('longitude', sa.Float),
            sa.Column('address', sa.Text),
            sa.Column('technical_notes', sa.Text),
            # Metadata
            sa.Column('photos_urls_json', sa.Text),
            sa.Column('survey_completed', sa.Boolean, server_default='false'),
            sa.Column('metadata_complete', sa.Boolean, server_default='false'),
            sa.Column('metadata_missing_fields_json', sa.Text),
            # Timestamps
            sa.Column('submitted_at', sa.DateTime),
            sa.Column('reviewed_at', sa.DateTime),
            sa.Column('approved_at', sa.DateTime),
            sa.Column('rejected_at', sa.DateTime),
            sa.Column('rejection_reason', sa.Text),
            # Sync
            sa.Column('sync_status', sa.String),
            sa.Column('sync_error_message', sa.Text),
            # ThingsBoard references
            sa.Column('tb_device_id', sa.String),
            sa.Column('tb_customer_id', sa.String),
            sa.Column('tb_access_token', sa.String),
            # Audit
            sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
            # Constraints
            sa.UniqueConstraint('serial_number', name='uq_device_requests_serial_number'),
        )

    # Re-inspect so newly created table's indexes are visible.
    existing_indexes = {ix['name'] for ix in sa.inspect(bind).get_indexes('device_requests')}
    if 'ix_device_requests_status' not in existing_indexes:
        op.create_index('ix_device_requests_status', 'device_requests', ['status'])
    if 'ix_device_requests_created_by' not in existing_indexes:
        op.create_index('ix_device_requests_created_by', 'device_requests', ['created_by_user_id'])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'device_requests' in inspector.get_table_names():
        existing_indexes = {ix['name'] for ix in inspector.get_indexes('device_requests')}
        if 'ix_device_requests_created_by' in existing_indexes:
            op.drop_index('ix_device_requests_created_by', table_name='device_requests')
        if 'ix_device_requests_status' in existing_indexes:
            op.drop_index('ix_device_requests_status', table_name='device_requests')
        op.drop_table('device_requests')
