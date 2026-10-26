"""Sysadmin-only account editing, with UUID identity and durable delivery."""
import hashlib
import json
from datetime import datetime
from urllib.error import HTTPError
from flask import Blueprint, current_app, request
from sqlalchemy import func, or_
import ckan.model as model
import ckan.plugins.toolkit as tk
from ckan.logic import schema as schemas
from ckanext.colab.models.account_update import AccountUpdate
from ckanext.colab.models.cool_plugin_table import AuditLog, CoolPluginTable, OrganizationRequestTable

blueprint = Blueprint('colab_accounts', __name__)


@blueprint.before_request
def protect_request():
    if request.method == 'POST':
        csrf = current_app.extensions.get('csrf')
        if csrf is None:
            tk.abort(503, tk._('Form protection is unavailable.'))
        csrf.protect()


@blueprint.after_request
def private_response(response):
    response.headers['Cache-Control'] = 'private, no-store'
    return response


def auth(context, data_dict):
    user = context.get('auth_user_obj') or model.User.get(context.get('user'))
    return {'success': bool(user and user.sysadmin and user.state == 'active')}


def require_admin(context):
    tk.check_access('sysadmin', context, {})


def context():
    ctx = {'model': model, 'session': model.Session, 'user': tk.g.user, 'auth_user_obj': tk.g.userobj}
    try:
        require_admin(ctx)
    except tk.NotAuthorized:
        tk.abort(403, tk._('Need to be system administrator'))
    return ctx


def profile(user):
    return {'name': user.name, 'email': user.email or '', 'fullname': user.fullname or ''}


def version(user):
    return hashlib.sha256(json.dumps({'id': user.id, 'state': user.state,
                                     **profile(user)}, sort_keys=True).encode()).hexdigest()


def account(ident, lock=False):
    query = model.Session.query(model.User).filter(model.User.id == str(ident))
    user = (query.populate_existing().with_for_update() if lock else query).first()
    if not user:
        raise tk.ObjectNotFound('User not found')
    return user


def event_data(row):
    return {'id': row.id, 'ckan_id': row.ckan_id, 'status': row.status,
            'before': json.loads(row.before_json), 'after': json.loads(row.after_json),
            'toolbox_expected': row.toolbox_expected, 'error': row.error}


def _event(ident):
    try:
        ident = int(ident)
    except (TypeError, ValueError):
        raise tk.ObjectNotFound('Update not found')
    row = model.Session.query(AccountUpdate).filter(AccountUpdate.id == ident).first()
    if row is None:
        raise tk.ObjectNotFound('Update not found')
    return row


@tk.side_effect_free
def colab_account_updates_pending(context, data_dict):
    require_admin(context)
    return [{'id': r.id, 'ckan_id': r.ckan_id} for r in model.Session.query(AccountUpdate).filter(
        AccountUpdate.status == 'pending').order_by(AccountUpdate.id).limit(50)]


@tk.side_effect_free
def colab_account_update_show(context, data_dict):
    require_admin(context)
    return event_data(_event(data_dict.get('id')))


def colab_account_update_ack(context, data_dict):
    require_admin(context)
    row = _event(data_dict.get('id'))
    if row.ckan_id != data_dict.get('ckan_id'):
        raise tk.ValidationError({'id': ['Update identity mismatch']})
    status = data_dict.get('status')
    if status not in ('synced', 'failed'):
        raise tk.ValidationError({'status': ['Invalid delivery status']})
    if row.status != 'synced':
        row.status = status
        allowed = {'identity_conflict', 'username_taken', 'email_taken',
                   'identity_changed', 'toolbox_profile_changed', 'sync_conflict'}
        error = data_dict.get('error')
        row.error = (error if error in allowed else 'sync_conflict') if status == 'failed' else None
        row.synced_at = datetime.utcnow() if status == 'synced' else None
        model.Session.add(row)
        model.Session.commit()
    return {'id': row.id, 'ckan_id': row.ckan_id, 'status': row.status}


def toolbox_request(path, body):
    from ckanext.csunesco.logic.snapshots import app_request
    return app_request(path, body)


def preflight(ident, before, after):
    try:
        result = toolbox_request('/internal/portal-users/' + ident + '/preview', {'before': before, 'after': after})
    except HTTPError as exc:
        if exc.code == 409:
            try:
                code = json.loads(exc.read(8192)).get('detail', {}).get('code')
            except (ValueError, AttributeError):
                code = None
            field = 'name' if code == 'username_taken' else 'email' if code == 'email_taken' else 'general'
            raise tk.ValidationError({field: [tk._('This change conflicts with an existing Toolbox account.')]})
        raise tk.ValidationError({'general': [tk._('Toolbox is unavailable. No changes were saved.')]})
    except Exception:
        raise tk.ValidationError({'general': [tk._('Toolbox is unavailable. No changes were saved.')]})
    if not isinstance(result, dict) or result.get('ckan_id') != ident or not result.get('expected'):
        raise tk.ValidationError({'general': [tk._('Toolbox verification failed. No changes were saved.')]})
    return result['expected']


def admin_name_validator(key, data, errors, context):
    """Keep CKAN format checks, replacing only the active-account rename ban."""
    require_admin(context)
    other = model.Session.query(model.User).filter(
        func.lower(model.User.name) == data[key].lower(), model.User.id != context['user_obj'].id).first()
    if other:
        errors[key].append(tk._('That login name is not available.'))


def save_profile(ctx, ident, values, expected_version):
    require_admin(ctx)
    user = account(ident, lock=True)
    if user.state != 'active':
        raise tk.ValidationError({'general': [tk._('Only active accounts can be edited.')]})
    if version(user) != expected_version:
        raise tk.ValidationError({'general': [tk._('This account changed. Reload it before saving.')]})
    if model.Session.query(AccountUpdate).filter(
            AccountUpdate.ckan_id == user.id, AccountUpdate.status != 'synced').first():
        raise tk.ValidationError({'general': [tk._('Finish the pending Toolbox synchronization before editing again.')]})
    before = profile(user)
    after = {k: (values.get(k) or '').strip() for k in ('name', 'email', 'fullname')}
    if after == before:
        return None
    if len(after['fullname']) > 256 or len(after['email']) > 254:
        raise tk.ValidationError({'general': [tk._('One of the values is too long.')]})
    schema = schemas.default_update_user_schema()
    schema['name'] = [tk.get_validator('not_empty'), tk.get_validator('name_validator'),
                      admin_name_validator, tk.get_validator('unicode_safe')]
    patch_ctx = dict(ctx, defer_commit=True, schema=schema, user_obj=user)
    if after['email'].lower() != before['email'].lower():
        if model.Session.query(model.User).filter(
                func.lower(model.User.email) == after['email'].lower(),
                model.User.id != user.id, model.User.state != 'deleted').first():
            raise tk.ValidationError({'email': [tk._('This email address belongs to another account.')]})
    tk.get_action('user_patch')(patch_ctx, dict(after, id=user.id))
    expected = preflight(user.id, before, after)
    if before['email'] != after['email'] or before['name'] != after['name']:
        user.reset_key = None
    for row in model.Session.query(CoolPluginTable).filter(CoolPluginTable.wins_username == before['name']):
        row.wins_username, row.email, row.fullname = after['name'], after['email'], after['fullname']
    if before['name'] != after['name']:
        for field in (OrganizationRequestTable.requester_username, OrganizationRequestTable.admin_username):
            model.Session.query(OrganizationRequestTable).filter(field == before['name']).update(
                {field: after['name']}, synchronize_session=False)
    row = AccountUpdate()
    row.ckan_id, row.actor_id = user.id, ctx['auth_user_obj'].id
    row.before_json, row.after_json = json.dumps(before), json.dumps(after)
    row.toolbox_expected, row.status = expected, 'pending'
    row.created_at = datetime.utcnow()
    model.Session.add(row)
    model.Session.add(AuditLog(action='account_update', admin_user=ctx['user'], target_user=user.id,
        details=json.dumps({'actor_id': row.actor_id, 'before': before, 'after': after})))
    model.Session.commit()
    return row.id


def deliver(ident, event_id):
    try:
        toolbox_request('/internal/portal-users/' + ident + '/sync', {'event_id': event_id})
    except Exception:
        pass  # The committed event is picked up by the Toolbox worker.
    model.Session.expire_all()
    return _event(event_id)


@blueprint.route('/colab/admin/users')
def users():
    context()
    q = request.args.get('q', '').strip()[:200]
    try:
        page = max(1, min(100000, int(request.args.get('page', '1'))))
    except ValueError:
        page = 1
    query = model.Session.query(model.User)
    if q:
        term = '%' + q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
        query = query.filter(or_(*(field.ilike(term, escape='\\') for field in (
            model.User.name, model.User.fullname, model.User.email))))
    count = query.count()
    rows = query.order_by(model.User.name).offset((page - 1) * 25).limit(25).all()
    return tk.render('account_users.html', extra_vars={'users': rows, 'q': q, 'page': page, 'count': count})


@blueprint.route('/colab/admin/users/<uuid:ident>/edit', methods=['GET', 'POST'])
def edit(ident):
    ctx = context()
    ident = str(ident)
    try:
        user = account(ident)
    except tk.ObjectNotFound:
        tk.abort(404, tk._('User not found'))
    errors, values = {}, profile(user)
    if request.method == 'POST':
        values = {k: request.form.get(k, '') for k in ('name', 'email', 'fullname')}
        try:
            event_id = save_profile(ctx, ident, values, request.form.get('version', ''))
        except tk.ValidationError as exc:
            model.Session.rollback()
            errors = exc.error_dict
        except Exception:
            model.Session.rollback()
            raise
        else:
            if event_id:
                result = deliver(ident, event_id)
                if result.status == 'synced':
                    tk.h.flash_success(tk._('Account updated and synchronized with Toolbox.'))
                else:
                    tk.h.flash_notice(tk._('Account saved in IHP-WINS. Toolbox synchronization is pending.'))
                if ctx['auth_user_obj'].id == ident and ctx['user'] != values['name'].strip():
                    return tk.redirect_to('user.logout')
            else:
                tk.h.flash_notice(tk._('No changes to save.'))
            return tk.redirect_to('colab_accounts.edit', ident=ident)
    events = model.Session.query(AccountUpdate).filter(AccountUpdate.ckan_id == ident).order_by(
        AccountUpdate.id.desc()).limit(10).all()
    return tk.render('account_edit.html', extra_vars={
        'account': user, 'values': values, 'errors': errors, 'version': version(user),
        'events': events, 'current': profile(user)})


@blueprint.route('/colab/admin/users/<uuid:ident>/retry', methods=['POST'])
def retry(ident):
    ctx = context()
    ident = str(ident)
    user = account(ident, lock=True)
    row = model.Session.query(AccountUpdate).filter(
        AccountUpdate.ckan_id == ident, AccountUpdate.status != 'synced').order_by(AccountUpdate.id).first()
    if row:
        row.status, row.error = 'pending', None
        model.Session.add(row)
        model.Session.add(AuditLog(action='account_sync_retry', admin_user=ctx['user'],
                                  target_user=user.id, details=json.dumps({'event_id': row.id})))
        model.Session.commit()
        deliver(ident, row.id)
    return tk.redirect_to('colab_accounts.edit', ident=ident)
