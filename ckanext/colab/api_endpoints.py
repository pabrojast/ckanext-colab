# encoding: utf-8
"""
Public API endpoints for ckanext-colab.

Exposes JSON endpoints to query application data (user → organization → status).
Follows the blueprint pattern used by ckanext-terria_view.
"""
import json
import logging

from flask import Blueprint, Response, request

import ckan.logic as logic
import ckan.model as model
import ckan.plugins.toolkit as toolkit

from ckanext.colab.models.cool_plugin_table import (
    CoolPluginTable,
    OrganizationRequestTable,
)


logger = logging.getLogger(__name__)


colab_api = Blueprint('colab_api', __name__)


def _json_response(data, status_code=200):
    return Response(
        json.dumps(data, ensure_ascii=False, default=str),
        status=status_code,
        content_type='application/json; charset=utf-8',
    )


def _error(message, status_code=500):
    return _json_response({'error': True, 'message': message}, status_code)


def _require_sysadmin():
    """Raise toolkit.NotAuthorized if the caller is not a sysadmin.

    Works for both session-cookie callers and API-key/token callers because
    CKAN populates ``toolkit.g.user`` from either source before the view runs.
    """
    context = {
        'model': model,
        'user': toolkit.g.user,
        'auth_user_obj': toolkit.g.userobj,
    }
    logic.check_access('sysadmin', context, {})


def _normalize_status(record):
    """Map a CoolPluginTable row to a coarse status: pending|approved|rejected."""
    if record.rejected:
        return 'rejected'
    approved = (record.approved or '').strip()
    if approved and approved.lower() != 'pending' and 'approved by' in approved.lower():
        return 'approved'
    return 'pending'


def _resolve_org(name_or_slug):
    """Look up an organization by name/id/slug. Returns (id, name, title).

    Falls back to (None, name_or_slug, name_or_slug) when no matching CKAN
    organization exists yet — e.g. for a not-yet-approved new organization.
    """
    raw = (name_or_slug or '').strip()
    if not raw:
        return None, None, None
    try:
        org = toolkit.get_action('organization_show')(
            {'ignore_auth': True},
            {
                'id': raw,
                'include_users': False,
                'include_datasets': False,
                'include_followers': False,
                'include_extras': False,
                'include_tags': False,
                'include_groups': False,
            },
        )
        return org.get('id'), org.get('name'), org.get('title') or org.get('display_name')
    except (toolkit.ObjectNotFound, logic.NotFound):
        pass
    except Exception as exc:
        logger.warning("_resolve_org('%s') failed: %s", raw, exc)
    # Try the slugified form too (form may store the typed title for a brand-new org).
    slug = raw.lower().replace(' ', '-').replace("'", '').replace('.', '') \
              .replace('(', '').replace(')', '')
    if slug and slug != raw:
        try:
            org = toolkit.get_action('organization_show')(
                {'ignore_auth': True},
                {
                    'id': slug,
                    'include_users': False,
                    'include_datasets': False,
                    'include_followers': False,
                    'include_extras': False,
                    'include_tags': False,
                    'include_groups': False,
                },
            )
            return org.get('id'), org.get('name'), org.get('title') or org.get('display_name')
        except (toolkit.ObjectNotFound, logic.NotFound):
            pass
        except Exception as exc:
            logger.warning("_resolve_org slug fallback '%s' failed: %s", slug, exc)
    return None, raw, raw


@colab_api.route('/api/colab/user-organizations', methods=['GET'])
def user_organizations():
    """List every applicant's (username, organization, status).

    Query params:
        status: optional filter — ``pending``, ``approved``, or ``rejected``.
                Multiple values comma-separated, e.g. ``status=pending,approved``.
        include_rejected: ``true`` to include rejected rows when no ``status`` filter is given.
                          Defaults to ``false`` so the default response only shows
                          pending and approved applications, matching the request.
        include_org_requests: ``true`` to also include rows from the
                              organization-creation request table.
    """
    try:
        _require_sysadmin()
    except logic.NotAuthorized:
        return _error('Sysadmin privileges required.', 403)

    status_filter_raw = (request.args.get('status') or '').strip().lower()
    include_rejected = request.args.get('include_rejected', '').strip().lower() == 'true'
    include_org_requests = request.args.get('include_org_requests', '').strip().lower() == 'true'

    allowed_statuses = {'pending', 'approved', 'rejected'}
    if status_filter_raw:
        requested = {s.strip() for s in status_filter_raw.split(',') if s.strip()}
        invalid = requested - allowed_statuses
        if invalid:
            return _error(
                f"Invalid status filter: {', '.join(sorted(invalid))}. "
                f"Allowed: pending, approved, rejected.",
                400,
            )
        status_filter = requested
    elif include_rejected:
        status_filter = allowed_statuses
    else:
        status_filter = {'pending', 'approved'}

    try:
        rows = (
            model.Session.query(CoolPluginTable)
            .filter(CoolPluginTable.deleted_at.is_(None))
            .order_by(CoolPluginTable.created_date.desc())
            .all()
        )
    except Exception as exc:
        logger.exception("user_organizations: failed to query colab table: %s", exc)
        return _error('Failed to query application data.', 500)

    items = []
    for r in rows:
        status = _normalize_status(r)
        if status not in status_filter:
            continue
        items.append({
            'username': r.wins_username,
            'organization': r.organization_name,
            'status': status,
            'source': 'user_application',
        })

    if include_org_requests:
        try:
            org_rows = (
                model.Session.query(OrganizationRequestTable)
                .order_by(OrganizationRequestTable.created_date.desc())
                .all()
            )
        except Exception as exc:
            logger.warning(
                "user_organizations: failed to query organization requests: %s", exc
            )
            org_rows = []

        for r in org_rows:
            raw_status = (r.status or '').strip().lower()
            if raw_status == 'approved':
                status = 'approved'
            elif raw_status == 'rejected':
                status = 'rejected'
            else:
                status = 'pending'
            if status not in status_filter:
                continue
            items.append({
                'username': r.requester_username,
                'organization': r.organization_name,
                'status': status,
                'source': 'organization_request',
            })

    return _json_response({
        'count': len(items),
        'filter': sorted(status_filter),
        'results': items,
    })


@colab_api.route('/api/colab/organization-list-for-user', methods=['GET'])
def organization_list_for_user():
    """Return every organization for a single user, including not-yet-approved ones.

    Mirrors the shape of CKAN's ``organization_list_for_user`` but additionally
    surfaces:
      * pending and rejected user-registration applications (CoolPluginTable)
      * pending and rejected organization-creation requests
        (OrganizationRequestTable)

    Each result entry contains ``id``, ``name``, ``title`` — matching the keys
    used by the existing integration — plus ``status`` (one of
    ``approved`` | ``pending`` | ``rejected``) and ``source`` describing where
    the record came from.

    Query params:
        id: required — username of the user to look up.
        include_rejected: ``true`` to also return rejected applications and
                          rejected org-creation requests. Defaults to ``false``.

    Auth: caller must be a sysadmin OR must be authenticated as the user being
    queried.
    """
    username = (request.args.get('id') or '').strip()
    if not username:
        return _error("Missing required query param 'id' (username).", 400)

    caller = (toolkit.g.user or '').strip() if hasattr(toolkit.g, 'user') else ''
    if not caller:
        return _error('Authentication required.', 401)

    try:
        _require_sysadmin()
        is_sysadmin = True
    except logic.NotAuthorized:
        is_sysadmin = False

    if not is_sysadmin and caller != username:
        return _error('You can only list organizations for your own user.', 403)

    include_rejected = request.args.get('include_rejected', '').strip().lower() == 'true'

    results = []
    seen_ids = set()
    seen_names = set()

    def _push(entry):
        oid = entry.get('id')
        oname = (entry.get('name') or '').lower()
        if oid and oid in seen_ids:
            return False
        if not oid and oname and oname in seen_names:
            return False
        if oid:
            seen_ids.add(oid)
        if oname:
            seen_names.add(oname)
        results.append(entry)
        return True

    # 1. Approved memberships via the CKAN core action.
    try:
        approved_orgs = toolkit.get_action('organization_list_for_user')(
            {'ignore_auth': True, 'user': username},
            {'id': username, 'permission': 'read'},
        )
    except Exception as exc:
        logger.warning(
            "organization_list_for_user: CKAN core lookup failed for '%s': %s",
            username, exc,
        )
        approved_orgs = []

    for org in approved_orgs or []:
        _push({
            'id': org.get('id'),
            'name': org.get('name'),
            'title': org.get('title') or org.get('display_name'),
            'status': 'approved',
            'source': 'ckan_membership',
        })

    # 2. User-registration applications — pending and (optionally) rejected.
    try:
        user_rows = (
            model.Session.query(CoolPluginTable)
            .filter(CoolPluginTable.wins_username == username)
            .filter(CoolPluginTable.deleted_at.is_(None))
            .order_by(CoolPluginTable.created_date.desc())
            .all()
        )
    except Exception as exc:
        logger.warning(
            "organization_list_for_user: failed to query user applications for '%s': %s",
            username, exc,
        )
        user_rows = []

    for r in user_rows:
        status = _normalize_status(r)
        if status == 'approved':
            continue  # already returned via the core action
        if status == 'rejected' and not include_rejected:
            continue
        org_id, org_name, org_title = _resolve_org(r.organization_name)
        if not org_name and not org_id:
            continue
        _push({
            'id': org_id,
            'name': org_name,
            'title': org_title,
            'status': status,
            'source': 'user_application',
        })

    # 3. Organization-creation requests submitted by the user.
    try:
        org_req_rows = (
            model.Session.query(OrganizationRequestTable)
            .filter(OrganizationRequestTable.requester_username == username)
            .order_by(OrganizationRequestTable.created_date.desc())
            .all()
        )
    except Exception as exc:
        logger.warning(
            "organization_list_for_user: failed to query org requests for '%s': %s",
            username, exc,
        )
        org_req_rows = []

    for r in org_req_rows:
        raw_status = (r.status or '').strip().lower()
        if raw_status == 'approved':
            status = 'approved'
        elif raw_status == 'rejected':
            status = 'rejected'
        else:
            status = 'pending'
        if status == 'rejected' and not include_rejected:
            continue
        org_id, org_name, org_title = _resolve_org(r.organization_name)
        if not org_name and not org_id:
            continue
        _push({
            'id': org_id,
            'name': org_name,
            'title': org_title,
            'status': status,
            'source': 'organization_request',
        })

    return _json_response({
        'username': username,
        'count': len(results),
        'results': results,
    })
