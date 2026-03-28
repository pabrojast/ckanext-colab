import logging
from ckan.common import config
from ckan.lib.base import render
from ckan.lib import mailer
from ckan import model

log = logging.getLogger(__name__)


def get_device_notification_body(device_request, submitter_name):
    """Generate the email body for a device request submission notification."""
    extra_vars = {
        'site_title': config.get('ckan.site_title'),
        'site_url': config.get('ckan.site_url'),
        'device_request': device_request,
        'submitter_name': submitter_name
    }
    return render('thingsboard/email/device_submission.txt', extra_vars)


def send_device_submission_notification(device_request, submitter_name):
    """Send notification to all sysadmins when a device request is submitted."""
    try:
        admin_users = model.Session.query(model.User).filter(
            model.User.sysadmin == True,
            model.User.state == 'active'
        ).all()

        if not admin_users:
            log.warning('No system administrators found for device notification')
            return

        body = get_device_notification_body(device_request, submitter_name)
        subject = f"[{config.get('ckan.site_title')}] New Device Registration Request"

        for admin in admin_users:
            if admin.email:
                mailer.mail_user(admin, subject, body)

    except Exception as e:
        log.error(f'Error sending device submission notification: {e}')
