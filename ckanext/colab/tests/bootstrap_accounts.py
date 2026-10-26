"""Initialize the explicitly named disposable CI database, without web startup."""
import os
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from ckan.cli import load_config
from ckan.common import config
import ckan.model as model

url = os.environ['COLAB_ACCOUNT_TEST_DB']
if not make_url(url).database.startswith('colab_test'):
    raise RuntimeError('Refusing to initialize anything except a colab_test database')
config.update(load_config('/app/production.ini'))
config['sqlalchemy.url'] = url
engine = create_engine(url)
model.init_model(engine)
model.repo.init_db()
from ckanext.colab.models.cool_plugin_table import metadata
from ckanext.colab.models import account_update  # registers the new receipt table
metadata.create_all(engine)
