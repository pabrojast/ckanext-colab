import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.model as model
from ckan.lib.plugins import DefaultTranslation
from flask import Blueprint
from ckanext.colab.controller import MyLogic
from ckanext.colab.models.cool_plugin_table import CoolPluginTable
from ckanext.colab.controllers.thingsboard_controller import ThingsBoardLogic
from ckanext.colab.models.device_request import DeviceRequest


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

        blueprint = Blueprint('colab', self.__module__)        
       
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

        # Keep the parameterized legacy route, but do not allow state changes via GET.
        blueprint.add_url_rule(
            u'/colab/admin/approve/<name>/<organization>/<new>/<new_organization_description>',
            u'approve',
            MyLogic.approve,
            methods=['POST']
        )

        blueprint.add_url_rule(
            u'/colab/admin/approvegroup/<name>/<new>/<group>/<new_group_description>',
            u'approvegroup',
            MyLogic.approvegroup,
            methods=['POST']
        )

        blueprint.add_url_rule(
            u'/colab/admin/reject',
            u'reject_post',
            MyLogic.reject_post,
            methods=['POST']
        )

        blueprint.add_url_rule(
            u'/colab/admin/reject/<name>/<organization>/<reason>',
            u'reject',
            MyLogic.reject,
            methods=['POST']
        )

        blueprint.add_url_rule(
            u'/colab/admin/delete',
            u'delete_application',
            MyLogic.delete_application,
            methods=['POST']
        )

        blueprint.add_url_rule(
            u'/colab/admin/restore',
            u'restore_application',
            MyLogic.restore_application,
            methods=['POST']
        )

        blueprint.add_url_rule(
            u'/colab/admin/note',
            u'save_admin_note',
            MyLogic.save_admin_note,
            methods=['POST']
        )

        blueprint.add_url_rule(
            u'/colab/admin/export',
            u'export_csv',
            MyLogic.export_csv,
            methods=['GET']
        )

        blueprint.add_url_rule(
            u'/colab/admin/bulk',
            u'bulk_action',
            MyLogic.bulk_action,
            methods=['POST']
        )

        # Application status check
        blueprint.add_url_rule(
            u'/colab/status',
            u'check_status',
            MyLogic.check_status,
            methods=['GET', 'POST']
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

        # ThingsBoard device management blueprint
        tb_blueprint = Blueprint('thingsboard', self.__module__,
                                 url_prefix='/thingsboard')

        # User routes
        tb_blueprint.add_url_rule(
            u'/',
            u'dashboard',
            ThingsBoardLogic.user_dashboard,
            methods=['GET']
        )
        tb_blueprint.add_url_rule(
            u'/request/new',
            u'new_request',
            ThingsBoardLogic.new_request_form,
            methods=['GET']
        )
        tb_blueprint.add_url_rule(
            u'/request',
            u'create_request',
            ThingsBoardLogic.create_request,
            methods=['POST']
        )
        tb_blueprint.add_url_rule(
            u'/request/<int:id>/edit',
            u'edit_request',
            ThingsBoardLogic.edit_request_form,
            methods=['GET']
        )
        tb_blueprint.add_url_rule(
            u'/request/<int:id>/update',
            u'update_request',
            ThingsBoardLogic.update_request,
            methods=['POST']
        )
        tb_blueprint.add_url_rule(
            u'/request/<int:id>/submit',
            u'submit_request',
            ThingsBoardLogic.submit_request,
            methods=['POST']
        )

        # Admin routes
        tb_blueprint.add_url_rule(
            u'/admin',
            u'admin_dashboard',
            ThingsBoardLogic.admin_dashboard,
            methods=['GET']
        )
        tb_blueprint.add_url_rule(
            u'/admin/request/<int:id>',
            u'admin_detail',
            ThingsBoardLogic.admin_detail,
            methods=['GET']
        )
        tb_blueprint.add_url_rule(
            u'/admin/request/<int:id>/approve',
            u'approve',
            ThingsBoardLogic.approve_request,
            methods=['POST']
        )
        tb_blueprint.add_url_rule(
            u'/admin/request/<int:id>/reject',
            u'reject',
            ThingsBoardLogic.reject_request,
            methods=['POST']
        )
        tb_blueprint.add_url_rule(
            u'/admin/request/<int:id>/retry-sync',
            u'retry_sync',
            ThingsBoardLogic.retry_sync,
            methods=['POST']
        )

        return [blueprint, tb_blueprint]
    

    #ITemplateHelpers

    def get_helpers(self):
        return {
            'get_site_key': lambda: toolkit.config.get('ckan.recaptcha.publickey'),
            'colab_image_url': self._colab_image_url,
            'colab_pending_count': self._colab_pending_count,
            'tb_pending_count': self._tb_pending_count,
        }

    def _colab_pending_count(self):
        """Return the number of pending user approval requests."""
        try:
            count = model.Session.query(CoolPluginTable).filter(
                CoolPluginTable.approved == 'Pending',
                CoolPluginTable.rejected.is_(None),
                CoolPluginTable.deleted_at.is_(None)
            ).count()
            return count
        except Exception:
            return 0

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

    def _tb_pending_count(self):
        """Return the number of pending device request approvals."""
        try:
            count = model.Session.query(DeviceRequest).filter(
                DeviceRequest.status.in_(['SUBMITTED', 'UNDER_REVIEW'])
            ).count()
            return count
        except Exception:
            return 0
