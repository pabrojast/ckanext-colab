"""Colab's Citizen Science inbox; CS actions own records and authorization."""
import logging

from flask import Blueprint, current_app, request
import ckan.model as model
import ckan.plugins.toolkit as tk

log = logging.getLogger(__name__)
blueprint = Blueprint('colab_cs', __name__, url_prefix='/colab/admin/citizen-science')
TABS = ('managers', 'joins', 'projects', 'manager_joins', 'claims')
NO_ACCESS = {'managers': False, 'joins': False, 'projects': False,
             'manager_joins': False}
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


def claims_available():
    """Citizens4Water project claims: records and permissions live in
    ckanext-c4w, exactly as join requests live in csunesco."""
    try:
        tk.get_action('c4w_project_claim_list')
        return True
    except KeyError:
        return False


def can_review_claims():
    if not claims_available() or not getattr(tk.g, 'user', None):
        return False
    try:
        tk.check_access('c4w_project_claim_decide', context(), {})
        return True
    except tk.NotAuthorized:
        return False


def can_review_cs():
    if not available() or not getattr(tk.g, 'user', None):
        return False
    from ckanext.csunesco.logic.auth import is_reviewer
    return is_reviewer(context())


def can_review():
    return can_review_cs() or can_review_claims()


def capabilities():
    allowed = dict(NO_ACCESS)
    if can_review_cs():
        from ckanext.csunesco.logic import auth
        ctx = context()
        allowed = {'managers': auth._is_sysadmin(ctx),
                   'manager_joins': auth._is_sysadmin(ctx),
                   'projects': auth._is_sysadmin(ctx) or auth._is_any_initiative_admin(ctx),
                   'joins': auth.is_reviewer(ctx)}
    allowed['claims'] = can_review_claims()
    return allowed


def claims_pending_count():
    try:
        return tk.get_action('c4w_project_claim_pending_count')(context(), {})
    except (KeyError, tk.NotAuthorized):
        return 0


def pending_count():
    total = claims_pending_count() if can_review_claims() else 0
    if not can_review_cs():
        return total
    return total + _cs_pending_count()


def _cs_pending_count():
    from ckanext.csunesco.logic.action.admin import _get_pending_counts
    counts = _get_pending_counts(context())
    total = counts.get('join_requests', 0) + counts.get('project_requests', 0)
    if capabilities()['managers']:
        from ckanext.csunesco import db
        total += model.Session.query(db.CsCitizenScientist).filter(
            db.CsCitizenScientist.profile_type == 'manager',
            db.CsCitizenScientist.email_verified.is_(True),
            db.CsCitizenScientist.manager_decision.is_(None)).count()
    if capabilities()["manager_joins"]:
        total += model.Session.query(db.CsJoinRequest).filter_by(requested_role="project_manager", status="pending").count()
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
    default = 'joins' if allowed.get('joins') or not allowed.get('claims') else 'claims'
    tab = request.args.get('tab', default)
    if tab not in TABS or not allowed.get(tab):
        tk.abort(403, tk._('You are not authorized to view this page'))
    offset = _offset()
    if not any(allowed.get(key) for key in NO_ACCESS):
        return _show_claims_only(allowed, offset)
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
    manager_joins = []
    if allowed['manager_joins']:
        manager_joins = [row for row in tk.get_action('csunesco_pathway_requests')(context(), {'review': True}) if row['requested_role'] == 'project_manager' and row['status'] == 'pending']
    values['manager_joins'] = manager_joins[offset:offset+PAGE_SIZE]
    values['counts'] = dict(data['counts'])
    values['counts']['manager_joins'] = len(manager_joins)
    values['counts']['managers'] = values['result']['count']
    values['count'] = values['result']['count'] if tab == 'managers' else data['counts']['join_requests' if tab == 'joins' else 'project_requests']
    if tab == 'manager_joins': values['count'] = len(manager_joins)
    _add_claims(values, allowed, tab, offset)
    return tk.render('colab_cs/inbox.html', extra_vars=values)


CLAIM_STATUSES = ('pending', 'approved', 'rejected', 'all')


def _add_claims(values, allowed, tab, offset):
    """Citizens4Water project claims, read through the C4W action."""
    values.setdefault('counts', {})
    values['claims'] = {'count': 0, 'results': []}
    if not allowed.get('claims'):
        return
    status = request.args.get('status', 'pending') if tab == 'claims' else 'pending'
    if status not in CLAIM_STATUSES:
        tk.abort(400, tk._('Invalid filter'))
    values['claims'] = tk.get_action('c4w_project_claim_list')(context(), {
        'status': status, 'limit': PAGE_SIZE,
        'offset': offset if tab == 'claims' else 0})
    values['counts']['claims'] = claims_pending_count()
    if tab == 'claims':
        values.update(count=values['claims']['count'], status=status)


def _show_claims_only(allowed, offset):
    """A C4W content administrator who reviews nothing in csunesco."""
    values = dict(tab='claims', capabilities=allowed, offset=offset,
                  page_size=PAGE_SIZE, can_review_projects=False,
                  status=request.args.get('status', 'pending'),
                  q='', counts={}, manager_joins=[],
                  result={'count': 0, 'results': []}, organizations=[],
                  join_requests=[], project_requests=[])
    _add_claims(values, allowed, 'claims', offset)
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
        tk.h.flash_error(' '.join(_validation_messages(exc)))
    else:
        tk.h.flash_success(tk._('Review decision saved.'))
    return tk.redirect_to(inbox_url(tab))


def _validation_messages(error):
    try:
        from ckanext.csunesco.logic.views_admin import _validation_messages as flatten
        return flatten(error)
    except ImportError:
        messages = []
        for value in (getattr(error, 'error_dict', None) or {}).values():
            messages.extend([value] if isinstance(value, str) else list(value))
        return messages or [tk._('That item could not be updated.')]


@blueprint.route('/managers/<username>/<decision>', methods=['POST'])
def manager_decision(username, decision):
    if decision not in ('approve', 'reject'):
        tk.abort(404)
    return decide('csunesco_manager_' + decision, {
        'username': username, 'reason': request.form.get('reason', ''),
        'organization_id': request.form.get('organization_id'),
        'organization_role': request.form.get('organization_role')}, 'managers')


REJECT_REASON_MIN = 10


@blueprint.route('/joins/<project_id>/<user_id>/<decision>', methods=['POST'])
def join_decision(project_id, user_id, decision):
    if decision not in ('approve', 'reject'):
        tk.abort(404)
    payload = {'project_id': project_id, 'user_id': user_id}
    if decision == 'reject':
        # The person reads this in the decision e-mail and in the Toolbox, as
        # when their project manager rejects them there (same minimum).
        reason = (request.form.get('reason') or '').strip()
        if len(reason) < REJECT_REASON_MIN:
            tk.h.flash_error(tk._('Write the reason for the person (at least 10 characters).'))
            return tk.redirect_to(inbox_url('joins'))
        payload['reason'] = reason
    return decide('csunesco_join_' + decision, payload, 'joins')


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


@blueprint.route('/manager-joins/<request_id>/<decision>', methods=['POST'])
def manager_join_decision(request_id, decision):
    if decision not in ('approve', 'reject'):
        tk.abort(404)
    return decide('csunesco_pathway_decide', {'id': request_id, 'decision': decision,
        'reason': request.form.get('reason', '')}, 'manager_joins')


@blueprint.route('/claims/<claim_id>/<decision>', methods=['POST'])
def claim_decision(claim_id, decision):
    """Approve or reject a Citizens4Water project claim."""
    if decision not in ('approve', 'reject'):
        tk.abort(404)
    payload = {'id': claim_id, 'decision': decision}
    if decision == 'reject':
        reason = (request.form.get('reason') or '').strip()
        if len(reason) < REJECT_REASON_MIN:
            tk.h.flash_error(tk._('Write the reason for the person (at least 10 characters).'))
            return tk.redirect_to(inbox_url('claims'))
        payload['reason'] = reason
    else:
        payload['reason'] = (request.form.get('reason') or '').strip()
    return decide('c4w_project_claim_decide', payload, 'claims')
