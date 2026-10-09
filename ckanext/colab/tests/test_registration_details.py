"""An existing identity may reuse only its own Colab application data."""
import datetime
from types import SimpleNamespace
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from ckanext.colab.lib import registration_details as details
from ckanext.colab.models.cool_plugin_table import CoolPluginTable, cool_plugin_table


@pytest.fixture
def session(monkeypatch):
    engine = sa.create_engine('sqlite://')
    cool_plugin_table.create(engine)
    session = sessionmaker(bind=engine)()
    monkeypatch.setattr(details.model, 'Session', session)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def application(session, **kwargs):
    data = dict(wins_username='citizen', email='Citizen@Example.org', fullname='Colab Name',
                date_of_birth=datetime.date(1990, 5, 18), nationality='Chile', gender='woman',
                user_role='admin', approved='approved by reviewer', created_date=datetime.datetime(2026, 1, 1))
    data.update(kwargs)
    row = CoolPluginTable(**data)
    session.add(row)
    session.commit()
    return row


def test_own_fields_only_and_read_does_not_change_request(session):
    row = application(session)
    user = SimpleNamespace(name='citizen', email=' citizen@example.org ')
    result = details.registration_details(user)
    assert result == dict(fullname='Colab Name', date_of_birth=datetime.date(1990, 5, 18), nationality='Chile', gender='woman')
    assert row.user_role == 'admin' and row.approved == 'approved by reviewer'
    assert not session.dirty and not session.new


@pytest.mark.parametrize('name,email', [('different', 'citizen@example.org'), ('citizen', 'different@example.org'), ('citizen', None), ('', 'citizen@example.org')])
def test_both_identity_fields_must_match(session, name, email):
    application(session)
    assert details.registration_details(SimpleNamespace(name=name, email=email)) == {}


def test_latest_own_non_deleted_application_wins(session):
    application(session)
    latest = application(session, fullname='Updated name', created_date=datetime.datetime(2026, 2, 1))
    deleted = application(session, fullname='Deleted name', created_date=datetime.datetime(2026, 3, 1))
    deleted.deleted_at = datetime.datetime(2026, 3, 2)
    session.commit()
    user = SimpleNamespace(name='citizen', email='citizen@example.org')
    assert details.registration_details(user)['fullname'] == latest.fullname
    latest.deleted_at = datetime.datetime(2026, 3, 2)
    session.commit()
    assert details.registration_details(user)['fullname'] == 'Colab Name'


def test_uninitialized_colab_database_is_optional(session):
    cool_plugin_table.drop(session.get_bind())
    assert details.registration_details(SimpleNamespace(name='citizen', email='citizen@example.org')) == {}
