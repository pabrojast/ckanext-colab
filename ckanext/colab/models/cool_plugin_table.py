from sqlalchemy import Table, Column, types, MetaData
from ckan.model import meta
from ckan.model import meta, Package, domain_object

metadata = MetaData()

cool_plugin_table = Table(
    'colab',
    metadata,
    Column('id', types.Integer, primary_key=True, autoincrement=True),
    Column('fullname', types.String),
    Column('wins_username', types.String),
    Column('email', types.String),
    Column('approved', types.String),
    Column('approvedgroup', types.String),
    Column('organization_name', types.String),
    Column('new_organization_name', types.Integer),
    Column('new_organization_description', types.String), 
    Column('title_within_organization', types.String),
    Column('gender', types.String),
    Column('organizationType', types.String),
    Column('nationality', types.String),
    Column('age', types.Integer),
    Column('user_role', types.String),
    Column('rejected', types.String),
    Column('rejection_reason', types.String)
    )


class CoolPluginTable(domain_object.DomainObject):
    def __init__(self, fullname=None, wins_username=None, email=None, organization_name = None, new_organization_name = None, new_organization_description = None, approved=None,  approvedgroup=None, title_within_organization=None, gender=None,age=None, organizationType=None, nationality=None, user_role=None, rejected=None, rejection_reason=None):
        self.fullname = fullname
        self.wins_username = wins_username        
        self.email = email
        self.organization_name = organization_name
        self.new_organization_name = new_organization_name
        self.approved = approved
        self.approvedgroup = approvedgroup
        self.title_within_organization = title_within_organization
        self.gender = gender
        self.age = age
        self.new_organization_description = new_organization_description
        self.organizationType = organizationType
        self.nationality = nationality
        self.user_role = user_role
        self.rejected = rejected
        self.rejection_reason = rejection_reason

meta.mapper(CoolPluginTable, cool_plugin_table)