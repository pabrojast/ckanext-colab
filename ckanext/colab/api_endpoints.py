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
