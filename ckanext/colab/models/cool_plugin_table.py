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
    Column('rejection_reason', types.String),
    Column('citizens4water', types.String)
    )

organization_request_table = Table(
    'colab_organization_requests',
    metadata,
    Column('id', types.Integer, primary_key=True, autoincrement=True),
    Column('requester_username', types.String, nullable=False),
    Column('organization_name', types.String, nullable=False),
    Column('organization_description', types.String),
    Column('organization_image_url', types.String),
    Column('admin_username', types.String, nullable=False),
    Column('organization_type', types.String),
    Column('status', types.String, default='pending'),
    Column('created_date', types.DateTime),
    Column('approved_by', types.String),
    Column('approved_date', types.DateTime),
    Column('rejected_by', types.String),
    Column('rejected_date', types.DateTime),
    Column('rejection_reason', types.String)
    )


class CoolPluginTable(domain_object.DomainObject):
    def __init__(self, fullname=None, wins_username=None, email=None, organization_name = None, new_organization_name = None, new_organization_description = None, approved=None,  approvedgroup=None, title_within_organization=None, gender=None,age=None, organizationType=None, nationality=None, user_role=None, rejected=None, rejection_reason=None, citizens4water=None):
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
        self.citizens4water = citizens4water

class OrganizationRequestTable(domain_object.DomainObject):
    def __init__(self, requester_username=None, organization_name=None, organization_description=None, 
                 organization_image_url=None, admin_username=None, organization_type=None, 
                 status='pending', created_date=None, approved_by=None, approved_date=None,
                 rejected_by=None, rejected_date=None, rejection_reason=None):
        self.requester_username = requester_username
        self.organization_name = organization_name
        self.organization_description = organization_description
        self.organization_image_url = organization_image_url
        self.admin_username = admin_username
        self.organization_type = organization_type
        self.status = status
        self.created_date = created_date
        self.approved_by = approved_by
        self.approved_date = approved_date
        self.rejected_by = rejected_by
        self.rejected_date = rejected_date
        self.rejection_reason = rejection_reason

meta.mapper(CoolPluginTable, cool_plugin_table)
meta.mapper(OrganizationRequestTable, organization_request_table)