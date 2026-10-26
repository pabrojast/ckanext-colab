"""Durable profile edit receipts and Toolbox delivery state."""
from datetime import datetime
from sqlalchemy import Column, Table, types, Index, text
from ckan.model import meta, domain_object
from ckanext.colab.models.cool_plugin_table import metadata

account_update_table = Table(
    'colab_account_updates', metadata,
    Column('id', types.Integer, primary_key=True, autoincrement=True),
    Column('ckan_id', types.String, nullable=False, index=True),
    Column('actor_id', types.String, nullable=False),
    Column('before_json', types.Text, nullable=False),
    Column('after_json', types.Text, nullable=False),
    Column('toolbox_expected', types.String, nullable=False),
    Column('status', types.String, nullable=False, default='pending'),
    Column('error', types.String),
    Column('created_at', types.DateTime, nullable=False, default=datetime.utcnow),
    Column('synced_at', types.DateTime),
)
Index('ix_colab_account_updates_status_id', account_update_table.c.status, account_update_table.c.id)


class AccountUpdate(domain_object.DomainObject):
    pass


meta.mapper(AccountUpdate, account_update_table)


def ensure_table(engine):
    """Additive startup compatibility, serialized across CKAN workers.

The Alembic migration remains the canonical installation path. Older deployments
already bootstrap Colab schema on import; retain that contract for this new table.
"""
    with engine.begin() as connection:
        if engine.dialect.name == 'postgresql':
            connection.execute(text('SELECT pg_advisory_xact_lock(20261026, 1)'))
        account_update_table.create(connection, checkfirst=True)
