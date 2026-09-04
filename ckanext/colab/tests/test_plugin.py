import ast
from pathlib import Path
import re


BASE_DIR = Path(__file__).resolve().parents[3]
CONTROLLER_PATH = BASE_DIR / 'ckanext' / 'colab' / 'controller.py'
PLUGIN_PATH = BASE_DIR / 'ckanext' / 'colab' / 'plugin.py'


def _class_method_names(path, class_name):
    module = ast.parse(path.read_text())
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                child.name for child in node.body
                if isinstance(child, ast.FunctionDef)
            }
    raise AssertionError(f'Class {class_name} not found in {path}')


def test_mylogic_handlers_exist():
    method_names = _class_method_names(CONTROLLER_PATH, 'MyLogic')
    assert 'check_status' in method_names
    assert 'reject_post' in method_names


def test_reject_blueprint_routes_are_post_only():
    plugin_source = PLUGIN_PATH.read_text()
    assert re.search(
        r"u'/colab/admin/reject',\s+u'reject_post',\s+MyLogic\.reject_post,\s+methods=\['POST'\]",
        plugin_source,
        re.DOTALL,
    )
    assert re.search(
        r"u'/colab/admin/reject/<name>/<organization>/<reason>',\s+u'reject',\s+MyLogic\.reject,\s+methods=\['POST'\]",
        plugin_source,
        re.DOTALL,
    )


FORM_PATH = BASE_DIR / 'ckanext' / 'colab' / 'templates' / 'colab_temp' / 'snippets' / 'form.html'
API_PATH = BASE_DIR / 'ckanext' / 'colab' / 'api_endpoints.py'


def test_organizations_lookup_route_is_public():
    api_source = API_PATH.read_text()
    assert "/api/colab/organizations" in api_source
    assert "def organizations_lookup(" in api_source
    assert "get_all_organizations_cached" in api_source
    assert "filter_organizations" in api_source


def test_registration_form_uses_searchable_combobox():
    form_source = FORM_PATH.read_text()
    assert 'role="combobox"' in form_source
    assert 'id="organization_search"' in form_source
    assert 'id="new_org_sentinel"' in form_source
    assert 'name="organization_name"' in form_source
    assert 'value="new"' in form_source
    assert 'organization_list?all_fields=true' not in form_source
    assert '<select name="organization_name"' not in form_source
    assert 'colab_api.organizations_lookup' in form_source
    assert 'org-create-from-search' in form_source
    assert 'org-similar' in form_source
    # CKAN Jinja newstyle gettext runs `msgstr % variables`. A bare
    # `_('...%(query)s...')` raises KeyError('query') and 500s /colab.
    assert "query='%(query)s'" in form_source
    assert "shown='%(shown)s'" in form_source
    assert "total='%(total)s'" in form_source
