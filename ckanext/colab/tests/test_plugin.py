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
