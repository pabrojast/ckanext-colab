# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is ckanext-colab, a CKAN extension that provides user management and organization approval workflow functionality. It features:

- User registration forms with extended profile information
- Admin approval workflow for users and organizations
- Email notifications for administrators
- Multi-tab interface for managing requests
- Support for both new and existing organizations
- Demographic data collection (age, gender, nationality)

## Architecture

The extension follows standard CKAN plugin architecture:

- **Main Plugin**: `ckanext/colab/plugin.py` - ColabPlugin class implementing IConfigurer, IBlueprint, ITranslation, and ITemplateHelpers
- **Controller Logic**: `ckanext/colab/controller.py` - MyLogic class with static methods for handling requests
- **Database Models**: `ckanext/colab/models/cool_plugin_table.py` - CoolPluginTable for storing user registration data
- **Templates**: `ckanext/colab/templates/colab_temp/` - HTML templates for forms and admin interface
- **Static Assets**: `ckanext/colab/public/colab_static/` - CSS and image files
- **Email Notifications**: `ckanext/colab/lib/email_notifications.py` - Functions for sending admin notifications

## Key Routes

- `/colab` - Main user registration form (GET/POST)
- `/colab/admin` - Admin interface for managing requests (GET)
- `/colab/admin/approve` - Approve user requests (POST)
- `/colab/admin/approve/<params>` - Legacy approve endpoint (GET)
- `/colab/admin/reject/<params>` - Reject user requests (GET)
- `/colab/admin/approvegroup/<params>` - Approve group requests (GET)

## Development Commands

### Installation and Setup
```bash
# Install in development mode
pip install -e .
pip install -r requirements.txt

# Install development dependencies
pip install -r dev-requirements.txt

# Initialize database
ckan db init -p colab
```

### Database Migrations
```bash
# Generate migration
ckan -c production.ini generate migration -p colab -m 'migration description'

# Apply migrations
ckan -c production.ini db upgrade -p colab
```

### Testing
```bash
# Run tests using pytest-ckan
pytest ckanext/colab/tests/
```

### Internationalization
```bash
# Extract messages
python setup.py extract_messages

# Update translations
python setup.py update_catalog

# Compile translations
python setup.py compile_catalog
```

## Configuration

Add `colab` to `ckan.plugins` in your CKAN configuration file.

Required settings for full functionality:
- `ckan.recaptcha.publickey` - reCAPTCHA public key
- `ckan.recaptcha.privatekey` - reCAPTCHA private key
- SMTP settings for email notifications

## Database Schema

The extension creates a `CoolPluginTable` with fields for:
- User information (fullname, wins_username, email)
- Organization details (organization_name, new_organization_name, new_organization_description)
- Approval status (approved, approvedgroup, rejected, rejection_reason)
- Demographic data (age, gender, nationality, organizationType)
- User role (admin, editor, member)

## Dependencies

- CKAN 2.9+
- Python 3.7+
- SQLAlchemy 1.3.0+
- requests 2.25.0+
- pytest-ckan (for testing)