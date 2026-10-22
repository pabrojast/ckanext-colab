"""Canonical organization membership for all Colab approval entry points."""
import ckan.model as model
import ckan.plugins.toolkit as tk

RANK = {'member': 1, 'editor': 2, 'admin': 3}


def resolve_organization(identifier):
    org = model.Group.get(identifier)
    if org is None and identifier:
        # Historical applications sometimes stored the title instead of the slug.
        matches = model.Session.query(model.Group).filter(
            model.Group.title == identifier, model.Group.is_organization.is_(True),
            model.Group.state == 'active').all()
        if len(matches) == 1:
            org = matches[0]
    return org


def ensure_organization_member(context, data):
    role = data.get('role')
    if role not in RANK:
        raise tk.ValidationError({'role': ['Choose Member, Editor or Admin.']})
    org = resolve_organization(data.get('id'))
    user = model.User.get(data.get('username'))
    if org is None or not org.is_organization or org.state != 'active':
        raise tk.ObjectNotFound('Organization not found')
    if user is None or user.state != 'active':
        raise tk.ObjectNotFound('User not found')
    canonical = {'id': org.id, 'username': user.name, 'role': role}
    # Do not let an idempotent re-approval reduce an existing role.
    tk.check_access('organization_member_create', context, canonical)
    def membership():
        return model.Session.query(model.Member).filter(
            model.Member.group_id == org.id, model.Member.table_name == 'user',
            model.Member.table_id == user.id, model.Member.state == 'active').first()
    current = membership()
    if current is None or RANK.get(current.capacity, 0) < RANK[role]:
        tk.get_action('organization_member_create')(dict(context, defer_commit=True), canonical)
        model.Session.flush()
    confirmed = membership()
    if confirmed is None or RANK.get(confirmed.capacity, 0) < RANK[role]:
        raise tk.ValidationError({'organization': ['Organization membership was not confirmed.']})
    return {'id': org.id, 'name': org.name, 'user_id': user.id, 'role': confirmed.capacity}
