"""Read a signed-in account's own Colab details without changing its request."""
from sqlalchemy import func, inspect
import ckan.model as model


def registration_details(user):
    # Colab's legacy records have no CKAN user id. Require both identity fields;
    # matching either one alone could expose another applicant's personal data.
    if not user or not user.name or not user.email:
        return {}
    if not inspect(model.Session.get_bind()).has_table('colab'):
        return {}
    from ckanext.colab.models.cool_plugin_table import CoolPluginTable as Application
    row = (model.Session.query(Application.fullname, Application.date_of_birth,
                               Application.nationality, Application.gender)
           .filter(Application.wins_username == user.name,
                   func.lower(func.trim(Application.email)) == user.email.strip().lower(),
                   Application.deleted_at.is_(None))
           .order_by(Application.created_date.desc().nullslast(), Application.id.desc())
           .first())
    # Organization roles, decisions, internal notes and consent are not profile
    # defaults. An application is not authorization for Citizen Science access.
    return dict(row._mapping) if row else {}
