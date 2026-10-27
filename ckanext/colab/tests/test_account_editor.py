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
    reset_path = '/colab/admin/users/'+str(uuid4())+'/reset-link'
    assert client.get(reset_path).status_code == 403
    response = client.post(reset_path)
    assert response.status_code == 400
    assert response.headers['Cache-Control'] == 'private, no-store'
    assert response.headers['Referrer-Policy'] == 'no-referrer'


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


def test_reset_link_targets_uuid_preserves_account_and_audits_without_secrets(database, monkeypatch):
    from ckan.lib import mailer
    from urllib.parse import urlencode, urlparse, parse_qs
    import json
    import smtplib
    ctx, user, prefix = database
    before, password = editor.profile(user), user._password
    other = model.User(name=prefix+'-shared-email', email=user.email, state='deleted')
    model.Session.add(other); model.Session.commit()
    def no_mail(*args, **kwargs):
        pytest.fail('Generating a reset link must not send email')
    monkeypatch.setattr(smtplib, 'SMTP', no_mail)
    monkeypatch.setattr(smtplib, 'SMTP_SSL', no_mail)
    monkeypatch.setattr(mailer, 'get_reset_link', lambda u: 'https://portal.example.test/user/reset/'+u.id+'?'+urlencode({'key':u.reset_key}))
    stale = editor.reset_version(user)
    link = editor.create_password_reset_link(ctx, user.id, stale)
    key = parse_qs(urlparse(link).query)['key'][0]
    assert '/'+user.id+'?' in link
    assert mailer.verify_reset_link(user, key)
    assert editor.profile(user) == before and user._password == password and user.state == 'active'
    assert other.reset_key is None
    audit = model.Session.query(AuditLog).filter_by(target_user=user.id, action='account_reset_link').one()
    assert audit.admin_user == ctx['user']
    assert json.loads(audit.details) == {'actor_id':ctx['auth_user_obj'].id}
    assert key not in audit.details and link not in audit.details
    assert model.Session.query(AccountUpdate).filter_by(ckan_id=user.id).count() == 0
    # Replaying a submitted form must not invalidate the displayed link.
    with pytest.raises(tk.ValidationError):
        editor.create_password_reset_link(ctx, user.id, stale)
    model.Session.rollback()
    assert mailer.verify_reset_link(editor.account(user.id), key)
    replacement = editor.create_password_reset_link(ctx, user.id, editor.reset_version(user))
    assert replacement != link and not mailer.verify_reset_link(user, key)


@pytest.mark.parametrize('case', ['inactive', 'stale_profile', 'pending_sync', 'not_admin'])
def test_reset_rejection_keeps_previous_key_and_password(database, monkeypatch, case):
    from ckan.lib import mailer
    ctx, user, prefix = database
    user.reset_key = mailer.make_key()
    model.Session.commit()
    key, password, expected = user.reset_key, user._password, editor.reset_version(user)
    if case == 'inactive':
        user.state = 'deleted'; model.Session.commit()
        expected = editor.reset_version(user)
    elif case == 'stale_profile':
        user.email = prefix+'-changed@example.test'; model.Session.commit()
    elif case == 'pending_sync':
        editor.save_profile(ctx, user.id, dict(editor.profile(user), fullname='Pending'), editor.version(user))
        expected = editor.reset_version(user)
    elif case == 'not_admin':
        ctx = dict(ctx, user=user.name, auth_user_obj=user)
    with pytest.raises(tk.NotAuthorized if case == 'not_admin' else tk.ValidationError):
        editor.create_password_reset_link(ctx, user.id, expected)
    model.Session.rollback()
    assert user.reset_key == key and user._password == password
    assert model.Session.query(AuditLog).filter_by(target_user=user.id, action='account_reset_link').count() == 0


def test_reset_audit_failure_rolls_back_key(database, monkeypatch):
    from ckan.lib import mailer
    ctx, user, prefix = database
    key = user.reset_key
    monkeypatch.setattr(mailer, 'get_reset_link', lambda u: 'https://portal.example.test/recovery')
    original_add = model.Session.add
    def fail_audit(row):
        if isinstance(row, AuditLog):
            raise RuntimeError('Cannot audit')
        original_add(row)
    monkeypatch.setattr(model.Session, 'add', fail_audit)
    with pytest.raises(RuntimeError):
        editor.create_password_reset_link(ctx, user.id, editor.reset_version(user))
    model.Session.rollback()
    assert user.reset_key == key


def test_reset_browser_get_does_not_generate_and_post_requires_csrf(database, monkeypatch):
    from flask_wtf.csrf import CSRFProtect, generate_csrf
    from ckan.lib import mailer
    ctx, user, prefix = database
    app = Flask(__name__)
    app.secret_key = 'isolated-reset-test-only'
    CSRFProtect(app)
    app.register_blueprint(editor.blueprint)
    @app.before_request
    def actor():
        g.user = ctx['user']; g.userobj = ctx['auth_user_obj']
    rendered = []
    def render(template, extra_vars):
        rendered.append(extra_vars)
        return str(generate_csrf())
    monkeypatch.setattr(tk, 'render', render)
    monkeypatch.setattr(mailer, 'get_reset_link', lambda u: 'https://portal.example.test/recovery?key='+u.reset_key)
    client = app.test_client()
    path = '/colab/admin/users/'+user.id+'/reset-link'
    before = user.reset_key
    response = client.get(path)
    assert response.status_code == 200 and user.reset_key == before
    assert rendered[-1]['reset_link'] is None
    csrf_token = response.get_data(as_text=True)
    expected = rendered[-1]['reset_version']
    assert client.post(path, data={'version':expected}).status_code == 400
    response = client.post(path, data={'version':expected,'_csrf_token':csrf_token,'csrf_token':csrf_token})
    assert response.status_code == 200
    key = user.reset_key
    assert key and rendered[-1]['reset_link'].endswith(key)
    assert response.headers['Cache-Control'] == 'private, no-store'
    assert response.headers['Referrer-Policy'] == 'no-referrer'
    assert key not in response.headers.get('Set-Cookie', '')
    assert client.post(path, data={'version':expected,'csrf_token':csrf_token}).status_code == 409
    assert user.reset_key == key
    assert client.get('/colab/admin/users/'+str(uuid4())+'/reset-link').status_code == 404
