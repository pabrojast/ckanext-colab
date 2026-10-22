"""Legacy and current Colab approval routes use canonical, confirmed membership."""
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
import ckan.model as model
import ckan.plugins.toolkit as tk
from ckanext.colab.membership import ensure_organization_member


@pytest.fixture
def membership_case(monkeypatch):
    engine = sa.create_engine('sqlite://')
    from ckan.model.group import group_table, member_table
    model.meta.metadata.create_all(bind=engine, tables=[group_table, member_table])
    model.Session.remove(); model.Session.configure(bind=engine)
    org = model.Group(name='canonical-name', title='A different display title', type='organization', is_organization=True)
    org.state = 'active'
    model.Session.add(org); model.Session.commit()
    user = SimpleNamespace(id='citizen', name='citizen', state='active')
    monkeypatch.setattr(model.User, 'get', staticmethod(lambda key: user))
    monkeypatch.setattr(tk, 'check_access', lambda *a: True)
    monkeypatch.setattr(model.Member, 'related_packages', lambda self: [])
    calls = []
    def action(name):
        assert name == 'organization_member_create'
        def create(context, data):
            assert context['defer_commit'] is True and data['id'] == org.id
            calls.append(data)
            current = model.Session.query(model.Member).filter_by(group_id=org.id, table_id=user.id).first()
            if current: current.capacity = data['role']
            else: model.Session.add(model.Member(group=org, table_name='user', table_id=user.id, capacity=data['role'], state='active'))
        return create
    monkeypatch.setattr(tk, 'get_action', action)
    yield org, user, calls
    model.Session.remove(); engine.dispose()


def test_title_resolves_to_canonical_organization_and_retry_preserves_admin(membership_case):
    org, user, calls = membership_case
    request = {'id': org.title, 'username': user.name, 'role': 'admin'}
    result = ensure_organization_member({'user': 'reviewer'}, request)
    assert result['id'] == org.id and result['role'] == 'admin'
    again = ensure_organization_member({'user': 'reviewer'}, dict(request, role='member'))
    assert again['role'] == 'admin' and len(calls) == 1


def test_false_success_is_rejected(membership_case, monkeypatch):
    org, user, _ = membership_case
    monkeypatch.setattr(tk, 'get_action', lambda name: lambda *args: {})
    with pytest.raises(tk.ValidationError, match='not confirmed'):
        ensure_organization_member({'user': 'reviewer'}, {'id': org.id, 'username': user.name, 'role': 'member'})


def test_permissions_are_checked_even_if_membership_already_exists(membership_case, monkeypatch):
    org, user, _ = membership_case
    def deny(*args): raise tk.NotAuthorized('Denied')
    monkeypatch.setattr(tk, 'check_access', deny)
    with pytest.raises(tk.NotAuthorized):
        ensure_organization_member({'user': 'outsider'}, {'id': org.id, 'username': user.name, 'role': 'member'})
