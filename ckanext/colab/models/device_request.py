from sqlalchemy import Table, Column, types, MetaData, UniqueConstraint, Index
from ckan.model import meta, domain_object
from datetime import datetime

metadata = MetaData()

device_request_table = Table(
    'device_requests',
    metadata,
    Column('id', types.Integer, primary_key=True, autoincrement=True),
    Column('organization_id', types.String),
    Column('created_by_user_id', types.String, nullable=False),
    Column('reviewed_by_user_id', types.String),
    Column('status', types.String, default='DRAFT'),
    # Device info
    Column('device_name', types.String),
    Column('device_label', types.String),
    Column('device_profile_name', types.String),
    Column('serial_number', types.String),
    Column('site_code', types.String),
    # Installation info
    Column('installer_name', types.String),
    Column('install_date', types.Date),
    Column('owner_name', types.String),
    Column('firmware_version', types.String),
    # Location
    Column('latitude', types.Float),
    Column('longitude', types.Float),
    Column('address', types.Text),
    Column('technical_notes', types.Text),
    # Metadata
    Column('photos_urls_json', types.Text),
    Column('survey_completed', types.Boolean, default=False),
    Column('metadata_complete', types.Boolean, default=False),
    Column('metadata_missing_fields_json', types.Text),
    # Timestamps
    Column('submitted_at', types.DateTime),
    Column('reviewed_at', types.DateTime),
    Column('approved_at', types.DateTime),
    Column('rejected_at', types.DateTime),
    Column('rejection_reason', types.Text),
    # Sync
    Column('sync_status', types.String),
    Column('sync_error_message', types.Text),
    # ThingsBoard references
    Column('tb_device_id', types.String),
    Column('tb_customer_id', types.String),
    Column('tb_access_token', types.String),
    # Audit
    Column('created_at', types.DateTime, default=datetime.utcnow),
    Column('updated_at', types.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
    # Constraints
    UniqueConstraint('serial_number', name='uq_device_requests_serial_number'),
    Index('ix_device_requests_status', 'status'),
    Index('ix_device_requests_created_by', 'created_by_user_id'),
)


class DeviceRequest(domain_object.DomainObject):
    def __init__(self, organization_id=None, created_by_user_id=None, reviewed_by_user_id=None,
                 status='DRAFT', device_name=None, device_label=None, device_profile_name=None,
                 serial_number=None, site_code=None, installer_name=None, install_date=None,
                 owner_name=None, firmware_version=None, latitude=None, longitude=None,
                 address=None, technical_notes=None, photos_urls_json=None,
                 survey_completed=False, metadata_complete=False, metadata_missing_fields_json=None,
                 submitted_at=None, reviewed_at=None, approved_at=None, rejected_at=None,
                 rejection_reason=None, sync_status=None, sync_error_message=None,
                 tb_device_id=None, tb_customer_id=None, tb_access_token=None,
                 created_at=None, updated_at=None):
        self.organization_id = organization_id
        self.created_by_user_id = created_by_user_id
        self.reviewed_by_user_id = reviewed_by_user_id
        self.status = status
        self.device_name = device_name
        self.device_label = device_label
        self.device_profile_name = device_profile_name
        self.serial_number = serial_number
        self.site_code = site_code
        self.installer_name = installer_name
        self.install_date = install_date
        self.owner_name = owner_name
        self.firmware_version = firmware_version
        self.latitude = latitude
        self.longitude = longitude
        self.address = address
        self.technical_notes = technical_notes
        self.photos_urls_json = photos_urls_json
        self.survey_completed = survey_completed
        self.metadata_complete = metadata_complete
        self.metadata_missing_fields_json = metadata_missing_fields_json
        self.submitted_at = submitted_at
        self.reviewed_at = reviewed_at
        self.approved_at = approved_at
        self.rejected_at = rejected_at
        self.rejection_reason = rejection_reason
        self.sync_status = sync_status
        self.sync_error_message = sync_error_message
        self.tb_device_id = tb_device_id
        self.tb_customer_id = tb_customer_id
        self.tb_access_token = tb_access_token
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()


meta.mapper(DeviceRequest, device_request_table)
