import os
import logging
import requests

log = logging.getLogger(__name__)


class ThingsBoardError(Exception):
    """Base exception for ThingsBoard operations."""
    pass


class ThingsBoardAuthError(ThingsBoardError):
    """Authentication failure with ThingsBoard."""
    pass


class ThingsBoardSyncError(ThingsBoardError):
    """Failed to sync a device to ThingsBoard."""
    pass


class ThingsBoardService:
    """REST API client for ThingsBoard using API Key authentication.

    Configuration via environment variables:
        TB_URL       - Base URL (default: https://tb.ihp-wins.unesco.org)
        TB_API_KEY   - API key created in ThingsBoard UI (API keys tab)

    The API key is long-lived and does not require login or token refresh.
    Include it in every request as: X-Authorization: ApiKey <key>
    """

    def __init__(self):
        self.base_url = os.environ.get('TB_URL', 'https://tb.ihp-wins.unesco.org').rstrip('/')
        self.api_key = os.environ.get('TB_API_KEY')
        if not self.api_key:
            raise ThingsBoardAuthError(
                'TB_API_KEY environment variable is required. '
                'Create an API key in ThingsBoard UI under the API keys tab.'
            )

    # ------------------------------------------------------------------
    # HTTP helper
    # ------------------------------------------------------------------

    def _request(self, method, path, data=None, params=None):
        """Make an authenticated request to the ThingsBoard API."""
        url = f'{self.base_url}{path}'
        headers = {
            'Content-Type': 'application/json',
            'X-Authorization': f'ApiKey {self.api_key}'
        }
        try:
            resp = requests.request(
                method, url, json=data, params=params,
                headers=headers, timeout=30
            )
        except requests.RequestException as e:
            raise ThingsBoardSyncError(f'Connection error: {e}')

        if resp.status_code == 401:
            raise ThingsBoardAuthError(
                'API key authentication failed (HTTP 401). '
                'Verify TB_API_KEY is valid and not expired.'
            )

        if resp.status_code >= 400:
            raise ThingsBoardSyncError(
                f'TB API error {method} {path} (HTTP {resp.status_code}): {resp.text}'
            )
        # Some endpoints return 200 with empty body
        if resp.content:
            return resp.json()
        return None

    # ------------------------------------------------------------------
    # Customer operations
    # ------------------------------------------------------------------

    def find_customer_by_title(self, title):
        """Search for a customer by title. Returns customer dict or None."""
        data = self._request('GET', '/api/customers', params={
            'pageSize': 100,
            'page': 0,
            'textSearch': title
        })
        if data and data.get('data'):
            for customer in data['data']:
                if customer.get('title', '').lower() == title.lower():
                    return customer
        return None

    def create_customer(self, title):
        """Create a new customer. Returns customer dict."""
        return self._request('POST', '/api/customer', data={
            'title': title
        })

    def find_or_create_customer(self, org_name):
        """Find existing customer by organization name or create one."""
        customer = self.find_customer_by_title(org_name)
        if customer:
            log.info(f'Found existing TB customer: {org_name} ({customer["id"]["id"]})')
            return customer
        customer = self.create_customer(org_name)
        log.info(f'Created TB customer: {org_name} ({customer["id"]["id"]})')
        return customer

    # ------------------------------------------------------------------
    # Device operations
    # ------------------------------------------------------------------

    def create_device(self, device_name, device_label=None, device_profile_name=None):
        """Create a device in ThingsBoard. Returns device dict."""
        payload = {
            'name': device_name,
            'label': device_label or device_name,
        }
        if device_profile_name:
            # Look up the device profile by name
            profile = self._find_device_profile(device_profile_name)
            if profile:
                payload['deviceProfileId'] = profile['id']

        return self._request('POST', '/api/device', data=payload)

    def _find_device_profile(self, profile_name):
        """Find a device profile by name. Returns profile dict or None."""
        data = self._request('GET', '/api/deviceProfiles', params={
            'pageSize': 100,
            'page': 0,
            'textSearch': profile_name
        })
        if data and data.get('data'):
            for profile in data['data']:
                if profile.get('name', '').lower() == profile_name.lower():
                    return profile
        return None

    def assign_device_to_customer(self, device_id, customer_id):
        """Assign a device to a customer."""
        return self._request(
            'POST',
            f'/api/customer/{customer_id}/device/{device_id}'
        )

    def get_device_credentials(self, device_id):
        """Get the access token for a device."""
        return self._request('GET', f'/api/device/{device_id}/credentials')

    def save_device_attributes(self, device_id, attributes):
        """Save server-side attributes for a device."""
        return self._request(
            'POST',
            f'/api/plugins/telemetry/DEVICE/{device_id}/attributes/SERVER_SCOPE',
            data=attributes
        )

    # ------------------------------------------------------------------
    # Orchestrator
    # ------------------------------------------------------------------

    def provision_device(self, device_request):
        """Full provisioning workflow for an approved device request.

        Args:
            device_request: DeviceRequest model instance with all fields populated.

        Returns:
            tuple: (tb_device_id, tb_customer_id, tb_access_token)

        Raises:
            ThingsBoardSyncError: If any step fails.
        """
        try:
            # 1. Find or create customer from organization
            tb_customer = None
            tb_customer_id = None
            if device_request.organization_id:
                from ckan import model as ckan_model
                org = ckan_model.Group.get(device_request.organization_id)
                org_name = org.title if org else device_request.organization_id
                tb_customer = self.find_or_create_customer(org_name)
                tb_customer_id = tb_customer['id']['id']

            # 2. Create device
            tb_device = self.create_device(
                device_name=device_request.device_name,
                device_label=device_request.device_label,
                device_profile_name=device_request.device_profile_name
            )
            tb_device_id = tb_device['id']['id']
            log.info(f'Created TB device: {device_request.device_name} ({tb_device_id})')

            # 3. Assign to customer if applicable
            if tb_customer_id:
                self.assign_device_to_customer(tb_device_id, tb_customer_id)
                log.info(f'Assigned device {tb_device_id} to customer {tb_customer_id}')

            # 4. Save server-side attributes
            attributes = {
                'serialNumber': device_request.serial_number,
                'siteCode': device_request.site_code,
                'installer': device_request.installer_name,
                'installDate': str(device_request.install_date) if device_request.install_date else None,
                'owner': device_request.owner_name,
                'firmwareVersion': device_request.firmware_version,
                'surveyCompleted': bool(device_request.survey_completed),
                'approvedBySiteAdmin': True,
                'externalRequestId': device_request.id,
            }
            if device_request.latitude is not None and device_request.longitude is not None:
                attributes['latitude'] = device_request.latitude
                attributes['longitude'] = device_request.longitude
                if device_request.address:
                    attributes['address'] = device_request.address

            # Remove None values
            attributes = {k: v for k, v in attributes.items() if v is not None}
            self.save_device_attributes(tb_device_id, attributes)
            log.info(f'Saved attributes for device {tb_device_id}')

            # 5. Get device credentials (access token)
            credentials = self.get_device_credentials(tb_device_id)
            tb_access_token = credentials.get('credentialsId', '') if credentials else ''

            return tb_device_id, tb_customer_id, tb_access_token

        except ThingsBoardError:
            raise
        except Exception as e:
            raise ThingsBoardSyncError(f'Unexpected error during provisioning: {e}')
