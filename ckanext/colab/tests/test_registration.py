"""Exercise registration without importing the controller's startup DB migration."""

import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest


CONTROLLER_PATH = Path(__file__).resolve().parents[1] / 'controller.py'


@pytest.fixture
def registration():
    # Execute the actual handler with CKAN I/O replaced by test doubles. This
    # also runs in the lightweight test environment without a CKAN database.
    source = ast.parse(CONTROLLER_PATH.read_text())
    controller = next(node for node in source.body
                      if isinstance(node, ast.ClassDef) and node.name == 'MyLogic')
    handler = next(node for node in controller.body
                   if isinstance(node, ast.FunctionDef) and node.name == 'show_something')
    handler.decorator_list = []

    class ObjectNotFound(Exception):
        pass

    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    application = MagicMock(side_effect=lambda **fields: SimpleNamespace(**fields))
    actions = {'user_show': Mock(return_value={'name': 'applicant'}),
               'user_create': Mock(return_value={'name': 'applicant'})}
    toolkit = SimpleNamespace(
        config={}, g=SimpleNamespace(user=''), ObjectNotFound=ObjectNotFound,
        get_action=Mock(side_effect=actions.__getitem__), _=lambda text: text,
    )
    form = {
        'form_submitted': 'true', 'wins_username': 'applicant',
        'email': 'applicant@example.org', 'wins_password': 'test-password',
        'confirm-password': 'test-password', 'title_within_organization': 'Researcher',
        'organization_name': 'existing-org', 'date_of_birth': '1990-01-01',
        'nationality': 'Chilean', 'gender': 'preferNotToSay',
    }
    namespace = {
        'request': SimpleNamespace(method='POST', form=form),
        'toolkit': toolkit, 'model': SimpleNamespace(Session=session),
        'logic': SimpleNamespace(check_access=Mock(), NotAuthorized=type('NotAuthorized', (Exception,), {})),
        'CoolPluginTable': application, 'or_': Mock(), 'logger': Mock(),
        'get_all_groups_cached': Mock(return_value=[]),
        'render_template': Mock(side_effect=lambda template, **context: context),
        'ensure_colab_schema': Mock(), 'handle_org_logo_upload': Mock(return_value=None),
        'send_admin_notification': Mock(), 'send_applicant_confirmation': Mock(),
    }
    exec(compile(ast.Module(body=[handler], type_ignores=[]), str(CONTROLLER_PATH), 'exec'), namespace)
    return SimpleNamespace(
        submit=namespace['show_something'], form=form, session=session,
        actions=actions, toolkit=toolkit, dependencies=namespace,
    )


@pytest.mark.parametrize('role', [None, '', 'member', 'owner'])
def test_existing_organization_rejects_invalid_role_before_side_effects(registration, role):
    if role is not None:
        registration.form['user_role'] = role

    result = registration.submit()

    assert result['errornewuserform'] is True
    assert result['error_message'] == 'Please select Editor or Admin as your role in the organization.'
    registration.toolkit.get_action.assert_not_called()
    registration.session.query.assert_not_called()
    registration.session.add.assert_not_called()
    registration.session.commit.assert_not_called()
    for name in ('handle_org_logo_upload', 'ensure_colab_schema',
                 'send_admin_notification', 'send_applicant_confirmation'):
        registration.dependencies[name].assert_not_called()


@pytest.mark.parametrize('existing_user', [True, False])
@pytest.mark.parametrize('organization,submitted_role,expected_role', [
    ('existing-org', 'editor', 'editor'),
    ('existing-org', 'admin', 'admin'),
    ('new', None, 'admin'),
    ('new', 'editor', 'admin'),
    ('new', 'member', 'admin'),
])
def test_registration_roles_and_omitted_platforms(
        registration, existing_user, organization, submitted_role, expected_role):
    registration.form['organization_name'] = organization
    if organization == 'new':
        registration.form['new_organization_name'] = 'New organization'
    if submitted_role is not None:
        registration.form['user_role'] = submitted_role
    if not existing_user:
        registration.actions['user_show'].side_effect = registration.toolkit.ObjectNotFound()

    result = registration.submit()

    assert result['newuser'] is True
    assert result['errornewuserform'] is False
    application = result['application']
    assert application.user_role == expected_role
    assert application.organization_name == ('New organization' if organization == 'new' else organization)
    assert application.new_organization_name == (1 if organization == 'new' else 0)
    assert application.citizens4water == ''
    assert application.ihp_wins == ''
    assert application.approved == 'Pending'
    registration.session.add.assert_called_once_with(application)
    registration.session.commit.assert_called_once()
    registration.session.rollback.assert_not_called()
    assert registration.actions['user_create'].call_count == (0 if existing_user else 1)
    registration.dependencies['send_applicant_confirmation'].assert_called_once_with(application)
