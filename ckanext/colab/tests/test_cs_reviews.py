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
    allowed = {'managers': False, 'projects': False, 'joins': True}
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
