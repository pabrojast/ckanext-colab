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
    #plugins.implements(plugins.ITemplateHelpers)

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
        # blueprint.add_url_rule(
        #     u'/cool_plugin/add',
        #     u'add',
        #     MyLogic.add,
        #     methods=['GET']
        # )

        # blueprint.add_url_rule(
        #     u'/cool_plugin/get',
        #     u'get',
        #     MyLogic.get,
        #     methods=['GET']
        # )

        # blueprint.add_url_rule(
        #     u'/cool_plugin/update',
        #     u'update',
        #     MyLogic.update,
        #     methods=['GET']
        # )

        # blueprint.add_url_rule(
        #     u'/cool_plugin/delete',
        #     u'delete',
        #     MyLogic.delete,
        #     methods=['GET']
        # )

        # blueprint.add_url_rule(
        #     u'/cool_plugin/do_something/<name>',
        #     u'do_something',
        #     MyLogic.do_something,
        #     methods=['GET']
        # )

        # blueprint.add_url_rule(
        #     u'/cool_plugin/only_admin_can_access_me',
        #     u'only_admin_can_access_me',
        #     MyLogic.only_admin_can_access_me,
        #     methods=['POST']
        # )


        return blueprint
    

    #ITemplateHelpers

    # def get_helpers(self):
    #     return {'help_me': MyLogic.help_it}