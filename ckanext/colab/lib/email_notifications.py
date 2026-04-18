import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from ckan.common import config
from ckan.lib.base import render
from ckan.lib import mailer
from ckan import model

log = logging.getLogger(__name__)

def get_admin_notification_body(user_data):
    """Genera el cuerpo del correo de notificación"""
    extra_vars = {
        'site_title': config.get('ckan.site_title'),
        'site_url': config.get('ckan.site_url'),
        'user_data': user_data
    }
    return render('email/admin_notification.txt', extra_vars)

def send_admin_notification(user_data):
    """Envía la notificación por correo a los administradores"""
    try:
        # Obtener todos los usuarios admin del sistema usando la sesión de modelo
        admin_users = model.Session.query(model.User).filter(
            model.User.sysadmin == True,
            model.User.state == 'active'
        ).all()
        
        if not admin_users:
            log.warning('No system administrators found')
            return

        body = get_admin_notification_body(user_data)
        subject = f"[{config.get('ckan.site_title')}] New User Registration"

        for admin in admin_users:
            if admin.email:
                # Usar el mailer de CKAN para enviar el correo
                mailer.mail_user(
                    admin,
                    subject,
                    body
                )
                
    except Exception as e:
        log.error(f'Error sending admin notification email: {str(e)}')


def send_applicant_confirmation(application):
    """Send confirmation email to the applicant after registration submission."""
    try:
        if not application or not application.email:
            log.warning('No email address for applicant confirmation')
            return

        site_title = config.get('ckan.site_title', 'IHP-WINS')
        site_url = config.get('ckan.site_url', '')
        status_url = f"{site_url}/colab/status"

        body = f"""Dear {application.fullname},

Thank you for submitting your registration to {site_title}.

Your application has been received and is now pending review by our team.

Application details:
  - Username: {application.wins_username}
  - Email: {application.email}
  - Organization: {application.organization_name}
  - Role requested: {application.user_role or 'admin'}

You can check the status of your application at any time:
  {status_url}

Our team will review your application and you will receive an email notification once a decision has been made.

If you have questions, please contact: ihp-wins@unesco.org

Best regards,
{site_title} Team
"""
        subject = f"[{site_title}] Registration received - pending review"

        # Create a temporary user-like object for CKAN's mailer
        temp_user = type('obj', (object,), {
            'email': application.email,
            'name': application.wins_username,
            'display_name': application.fullname
        })

        mailer.mail_user(temp_user, subject, body)
        log.info(f"Applicant confirmation email sent to {application.email}")

    except Exception as e:
        log.error(f'Error sending applicant confirmation email: {str(e)}')
