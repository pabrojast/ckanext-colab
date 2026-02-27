# Copilot Instructions for ckanext-colab

## Project Overview

CKAN extension providing user registration with admin approval workflow and organization request management. Built on CKAN 2.9+ / Python 3.7+.

## Build, Test, and Lint

```bash
# Install for development
pip install -e .
pip install -r requirements.txt
pip install -r dev-requirements.txt

# Run all tests
pytest --ckan-ini=test.ini --cov=ckanext.colab --disable-warnings ckanext/colab

# Run a single test
pytest --ckan-ini=test.ini ckanext/colab/tests/test_plugin.py::test_plugin

# Database init / migrations
ckan db init -p colab
ckan -c production.ini db upgrade -p colab
ckan -c production.ini generate migration -p colab -m 'description'

# i18n workflow
python setup.py extract_messages
python setup.py update_catalog
python setup.py compile_catalog
```

Tests require a running CKAN environment with Postgres, Solr, and Redis (see `.github/workflows/test.yml` for the CI setup).

## Architecture

### Plugin Structure

`ColabPlugin` (in `plugin.py`) implements four CKAN interfaces: `IConfigurer`, `IBlueprint`, `ITranslation`, `ITemplateHelpers`. All HTTP routes are registered via Flask Blueprints in `get_blueprint()`.

### Request Flow

All route handlers live as **static methods** on the `MyLogic` class in `controller.py`. This single file contains all business logic for both user registration and organization request workflows.

### Two Domain Models (in `models/cool_plugin_table.py`)

Both models use CKAN's `domain_object.DomainObject` with `meta.mapper()` (classical SQLAlchemy mapping, not declarative):

- **`CoolPluginTable`** → `colab` table: user registration requests with demographic data and approval status
- **`OrganizationRequestTable`** → `colab_organization_requests` table: organization creation requests with status tracking

### Database Migrations

Alembic migrations live in `ckanext/colab/migration/colab/versions/`. The `controller.py` also has a runtime schema repair function (`ensure_colab_schema`) that adds missing columns to the `colab` table on startup.

### Template Helpers

Two helpers are exposed to templates:
- `h.get_site_key()` — returns the reCAPTCHA public key from config
- `h.colab_image_url(image_path)` — generates full URL for uploaded organization images

### File Uploads

Organization images use CKAN's built-in uploader (`ckan.lib.uploader`). Filenames are stored in the database; full URLs are generated via the `colab_image_url` helper.

## Key Conventions

- Controller methods are all **static** on `MyLogic` — no instance state. Follow this pattern when adding new routes.
- Models use CKAN's **classical mapper pattern** (`meta.mapper(Class, table)`), not SQLAlchemy declarative base. New models should follow the same style.
- Templates live in `templates/colab_temp/` and static assets in `public/colab_static/`.
- The extension supports three languages (es, fr, ar). Run the i18n workflow after changing user-facing strings.
- Email notifications are sent to all active sysadmins via `ckan.lib.mailer`.
- The plugin name registered in `setup.py` entry points is `colab`.

## Configuration

Required in the CKAN `.ini` file:
- `ckan.plugins = colab`
- `ckan.recaptcha.publickey` / `ckan.recaptcha.privatekey` for form captcha
- SMTP settings for admin email notifications
