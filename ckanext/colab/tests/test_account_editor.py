"""Database-backed profile edits; run against an isolated CKAN schema.

COLAB_ACCOUNT_TEST_DB must name a disposable database, never a live database.
Ordinary CI still runs the authorization/CSRF tests without a database.
"""
import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from flask import Flask, g
from werkzeug.exceptions import BadRequest

import ckan.model as model
import ckan.plugins.toolkit as tk
from ckanext.colab import account_editor as editor
from ckanext.colab.models.account_update import AccountUpdate, account_update_table
from ckanext.colab.models.cool_plugin_table import AuditLog, CoolPluginTable, OrganizationRequestTable


def test_browser_authorization_csrf_and_no_cache(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'isolated-test-only'
    app.register_blueprint(editor.blueprint)
    @app.before_request
    def actor():
        g.user = 'ordinary'; g.userobj = SimpleNamespace(sysadmin=False)
    def denied(*args, **kwargs):
        raise tk.NotAuthorized('denied')
    monkeypatch.setattr(tk, 'check_access', denied)
    monkeypatch.setattr(tk, '_', lambda value: value)
    client = app.test_client()
    response = client.get('/colab/admin/users')
    assert response.status_code == 403
    assert response.headers['Cache-Control'] == 'private, no-store'
    def csrf():
        raise BadRequest('Missing CSRF token')
    app.extensions['csrf'] = SimpleNamespace(protect=csrf)
    assert client.post('/colab/admin/users/'+str(uuid4())+'/edit').status_code == 400
    assert client.get('/colab/admin/users/'+str(uuid4())+'/retry').status_code == 405


@pytest.fixture
def database(monkeypatch):
    url = os.environ.get('COLAB_ACCOUNT_TEST_DB')
    if not url:
        pytest.skip('Requires an isolated CKAN database in COLAB_ACCOUNT_TEST_DB')
    from sqlalchemy import create_engine
    from ckan.cli import load_config
    from ckan.common import config
    config.update(load_config('/app/production.ini'))
    model.init_model(create_engine(url))
    account_update_table.create(model.meta.engine, checkfirst=True)
    prefix = 'editor-test-'+uuid4().hex[:10]
    actor = model.User(name=prefix+'-admin', email=prefix+'-admin@example.test', sysadmin=True)
    user = model.User(name=prefix, email=prefix+'@example.test', fullname='Original', password='RetainedPassword123')
    model.Session.add_all([actor, user]); model.Session.commit()
    ctx = {'model':model, 'session':model.Session, 'user':actor.name, 'auth_user_obj':actor}
    monkeypatch.setattr(tk, '_', lambda value: value)
    monkeypatch.setattr(editor, 'preflight', lambda ident, before, after: 'expected-fingerprint')
    yield ctx, user, prefix
    model.Session.rollback()
    ids = [x.id for x in model.Session.query(model.User).filter(model.User.name.like(prefix+'%'))]
    model.Session.query(AccountUpdate).filter(AccountUpdate.ckan_id.in_(ids)).delete(synchronize_session=False)
    model.Session.query(AuditLog).filter(AuditLog.target_user.in_(ids)).delete(synchronize_session=False)
    model.Session.query(CoolPluginTable).filter(CoolPluginTable.wins_username.like(prefix+'%')).delete(synchronize_session=False)
    model.Session.query(OrganizationRequestTable).filter(OrganizationRequestTable.requester_username.like(prefix+'%')).delete(synchronize_session=False)
    model.Session.query(model.User).filter(model.User.id.in_(ids)).delete(synchronize_session=False)
    model.Session.commit(); model.Session.remove()


def test_rename_preserves_uuid_password_and_updates_operational_references(database):
    ctx, user, prefix = database
    before, ident, password = editor.profile(user), user.id, user._password
    model.Session.add(CoolPluginTable(wins_username=user.name, email=user.email, fullname=user.fullname))
    model.Session.add(OrganizationRequestTable(requester_username=user.name, admin_username=user.name,
                                               organization_name='test', status='pending'))
    model.Session.commit()
    after = dict(before, name=prefix+'-renamed', email=prefix+'-new@example.test', fullname='Correct name')
    event_id = editor.save_profile(ctx, ident, after, editor.version(user))
    model.Session.expire_all()
    user = editor.account(ident)
    assert user.name == after['name'] and user._password == password and user.id == ident
    assert model.Session.query(CoolPluginTable).filter_by(wins_username=after['name']).one().email == after['email']
    assert model.Session.query(OrganizationRequestTable).filter_by(requester_username=after['name']).one().admin_username == after['name']
    event = editor.colab_account_update_show(ctx, {'id':event_id})
    assert event['before'] == before and event['after'] == after and event['status'] == 'pending'
    assert model.Session.query(AuditLog).filter_by(target_user=ident, action='account_update').count() == 1
    # The ordinary API still forbids renaming active accounts.
    with pytest.raises(tk.ValidationError):
        tk.get_action('user_patch')(ctx, {'id':ident, 'name':prefix+'-ordinary'})


@pytest.mark.parametrize('case', ['stale', 'duplicate_name', 'duplicate_email', 'invalid_name', 'invalid_email', 'offline'])
def test_rejected_changes_leave_account_unchanged(database, monkeypatch, case):
    ctx, user, prefix = database
    before = editor.profile(user); ident = user.id; expected = editor.version(user)
    values = dict(before, fullname='Changed')
    other = model.User(name=prefix+'-other', email=prefix+'-other@example.test')
    model.Session.add(other); model.Session.commit()
    if case == 'stale': expected = 'stale'
    if case == 'duplicate_name': values['name'] = other.name
    if case == 'duplicate_email': values['email'] = other.email.upper()
    if case == 'invalid_name': values['name'] = 'invalid name'
    if case == 'invalid_email': values['email'] = 'not-an-email'
    if case == 'offline':
        def unavailable(*args): raise tk.ValidationError({'general':['Toolbox unavailable']})
        monkeypatch.setattr(editor, 'preflight', unavailable)
    with pytest.raises(tk.ValidationError):
        editor.save_profile(ctx, ident, values, expected)
    model.Session.rollback()
    assert editor.profile(editor.account(ident)) == before
    assert model.Session.query(AccountUpdate).filter_by(ckan_id=ident).count() == 0


def test_pending_edit_blocks_next_edit_ack_is_idempotent(database):
    ctx, user, prefix = database
    first = editor.save_profile(ctx, user.id, dict(editor.profile(user), fullname='First'), editor.version(user))
    with pytest.raises(tk.ValidationError):
        editor.save_profile(ctx, user.id, dict(editor.profile(user), fullname='Second'), editor.version(user))
    model.Session.rollback()
    with pytest.raises(tk.ValidationError):
        editor.colab_account_update_ack(ctx, {'id':first, 'ckan_id':str(uuid4()), 'status':'synced'})
    for _ in range(2):
        result = editor.colab_account_update_ack(ctx, {'id':first, 'ckan_id':user.id, 'status':'synced'})
        assert result['status'] == 'synced'
    assert editor.save_profile(ctx, user.id, editor.profile(user), editor.version(user)) is None
