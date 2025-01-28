[![Tests](https://github.com/pabrojst/ckanext-colab/workflows/Tests/badge.svg?branch=main)](https://github.com/pabrojst/ckanext-colab/actions)

# ckanext-colab

A CKAN extension that provides user management and organization approval workflow functionality.

## Features

- **User Registration Form**: Extended profile information collection.
- **Admin Approval Workflow**: Manage new users and organizations with ease.
- **Email Notifications**: Automated alerts for administrators upon new registrations.
- **Multi-Tab Interface**: Efficiently handle pending, approved, and rejected requests.
- **Organization Support**: Compatible with both new and existing organizations.
- **Demographic Data Collection**: Gather age, gender, and nationality information.

## Requirements

- **CKAN**: Version 2.9+
- **Python**: Version 3.7+

### Compatibility with Core CKAN Versions

| CKAN version | Compatible    |
|--------------|---------------|
| 2.9          | Yes           |
| 2.10         | Not Tested    |

## Installation

1. **Activate Your CKAN Virtual Environment**:

    ```bash
    . /usr/lib/ckan/default/bin/activate
    ```

2. **Clone the Repository and Install the Extension**:

    ```bash
    git clone https://github.com/pabrojast/ckanext-colab.git
    cd ckanext-colab
    pip install -e .
    pip install -r requirements.txt
    ```

3. **Configure CKAN**:

    Add `colab` to the `ckan.plugins` setting in your CKAN configuration file (default location: `/etc/ckan/default/ckan.ini`).

4. **Initialize the Database**:

    ```bash
    ckan db init -p colab
    ```

5. **Restart CKAN**:

    For example, if deployed with Apache on Ubuntu:

    ```bash
    sudo service apache2 reload
    ```

## Configuration Settings

Currently, there are no configurable settings. 

**TODO:** Document any optional configuration settings here. For example:

```ini
# The minimum number of hours to wait before re-checking a resource
# (optional, default: 24).
ckanext.colab.some_setting = some_default_value
```

## Migration and Upgrade

After making changes to the database schema or updating the extension, perform the following steps to apply migrations:

1. **Generate Migration Scripts**:

    ```bash
    ckan -c production.inigenerate migration -p colab -m 'member as option added'
    ```

2. **Upgrade the Database**:

    ```bash
    ckan -c production.ini db upgrade -p colab
    ```

