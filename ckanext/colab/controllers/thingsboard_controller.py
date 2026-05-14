from flask import render_template, request
import ckan.plugins.toolkit as toolkit
import ckan.model as model
import ckan.logic as logic
from ckanext.colab.models.device_request import DeviceRequest, device_request_table, metadata as dr_metadata
from datetime import datetime, date
import json
import logging

log = logging.getLogger(__name__)


class ThingsBoardLogic:
    """Controller for ThingsBoard device request management."""

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _require_login():
        if not toolkit.g.userobj:
            toolkit.abort(403, toolkit._('You must be logged in to access this page'))

    @staticmethod
    def _require_sysadmin():
        context = {'model': model, 'user': toolkit.g.user, 'auth_user_obj': toolkit.g.userobj}
        try:
            logic.check_access('sysadmin', context, {})
        except logic.NotAuthorized:
            toolkit.abort(403, toolkit._('Only system administrators can access this page'))

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_for_submission(req, request_id=None):
        """Validate a device request for submission. Returns list of error strings."""
        errors = []
        required = {
            'device_name': toolkit._('Device name'),
            'serial_number': toolkit._('Serial number'),
            'device_profile_name': toolkit._('Device profile name'),
            'site_code': toolkit._('Site code'),
            'installer_name': toolkit._('Installer name'),
            'install_date': toolkit._('Install date'),
            'owner_name': toolkit._('Owner name'),
        }
        for field, label in required.items():
            val = getattr(req, field, None)
            if not val:
                errors.append(toolkit._('%(field)s is required') % {'field': label})

        if not req.survey_completed:
            errors.append(toolkit._('Survey must be completed before submission'))

        # Serial number uniqueness
        if req.serial_number:
            query = model.Session.query(DeviceRequest).filter(
                DeviceRequest.serial_number == req.serial_number
            )
            if request_id:
                query = query.filter(DeviceRequest.id != request_id)
            if query.first():
                errors.append(toolkit._('Serial number already exists'))

        # Lat/lon ranges
        if req.latitude is not None:
            try:
                lat = float(req.latitude)
                if lat < -90 or lat > 90:
                    errors.append(toolkit._('Latitude must be between -90 and 90'))
            except (ValueError, TypeError):
                errors.append(toolkit._('Latitude must be a valid number'))

        if req.longitude is not None:
            try:
                lon = float(req.longitude)
                if lon < -180 or lon > 180:
                    errors.append(toolkit._('Longitude must be between -180 and 180'))
            except (ValueError, TypeError):
                errors.append(toolkit._('Longitude must be a valid number'))

        return errors

    @staticmethod
    def _normalize_organizations(orgs):
        """Return organizations in a consistent dict format for templates and validation."""
        normalized = []
        for org in orgs:
            if isinstance(org, dict):
                org_id = org.get('id') or org.get('name')
                org_name = org.get('name') or org_id
                display_name = org.get('display_name') or org.get('title') or org_name
            else:
                org_id = getattr(org, 'id', None) or getattr(org, 'name', None) or str(org)
                org_name = getattr(org, 'name', None) or org_id
                display_name = getattr(org, 'display_name', None) or getattr(org, 'title', None) or org_name

            normalized.append({
                'id': org_id,
                'name': org_name,
                'title': display_name,
                'display_name': display_name,
            })

        return normalized

    @staticmethod
    def _allowed_organization_ids(orgs):
        allowed_ids = set()
        for org in orgs:
            org_id = org.get('id') or org.get('name')
            if org_id:
                allowed_ids.add(org_id)
        return allowed_ids

    @staticmethod
    def _populate_request_from_form(req, allowed_org_ids=None):
        """Populate a DeviceRequest from form data and return validation errors."""
        errors = []
        req.device_name = request.form.get('device_name', '').strip()
        req.device_label = request.form.get('device_label', '').strip()
        req.device_profile_name = request.form.get('device_profile_name', '').strip()
        req.serial_number = request.form.get('serial_number', '').strip()
        req.site_code = request.form.get('site_code', '').strip()
        req.installer_name = request.form.get('installer_name', '').strip()
        req.owner_name = request.form.get('owner_name', '').strip()
        req.firmware_version = request.form.get('firmware_version', '').strip()
        req.address = request.form.get('address', '').strip()
        req.technical_notes = request.form.get('technical_notes', '').strip()
        req.organization_id = request.form.get('organization_id', '').strip() or None
        if req.organization_id and allowed_org_ids is not None and req.organization_id not in allowed_org_ids:
            errors.append(toolkit._('Selected organization is not available for your user'))
        req.survey_completed = request.form.get('survey_completed') == 'on'

        # Install date
        install_date_str = request.form.get('install_date', '').strip()
        if install_date_str:
            try:
                req.install_date = datetime.strptime(install_date_str, '%Y-%m-%d').date()
            except ValueError:
                req.install_date = None
                errors.append(toolkit._('Install date must use the YYYY-MM-DD format'))
        else:
            req.install_date = None

        # Lat/lon
        lat_str = request.form.get('latitude', '').strip()
        lon_str = request.form.get('longitude', '').strip()
        try:
            req.latitude = float(lat_str) if lat_str else None
        except ValueError:
            req.latitude = None
            errors.append(toolkit._('Latitude must be a valid number'))
        try:
            req.longitude = float(lon_str) if lon_str else None
        except ValueError:
            req.longitude = None
            errors.append(toolkit._('Longitude must be a valid number'))

        req.updated_at = datetime.utcnow()
        return errors

    # ------------------------------------------------------------------
    # Helper: ensure table exists
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_table():
        try:
            dr_metadata.create_all(model.meta.engine, tables=[device_request_table])
        except Exception as e:
            log.debug(f'Table creation attempt: {e}')

    # ------------------------------------------------------------------
    # User routes
    # ------------------------------------------------------------------

    @staticmethod
    def user_dashboard():
        """List the current user's device requests."""
        ThingsBoardLogic._require_sysadmin()
        ThingsBoardLogic._ensure_table()

        try:
            requests_list = model.Session.query(DeviceRequest).filter(
                DeviceRequest.created_by_user_id == toolkit.g.userobj.id
            ).order_by(DeviceRequest.created_at.desc()).all()
        except Exception as e:
            log.error(f'Error loading device requests: {e}')
            requests_list = []

        return render_template('thingsboard/dashboard.html',
                               requests=requests_list,
                               current_user=toolkit.g.userobj.name)

    @staticmethod
    def new_request_form():
        """Show empty device request form."""
        ThingsBoardLogic._require_sysadmin()

        orgs = ThingsBoardLogic._get_user_organizations()
        return render_template('thingsboard/device_form.html',
                               device_request=None,
                               organizations=orgs,
                               errors=[],
                               current_user=toolkit.g.userobj.name)

    @staticmethod
    def create_request():
        """Create a new device request as DRAFT."""
        ThingsBoardLogic._require_sysadmin()
        ThingsBoardLogic._ensure_table()
        orgs = ThingsBoardLogic._get_user_organizations()
        allowed_org_ids = ThingsBoardLogic._allowed_organization_ids(orgs)

        try:
            dr = DeviceRequest(
                created_by_user_id=toolkit.g.userobj.id,
                status='DRAFT',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            errors = ThingsBoardLogic._populate_request_from_form(
                dr,
                allowed_org_ids=allowed_org_ids
            )
            if errors:
                return render_template('thingsboard/device_form.html',
                                       device_request=dr,
                                       organizations=orgs,
                                       errors=errors,
                                       current_user=toolkit.g.userobj.name)

            model.Session.add(dr)
            model.Session.commit()

            toolkit.h.flash_success(toolkit._('Device request saved as draft'))
            return toolkit.redirect_to('thingsboard.edit_request', id=dr.id)
        except Exception as e:
            model.Session.rollback()
            log.error(f'Error creating device request: {e}')
            return render_template('thingsboard/device_form.html',
                                   device_request=dr if 'dr' in locals() else None,
                                   organizations=orgs,
                                   errors=['An error occurred while saving the request'],
                                   current_user=toolkit.g.userobj.name)

    @staticmethod
    def edit_request_form(id):
        """Show edit form for a draft or rejected request."""
        ThingsBoardLogic._require_sysadmin()
        ThingsBoardLogic._ensure_table()

        dr = model.Session.query(DeviceRequest).get(id)
        if not dr:
            toolkit.abort(404, toolkit._('Device request not found'))
        if dr.created_by_user_id != toolkit.g.userobj.id:
            toolkit.abort(403, toolkit._('You can only edit your own requests'))
        if dr.status not in ('DRAFT', 'REJECTED'):
            toolkit.abort(403, toolkit._('This request can no longer be edited'))

        orgs = ThingsBoardLogic._get_user_organizations()
        return render_template('thingsboard/device_form.html',
                               device_request=dr,
                               organizations=orgs,
                               errors=[],
                               current_user=toolkit.g.userobj.name)

    @staticmethod
    def update_request(id):
        """Update an existing draft or rejected request."""
        ThingsBoardLogic._require_sysadmin()
        ThingsBoardLogic._ensure_table()
        orgs = ThingsBoardLogic._get_user_organizations()
        allowed_org_ids = ThingsBoardLogic._allowed_organization_ids(orgs)

        dr = model.Session.query(DeviceRequest).get(id)
        if not dr:
            toolkit.abort(404, toolkit._('Device request not found'))
        if dr.created_by_user_id != toolkit.g.userobj.id:
            toolkit.abort(403, toolkit._('You can only edit your own requests'))
        if dr.status not in ('DRAFT', 'REJECTED'):
            toolkit.abort(403, toolkit._('This request can no longer be edited'))

        try:
            errors = ThingsBoardLogic._populate_request_from_form(
                dr,
                allowed_org_ids=allowed_org_ids
            )
            if errors:
                return render_template('thingsboard/device_form.html',
                                       device_request=dr,
                                       organizations=orgs,
                                       errors=errors,
                                       current_user=toolkit.g.userobj.name)
            if dr.status == 'REJECTED':
                dr.status = 'DRAFT'
                dr.rejection_reason = None
                dr.rejected_at = None
            model.Session.commit()
            toolkit.h.flash_success(toolkit._('Device request updated'))
            return toolkit.redirect_to('thingsboard.edit_request', id=dr.id)
        except Exception as e:
            model.Session.rollback()
            log.error(f'Error updating device request: {e}')
            return render_template('thingsboard/device_form.html',
                                   device_request=dr,
                                   organizations=orgs,
                                   errors=['An error occurred while updating the request'],
                                   current_user=toolkit.g.userobj.name)

    @staticmethod
    def submit_request(id):
        """Validate and submit a device request for review."""
        ThingsBoardLogic._require_sysadmin()
        ThingsBoardLogic._ensure_table()
        orgs = ThingsBoardLogic._get_user_organizations()
        allowed_org_ids = ThingsBoardLogic._allowed_organization_ids(orgs)

        dr = model.Session.query(DeviceRequest).get(id)
        if not dr:
            toolkit.abort(404, toolkit._('Device request not found'))
        if dr.created_by_user_id != toolkit.g.userobj.id:
            toolkit.abort(403, toolkit._('You can only submit your own requests'))
        if dr.status not in ('DRAFT', 'REJECTED'):
            toolkit.abort(403, toolkit._('This request cannot be submitted'))

        form_errors = ThingsBoardLogic._populate_request_from_form(
            dr,
            allowed_org_ids=allowed_org_ids
        )
        errors = form_errors + ThingsBoardLogic._validate_for_submission(dr, request_id=dr.id)
        if errors:
            return render_template('thingsboard/device_form.html',
                                   device_request=dr,
                                   organizations=orgs,
                                   errors=errors,
                                   current_user=toolkit.g.userobj.name)

        try:
            if dr.status == 'REJECTED':
                dr.rejection_reason = None
                dr.rejected_at = None
                dr.reviewed_by_user_id = None
                dr.reviewed_at = None
            dr.status = 'SUBMITTED'
            dr.submitted_at = datetime.utcnow()
            dr.updated_at = datetime.utcnow()
            model.Session.commit()

            # Send email notification
            try:
                from ckanext.colab.lib.device_email_notifications import send_device_submission_notification
                send_device_submission_notification(dr, toolkit.g.userobj.display_name)
            except Exception as e:
                log.error(f'Error sending device submission notification: {e}')

            toolkit.h.flash_success(toolkit._('Device request submitted for review'))
            return toolkit.redirect_to('thingsboard.dashboard')
        except Exception as e:
            model.Session.rollback()
            log.error(f'Error submitting device request: {e}')
            return render_template('thingsboard/device_form.html',
                                   device_request=dr,
                                   organizations=orgs,
                                   errors=['An error occurred while submitting the request'],
                                   current_user=toolkit.g.userobj.name)

    # ------------------------------------------------------------------
    # Admin routes
    # ------------------------------------------------------------------

    @staticmethod
    def admin_dashboard():
        """Admin dashboard with all device requests."""
        ThingsBoardLogic._require_sysadmin()
        ThingsBoardLogic._ensure_table()

        try:
            all_requests = model.Session.query(DeviceRequest).order_by(
                DeviceRequest.created_at.desc()
            ).all()
        except Exception as e:
            log.error(f'Error loading device requests: {e}')
            all_requests = []

        # Group by status
        pending = [r for r in all_requests if r.status in ('SUBMITTED', 'UNDER_REVIEW')]
        approved = [r for r in all_requests if r.status == 'APPROVED']
        rejected = [r for r in all_requests if r.status == 'REJECTED']
        synced = [r for r in all_requests if r.status == 'SYNCED' or r.sync_status == 'synced']
        sync_errors = [r for r in all_requests if r.sync_status == 'error']
        drafts = [r for r in all_requests if r.status == 'DRAFT']

        return render_template('thingsboard/admin_dashboard.html',
                               pending=pending,
                               approved=approved,
                               rejected=rejected,
                               synced=synced,
                               sync_errors=sync_errors,
                               drafts=drafts,
                               current_user=toolkit.g.userobj.name)

    @staticmethod
    def admin_detail(id):
        """Admin detail view for a device request."""
        ThingsBoardLogic._require_sysadmin()
        ThingsBoardLogic._ensure_table()

        dr = model.Session.query(DeviceRequest).get(id)
        if not dr:
            toolkit.abort(404, toolkit._('Device request not found'))

        # Resolve user names
        creator = model.User.get(dr.created_by_user_id)
        reviewer = model.User.get(dr.reviewed_by_user_id) if dr.reviewed_by_user_id else None

        # Resolve organization name
        org_name = None
        if dr.organization_id:
            org = model.Group.get(dr.organization_id)
            org_name = org.title if org else dr.organization_id

        return render_template('thingsboard/admin_detail.html',
                               dr=dr,
                               creator=creator,
                               reviewer=reviewer,
                               org_name=org_name,
                               current_user=toolkit.g.userobj.name)

    @staticmethod
    def approve_request(id):
        """Approve a device request and sync to ThingsBoard."""
        ThingsBoardLogic._require_sysadmin()
        ThingsBoardLogic._ensure_table()

        dr = model.Session.query(DeviceRequest).get(id)
        if not dr:
            toolkit.abort(404, toolkit._('Device request not found'))
        if dr.status not in ('SUBMITTED', 'UNDER_REVIEW'):
            toolkit.h.flash_error(toolkit._('This request cannot be approved in its current state'))
            return toolkit.redirect_to('thingsboard.admin_detail', id=id)

        # Validate required fields
        errors = ThingsBoardLogic._validate_for_submission(dr, request_id=dr.id)
        if errors:
            toolkit.h.flash_error(toolkit._('Cannot approve: %(errors)s') % {'errors': ", ".join(errors)})
            return toolkit.redirect_to('thingsboard.admin_detail', id=id)

        try:
            dr.status = 'APPROVED'
            dr.reviewed_by_user_id = toolkit.g.userobj.id
            dr.reviewed_at = datetime.utcnow()
            dr.approved_at = datetime.utcnow()
            dr.sync_status = 'pending'
            dr.updated_at = datetime.utcnow()
            model.Session.commit()
        except Exception as e:
            model.Session.rollback()
            log.error(f'Error approving device request: {e}')
            toolkit.h.flash_error(toolkit._('Error approving request'))
            return toolkit.redirect_to('thingsboard.admin_detail', id=id)

        # Sync to ThingsBoard
        try:
            from ckanext.colab.services.thingsboard_service import ThingsBoardService, ThingsBoardSyncError
            tb = ThingsBoardService()
            tb_device_id, tb_customer_id, tb_access_token = tb.provision_device(dr)

            dr.tb_device_id = tb_device_id
            dr.tb_customer_id = tb_customer_id
            dr.tb_access_token = tb_access_token
            dr.sync_status = 'synced'
            dr.sync_error_message = None
            dr.updated_at = datetime.utcnow()
            model.Session.commit()

            toolkit.h.flash_success(toolkit._('Device request approved and synced to ThingsBoard'))
        except Exception as e:
            dr.sync_status = 'error'
            dr.sync_error_message = str(e)
            dr.updated_at = datetime.utcnow()
            model.Session.commit()
            log.error(f'ThingsBoard sync error for request {id}: {e}')
            toolkit.h.flash_error(toolkit._('Request approved but sync failed: %(error)s') % {'error': e})

        return toolkit.redirect_to('thingsboard.admin_detail', id=id)

    @staticmethod
    def reject_request(id):
        """Reject a device request."""
        ThingsBoardLogic._require_sysadmin()
        ThingsBoardLogic._ensure_table()

        dr = model.Session.query(DeviceRequest).get(id)
        if not dr:
            toolkit.abort(404, toolkit._('Device request not found'))
        if dr.status not in ('SUBMITTED', 'UNDER_REVIEW'):
            toolkit.h.flash_error(toolkit._('This request cannot be rejected in its current state'))
            return toolkit.redirect_to('thingsboard.admin_detail', id=id)

        reason = request.form.get('rejection_reason', '').strip()
        if not reason:
            toolkit.h.flash_error(toolkit._('Rejection reason is required'))
            return toolkit.redirect_to('thingsboard.admin_detail', id=id)

        try:
            dr.status = 'REJECTED'
            dr.reviewed_by_user_id = toolkit.g.userobj.id
            dr.reviewed_at = datetime.utcnow()
            dr.rejected_at = datetime.utcnow()
            dr.rejection_reason = reason
            dr.updated_at = datetime.utcnow()
            model.Session.commit()

            toolkit.h.flash_success(toolkit._('Device request rejected'))
        except Exception as e:
            model.Session.rollback()
            log.error(f'Error rejecting device request: {e}')
            toolkit.h.flash_error(toolkit._('Error rejecting request'))

        return toolkit.redirect_to('thingsboard.admin_dashboard')

    @staticmethod
    def retry_sync(id):
        """Retry ThingsBoard sync for a failed request."""
        ThingsBoardLogic._require_sysadmin()
        ThingsBoardLogic._ensure_table()

        dr = model.Session.query(DeviceRequest).get(id)
        if not dr:
            toolkit.abort(404, toolkit._('Device request not found'))
        if dr.sync_status != 'error':
            toolkit.h.flash_error(toolkit._('Only requests with sync errors can be retried'))
            return toolkit.redirect_to('thingsboard.admin_detail', id=id)

        # Don't re-create if already exists in TB
        if dr.tb_device_id:
            toolkit.h.flash_error(toolkit._('Device already exists in ThingsBoard. Manual intervention required.'))
            return toolkit.redirect_to('thingsboard.admin_detail', id=id)

        try:
            from ckanext.colab.services.thingsboard_service import ThingsBoardService
            tb = ThingsBoardService()
            tb_device_id, tb_customer_id, tb_access_token = tb.provision_device(dr)

            dr.tb_device_id = tb_device_id
            dr.tb_customer_id = tb_customer_id
            dr.tb_access_token = tb_access_token
            dr.sync_status = 'synced'
            dr.sync_error_message = None
            dr.updated_at = datetime.utcnow()
            model.Session.commit()

            toolkit.h.flash_success(toolkit._('Device successfully synced to ThingsBoard'))
        except Exception as e:
            dr.sync_status = 'error'
            dr.sync_error_message = str(e)
            dr.updated_at = datetime.utcnow()
            model.Session.commit()
            log.error(f'ThingsBoard retry sync error for request {id}: {e}')
            toolkit.h.flash_error(toolkit._('Sync retry failed: %(error)s') % {'error': e})

        return toolkit.redirect_to('thingsboard.admin_detail', id=id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_user_organizations():
        """Get organizations the current user belongs to."""
        try:
            orgs = toolkit.get_action('organization_list_for_user')(
                {'user': toolkit.g.user},
                {'permission': 'read'}
            )
            return ThingsBoardLogic._normalize_organizations(orgs)
        except Exception:
            return []
