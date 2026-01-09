import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.model as model
from ckan.lib.plugins import DefaultTranslation
from flask import Blueprint
from ckanext.colab.controller import MyLogic
import logging


log = logging.getLogger(__name__)


class ColabPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.ITranslation)   # Implementar ITemplateHelpers
    plugins.implements(plugins.ITemplateHelpers)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates/colab_temp')
        toolkit.add_public_directory(config_, 'public/colab_static')
        toolkit.add_resource('public/colab_static', 'ckanext-colab-plugin')

    def get_blueprint(self):

        blueprint = Blueprint(self.name, self.__module__)        
       
        blueprint.add_url_rule(
            u'/colab',
            u'show_something',
            MyLogic.show_something,
            methods=['GET', 'POST']
        )

        blueprint.add_url_rule(
            u'/colab/admin',
            u'show_admin',
            MyLogic.show_admin,
            methods=['GET']
        )

        # New POST route for approve
        blueprint.add_url_rule(
            u'/colab/admin/approve',
            u'approve_post',
            MyLogic.approve_post,
            methods=['POST']
        )

        # Keep the old GET route for backward compatibility
        blueprint.add_url_rule(
            u'/colab/admin/approve/<name>/<organization>/<new>/<new_organization_description>',
            u'approve',
            MyLogic.approve,
            methods=['GET']
        )

        blueprint.add_url_rule(
            u'/colab/admin/approvegroup/<name>/<new>/<group>/<new_group_description>',
            u'approvegroup',
            MyLogic.approvegroup,
            methods=['GET']
        )

        # Legacy GET route for backward compatibility - deprecated
        blueprint.add_url_rule(
            u'/colab/admin/reject/<name>/<organization>/<reason>',
            u'reject',
            MyLogic.reject,
            methods=['GET']
        )

        # New POST route for reject with CSRF protection
        blueprint.add_url_rule(
            u'/colab/admin/reject',
            u'reject_post',
            MyLogic.reject_post,
            methods=['POST']
        )

        # Organization request routes
        blueprint.add_url_rule(
            u'/colab/organization-request',
            u'organization_request_form',
            MyLogic.show_organization_request_form,
            methods=['GET']
        )

        blueprint.add_url_rule(
            u'/colab/organization-request',
            u'submit_organization_request',
            MyLogic.submit_organization_request,
            methods=['POST']
        )

        blueprint.add_url_rule(
            u'/colab/admin/organizations',
            u'organization_admin',
            MyLogic.show_organization_admin,
            methods=['GET']
        )

        blueprint.add_url_rule(
            u'/colab/admin/organizations/approve',
            u'approve_organization_request',
            MyLogic.approve_organization_request,
            methods=['POST']
        )

        blueprint.add_url_rule(
            u'/colab/admin/organizations/reject',
            u'reject_organization_request',
            MyLogic.reject_organization_request,
            methods=['POST']
        )

        return blueprint
    

    #ITemplateHelpers

    def get_helpers(self):
        return {
            'get_site_key': lambda: toolkit.config.get('ckan.recaptcha.publickey'),
            'colab_image_url': self._colab_image_url,
            'get_csrf_token': self._get_csrf_token
        }

    def _colab_image_url(self, image_path):
        """Generate full URL for colab organization images"""
        if not image_path:
            return ''
        
        # If it's already a full URL, return as is
        if image_path.startswith(('http://', 'https://', '/')):
            return image_path
            
        # Generate the full URL using CKAN's helper (using page_images namespace for Azure compatibility)
        return toolkit.h.url_for_static(
            'uploads/page_images/%s' % image_path,
            qualified=True
        )

    def _get_csrf_token(self):
        """
        Return a CSRF token compatible with CKAN's validation helper.
        Attempts CKAN's internal generators first and falls back to Flask-WTF.
        """
        try:
            from ckan.lib import csrf_token  # CKAN >= 2.9
            for attr in ('_get_or_create_token', 'get_or_create_token', 'get_token', 'get_csrf_token'):
                getter = getattr(csrf_token, attr, None)
                if callable(getter):
                    return getter()
        except Exception as e:
            log.warning("Could not get CSRF token from CKAN helpers: %s", e)

        # Fallback to any token already on the request
        token = getattr(toolkit.request, 'csrf_token', None)
        if token:
            return token

        try:
            from flask_wtf.csrf import generate_csrf
            return generate_csrf()
        except Exception as e:
            log.error("CSRF token generation failed: %s", e)
            return ''
