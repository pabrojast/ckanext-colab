"""Colab's Citizen Science inbox; CS actions own records and authorization."""
import logging

from flask import Blueprint, current_app, request
import ckan.model as model
import ckan.plugins.toolkit as tk

log = logging.getLogger(__name__)
blueprint = Blueprint('colab_cs', __name__, url_prefix='/colab/admin/citizen-science')
TABS = ('managers', 'joins', 'projects')
PAGE_SIZE = 20


def context():
    return {'model': model, 'session': model.Session, 'user': tk.g.user,
            'auth_user_obj': getattr(tk.g, 'userobj', None)}


def available():
    try:
        tk.get_action('csunesco_manager_list')
        return True
    except KeyError:
        return False


def can_review():
    if not available() or not getattr(tk.g, 'user', None):
        return False
    from ckanext.csunesco.logic.auth import is_reviewer
    return is_reviewer(context())


def capabilities():
    from ckanext.csunesco.logic import auth
    ctx = context()
    return {'managers': auth._is_sysadmin(ctx),
            'projects': auth._is_sysadmin(ctx) or auth._is_any_initiative_admin(ctx),
            'joins': auth.is_reviewer(ctx)}


def pending_count():
    if not can_review():
        return 0
    from ckanext.csunesco.logic.action.admin import _get_pending_counts
    counts = _get_pending_counts(context())
    total = counts.get('join_requests', 0) + counts.get('project_requests', 0)
    if capabilities()['managers']:
        from ckanext.csunesco import db
        total += model.Session.query(db.CsCitizenScientist).filter(
            db.CsCitizenScientist.profile_type == 'manager',
            db.CsCitizenScientist.email_verified.is_(True),
            db.CsCitizenScientist.manager_decision.is_(None)).count()
    return total


def inbox_url(tab='joins', **kwargs):
    return tk.url_for('colab.show_admin', tab=tab, **kwargs)


def _require_review():
    if not tk.g.user:
        return tk.redirect_to('user.login', came_from=request.full_path)
    if not can_review():
        tk.abort(403, tk._('You are not authorized to view this page'))


def _offset():
    try:
        return max(0, int(request.args.get('offset', 0)))
    except (TypeError, ValueError):
        tk.abort(400, tk._('Invalid pagination'))


def show():
    guard = _require_review()
    if guard is not None:
        return guard
    allowed = capabilities()
    tab = request.args.get('tab', 'joins')
    if tab not in TABS or not allowed[tab]:
        tk.abort(403, tk._('You are not authorized to view this page'))
    offset = _offset()
    data = tk.get_action('csunesco_admin_pending_list')(context(), {'limit': PAGE_SIZE, 'offset': offset})
    values = dict(data, tab=tab, capabilities=allowed, offset=offset, page_size=PAGE_SIZE,
                  can_review_projects=allowed['projects'],
                  status=request.args.get('status', 'pending'), q=request.args.get('q', '').strip()[:100])
    if allowed['managers']:
        try:
            managers = tk.get_action('csunesco_manager_list')(context(), {
                'status': values['status'] if tab == 'managers' else 'pending',
                'q': values['q'] if tab == 'managers' else '',
                'offset': offset if tab == 'managers' else 0, 'limit': PAGE_SIZE})
        except tk.ValidationError:
            tk.abort(400, tk._('Invalid filter'))
        values.update(result=managers, organizations=managers.get('organizations', []))
    else:
        values.update(result={'count': 0, 'results': []}, organizations=[])
    values['counts'] = dict(data['counts'])
    values['counts']['managers'] = values['result']['count']
    values['count'] = values['result']['count'] if tab == 'managers' else data['counts']['join_requests' if tab == 'joins' else 'project_requests']
    return tk.render('colab_cs/inbox.html', extra_vars=values)


@blueprint.route('/projects/<project_id>')
def project_review(project_id):
    guard = _require_review()
    if guard is not None:
        return guard
    try:
        project = tk.get_action('csunesco_project_review_show')(context(), {'id': project_id})
    except tk.NotAuthorized:
        tk.abort(403, tk._('You are not authorized to view this page'))
    except tk.ObjectNotFound:
        tk.abort(404, tk._('Not found'))
    if project.get('organization_id'):
        organization = model.Group.get(project['organization_id'])
        if organization:
            project['organization_title'] = organization.title or organization.name
    from ckanext.csunesco import constants
    return tk.render('colab_cs/project_review.html', extra_vars={
        'project': project, 'project_steps': constants.PROJECT_FORM_STEPS,
        'tab': 'projects', 'capabilities': capabilities()})


def decide(action, payload, tab):
    guard = _require_review()
    if guard is not None:
        return guard
    current_app.extensions['csrf'].protect()
    try:
        tk.get_action(action)(context(), payload)
    except tk.NotAuthorized:
        tk.abort(403, tk._('You are not authorized to view this page'))
    except tk.ObjectNotFound:
        tk.h.flash_notice(tk._('This request is no longer available.'))
    except tk.ValidationError as exc:
        from ckanext.csunesco.logic.views_admin import _validation_messages
        tk.h.flash_error(' '.join(_validation_messages(exc)))
    else:
        tk.h.flash_success(tk._('Review decision saved.'))
    return tk.redirect_to(inbox_url(tab))


@blueprint.route('/managers/<username>/<decision>', methods=['POST'])
def manager_decision(username, decision):
    if decision not in ('approve', 'reject'):
        tk.abort(404)
    return decide('csunesco_manager_' + decision, {
        'username': username, 'reason': request.form.get('reason', ''),
        'organization_id': request.form.get('organization_id'),
        'organization_role': request.form.get('organization_role')}, 'managers')


@blueprint.route('/joins/<project_id>/<user_id>/<decision>', methods=['POST'])
def join_decision(project_id, user_id, decision):
    if decision not in ('approve', 'reject'):
        tk.abort(404)
    return decide('csunesco_join_' + decision, {'project_id': project_id, 'user_id': user_id}, 'joins')


@blueprint.route('/projects/<project_id>/<decision>', methods=['POST'])
def project_decision(project_id, decision):
    if decision not in ('approve', 'reject'):
        tk.abort(404)
    return decide('csunesco_project_' + decision, {
        'id': project_id, 'reason': request.form.get('reason', '')}, 'projects')


@blueprint.after_app_request
def private_reviews(response):
    if request.endpoint == 'colab.show_admin' or (request.endpoint or '').startswith('colab_cs.'):
        response.headers['Cache-Control'] = 'private, no-store'
    return response
