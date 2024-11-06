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
