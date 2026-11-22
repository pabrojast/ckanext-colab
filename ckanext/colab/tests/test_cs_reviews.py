"""Review routing must retain scoped permissions, CSRF and private responses."""
from types import SimpleNamespace

import pytest
from flask import Flask, g, url_for, redirect
from werkzeug.exceptions import BadRequest
import ckan.plugins.toolkit as tk
from ckanext.colab import cs_reviews as reviews


@pytest.fixture
def inbox(monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'test-only'
    app.register_blueprint(reviews.blueprint)
    app.add_url_rule('/colab/admin', 'colab.show_admin', reviews.show)
    actor = SimpleNamespace(name='project-reviewer', sysadmin=False)
    allowed = {'managers': False, 'projects': False, 'joins': True, 'manager_joins': False}
    calls = []
    @app.before_request
    def identity():
        g.user = actor.name
        g.userobj = actor
    monkeypatch.setattr(reviews, 'can_review', lambda: bool(actor.name))
    monkeypatch.setattr(reviews, 'capabilities', lambda: allowed)
    monkeypatch.setattr(tk, '_', lambda value: value)
    monkeypatch.setattr(tk, 'url_for', url_for)
    monkeypatch.setattr(tk, 'redirect_to', redirect)
    monkeypatch.setattr(tk, 'render', lambda name, extra_vars: {'template': name, 'data': extra_vars})
    monkeypatch.setattr(tk, 'h', SimpleNamespace(flash_success=lambda value: None,
        flash_error=lambda value: None, flash_notice=lambda value: None))
    def action(name):
        def run(ctx, data):
            calls.append((name, ctx.get('user'), data))
            if name == 'csunesco_pathway_requests':
                return [{'id':'pending-pm','requested_role':'project_manager','status':'pending','review_state':'waiting_for_account_approval'}]
            if name == 'csunesco_admin_pending_list':
                return {'join_requests': [{'project_id':'own-project'}], 'project_requests': [],
                        'counts': {'join_requests':1,'project_requests':0}}
            return {'count':0,'results':[]}
        return run
    monkeypatch.setattr(tk, 'get_action', action)
    app.extensions['csrf'] = SimpleNamespace(protect=lambda: None)
    return app, actor, allowed, calls


def test_project_manager_reaches_only_the_scoped_join_queue(inbox):
    app, _, _, calls = inbox
    client = app.test_client()
    response = client.get('/colab/admin?tab=joins')
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'private, no-store'
    assert response.json['data']['join_requests'] == [{'project_id':'own-project'}]
    assert calls[0][1] == 'project-reviewer'
    assert client.get('/colab/admin?tab=managers').status_code == 403
    assert client.get('/colab/admin?tab=projects').status_code == 403
    assert len(calls) == 1


def test_manager_filters_reach_canonical_action_without_copying_records(inbox):
    app, _, allowed, calls = inbox
    allowed['managers'] = True
    response = app.test_client().get('/colab/admin?tab=managers&status=rejected&q=River&offset=20')
    assert response.status_code == 200
    assert calls[-1] == ('csunesco_manager_list', 'project-reviewer',
                        {'status':'rejected','q':'River','offset':20,'limit':20})


def test_decision_is_post_only_and_csrf_precedes_domain_action(inbox):
    app, _, _, calls = inbox
    url = '/colab/admin/citizen-science/joins/p/u/approve'
    client = app.test_client()
    assert client.get(url).status_code == 405
    def reject_csrf():
        raise BadRequest('Missing CSRF token')
    app.extensions['csrf'].protect = reject_csrf
    assert client.post(url).status_code == 400
    assert not calls
    app.extensions['csrf'].protect = lambda: None
    response = client.post(url, data={'actor_username':'forged-admin'})
    assert response.status_code == 302
    assert response.location.endswith('/colab/admin?tab=joins')
    assert calls == [('csunesco_join_approve','project-reviewer',{'project_id':'p','user_id':'u'})]


def test_domain_permission_failure_cannot_be_overridden_by_colab(inbox, monkeypatch):
    app, _, _, _ = inbox
    def denied(*args):
        raise tk.NotAuthorized('Another project')
    monkeypatch.setattr(tk, 'get_action', lambda name: denied)
    response = app.test_client().post('/colab/admin/citizen-science/joins/other/u/approve')
    assert response.status_code == 403


def test_pm_project_queue_is_admin_only_and_keeps_waiting_state(inbox):
    app, actor, allowed, calls = inbox
    client=app.test_client()
    assert client.get('/colab/admin?tab=manager_joins').status_code==403
    allowed['manager_joins']=True
    response=client.get('/colab/admin?tab=manager_joins')
    assert response.status_code==200
    assert response.json['data']['manager_joins'][0]['review_state']=='waiting_for_account_approval'
    assert response.json['data']['count']==1


def test_join_rejection_needs_a_reason_and_passes_it_to_the_portal(inbox, monkeypatch):
    app, _, _, calls = inbox
    errors = []
    monkeypatch.setattr(tk, 'h', SimpleNamespace(flash_success=lambda value: None,
        flash_error=errors.append, flash_notice=lambda value: None))
    client = app.test_client()
    url = '/colab/admin/citizen-science/joins/p/u/reject'
    for reason in ('', '   ', 'too short'):
        response = client.post(url, data={'reason': reason})
        assert response.status_code == 302
        assert response.location.endswith('/colab/admin?tab=joins')
    assert calls == [] and len(errors) == 3
    response = client.post(url, data={'reason': '  The project is full this season.  '})
    assert response.status_code == 302
    assert calls == [('csunesco_join_reject', 'project-reviewer',
                      {'project_id': 'p', 'user_id': 'u', 'reason': 'The project is full this season.'})]


def test_claims_tab_is_hidden_without_the_c4w_permission(inbox):
    app, _, allowed, calls = inbox
    client = app.test_client()
    assert client.get('/colab/admin?tab=claims').status_code == 403
    assert not [c for c in calls if c[0].startswith('c4w_')]


def test_c4w_admin_without_cs_role_sees_only_claims(inbox, monkeypatch):
    app, _, allowed, calls = inbox
    allowed.update(joins=False, claims=True)
    monkeypatch.setattr(reviews, 'claims_pending_count', lambda: 3)
    response = app.test_client().get('/colab/admin')
    assert response.status_code == 200
    data = response.json['data']
    assert data['tab'] == 'claims' and data['counts'] == {'claims': 3}
    assert [c[0] for c in calls] == ['c4w_project_claim_list']
    assert calls[0][2] == {'status': 'pending', 'limit': 20, 'offset': 0}


def test_claims_status_filter_is_validated(inbox):
    app, _, allowed, calls = inbox
    allowed['claims'] = True
    client = app.test_client()
    assert client.get('/colab/admin?tab=claims&status=approved').status_code == 200
    listed = [c for c in calls if c[0] == 'c4w_project_claim_list']
    assert listed[-1][2]['status'] == 'approved'
    assert client.get('/colab/admin?tab=claims&status=bogus').status_code == 400


def test_claim_decisions_go_to_the_c4w_action_and_reject_needs_a_reason(inbox, monkeypatch):
    app, _, _, calls = inbox
    errors = []
    monkeypatch.setattr(tk, 'h', SimpleNamespace(flash_success=lambda value: None,
        flash_error=errors.append, flash_notice=lambda value: None))
    client = app.test_client()
    assert client.get('/colab/admin/citizen-science/claims/c1/approve').status_code == 405
    assert client.post('/colab/admin/citizen-science/claims/c1/maybe').status_code == 404
    response = client.post('/colab/admin/citizen-science/claims/c1/reject', data={'reason': 'short'})
    assert response.location.endswith('/colab/admin?tab=claims')
    assert calls == [] and errors
    client.post('/colab/admin/citizen-science/claims/c1/reject',
                data={'reason': ' We could not verify your role. '})
    client.post('/colab/admin/citizen-science/claims/c2/approve')
    assert calls == [
        ('c4w_project_claim_decide', 'project-reviewer',
         {'id': 'c1', 'decision': 'reject', 'reason': 'We could not verify your role.'}),
        ('c4w_project_claim_decide', 'project-reviewer',
         {'id': 'c2', 'decision': 'approve', 'reason': ''})]
