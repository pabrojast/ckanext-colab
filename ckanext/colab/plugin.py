import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.model as model
from ckan.lib.plugins import DefaultTranslation
from flask import Blueprint
from ckanext.colab.controller import MyLogic


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

        blueprint.add_url_rule(
            u'/colab/admin/reject/<name>/<organization>/<reason>',
            u'reject',
            MyLogic.reject,
            methods=['GET']
        )

        return blueprint
    

    #ITemplateHelpers

    def get_helpers(self):
        return {
            'get_site_key': lambda: toolkit.config.get('ckan.recaptcha.publickey')
        }