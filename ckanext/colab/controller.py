from random import random
from flask import render_template, request, abort
import ckan.plugins.toolkit as toolkit
import ckan.model as model
import ckan.logic as logic
from ckanext.colab.models.cool_plugin_table import CoolPluginTable
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import re 
import json 
import logging
from ckanext.colab.lib.email_notifications import send_admin_notification
import requests

# Logging configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

Base = declarative_base()

def verify_recaptcha(recaptcha_response):
    """Verify the reCAPTCHA response"""
    secret_key = toolkit.config.get('ckan.recaptcha.privatekey')
    verify_url = 'https://www.google.com/recaptcha/api/siteverify'
    
    data = {
        'secret': secret_key,
        'response': recaptcha_response
    }
    
    response = requests.post(verify_url, data=data)
    result = response.json()
    
    return result.get('success', False) and result.get('score', 0) > 0.5

class MyLogic():

    def approvegroup(name, new, group, new_group_description):
        #u'/colab/admin/approvegroup/<name>/<group>/<new>/<new_group_description>',
        # ckan.logic.action.create.group_create(context, data_dict)
        # Create a new group.

        # You must be authorized to create groups.

        # Plugins may change the parameters of this function depending on the value of the type parameter, see the IGroupForm plugin interface.

        # Parameters:	
        # name (string) – the name of the group, a string between 2 and 100 characters long, containing only lowercase alphanumeric characters, - and _
        # id (string) – the id of the group (optional)
        # title (string) – the title of the group (optional)
        # description (string) – the description of the group (optional)
        # image_url (string) – the URL to an image to be displayed on the group's page (optional)
        # type (string) – the type of the group (optional, default: 'group'), IGroupForm plugins associate themselves with different group types and provide custom group handling behaviour for these types Cannot be 'organization'
        # state (string) – the current state of the group, e.g. 'active' or 'deleted', only active groups show up in search results and other lists of groups, this parameter will be ignored if you are not authorized to change the state of the group (optional, default: 'active')
        # approval_status (string) – (optional)
        # extras (list of dataset extra dictionaries) – the group's extras (optional), extras are arbitrary (key: value) metadata items that can be added to groups, each extra dictionary should have keys 'key' (a string), 'value' (a string), and optionally 'deleted'
        # packages (list of dictionaries) – the datasets (packages) that belong to the group, a list of dictionaries each with keys 'name' (string, the id or name of the dataset) and optionally 'title' (string, the title of the dataset)
        # groups (list of dictionaries) – the groups that belong to the group, a list of dictionaries each with key 'name' (string, the id or name of the group) and optionally 'capacity' (string, the capacity in which the group is a member of the group)
        # users (list of dictionaries) – the users that belong to the group, a list of dictionaries each with key 'name' (string, the id or name of the user) and optionally 'capacity' (string, the capacity in which the user is a member of the group)
        # Returns:	
        # the newly created group (unless 'return_id_only' is set to True in the context, in which case just the group id will be returned)

        # Return type:	
        # dictionary
        try:
            context = {'model': model, 'user': toolkit.c.user}
            try:
                logic.check_access('organization_create', context)
            except logic.NotAuthorized:
                toolkit.abort(403, 'Not authorized to create organization')
            # Generate URL
            CleanTitle = group.lower().replace(" ", "-").replace("'", "").replace(".", "").replace("(", "").replace(")", "")
            # Keep hyphens
            CleanTitleStep2 = re.sub('[^A-Za-z0-9\-]+', '', CleanTitle)
            # Add user
            users = [{'name': format(name),'capacity': 'admin' }]
            # If it's a new group, create it
            db_session = model.Session()
            if(int(new) == 1):
                try:
                    # Retrieve object instance from database
                    cool_plugin_instance = db_session.query(CoolPluginTable).filter_by(new_group_name=group).first()
                    
                    # Modify 'group' field
                    cool_plugin_instance.group = 0
                    # Modify status
                    cool_plugin_instance.approvedgroup = 'approved by '+toolkit.g.user
                    
                    # Save changes to database
                    db_session.commit()
                    
                except Exception as e:
                    # Handle errors as needed
                    db_session.rollback()
                    jsonerror={'error': str(e)}
                    return json.dumps(jsonerror)
                finally:
                    db_session.close()
                organizationapi = toolkit.get_action('group_create')(
                data_dict={'name': CleanTitleStep2, 'description': new_group_description, 'title': group, 'users':users  })
            #si no es una nueva organizacion agregamos al usuario
            if(int(new) == 0):
    
            # ckan.logic.action.create.group_member_create(context, data_dict)
            # Make a user a member of a group.

            # You must be authorized to edit the group.

            # Parameters:	
            # id (string) – the id or name of the group
            # username (string) – name or id of the user to be made member of the group
            # role (string) – role of the user in the group. One of member, editor, or admin
            # Returns:	
            # the newly created (or updated) membership

            # Return type:	
            # dictionary
                
                try:
                    # Recuperamos la instancia del objeto desde la base de datos
                    cool_plugin_instance = db_session.query(CoolPluginTable).filter_by(new_group_name=group).first()
                    
                    # Modificamos el campo 'group'
                    cool_plugin_instance.group = 0

                    # Modificamos el status
                    cool_plugin_instance.approvedgroup = 'approved by '+toolkit.g.user
                    
                    # Guardamos los cambios en la base de datos
                    db_session.commit()
                    
                except Exception as e:
                    # Manejar errores según sea necesario
                    db_session.rollback()
                    jsonerror={'error': str(e)}
                    return json.dumps(jsonerror)
                finally:
                    db_session.close()  
                organizationapi = toolkit.get_action('group_member_create')(
                data_dict={'id': CleanTitleStep2, 'username': format(name), 'role': 'admin'   })          
            return json.dumps(organizationapi)
        except Exception as e:
            jsonerror={'error': str(e)}
            return json.dumps(jsonerror)
    

    def approve(name, organization, new, new_organization_description):
        try:
            context = {'model': model, 'user': toolkit.c.user}
            try:
                logic.check_access('organization_create', context)
            except logic.NotAuthorized:
                toolkit.abort(403, 'Not authorized to create organization')
            
            # Primero obtenemos la instancia antes de usarla
            db_session = model.Session()
            
            # Modificamos la consulta para ser más específica
            cool_plugin_instance = db_session.query(CoolPluginTable).filter_by(
                wins_username=name,
                organization_name=organization
            ).first()
            
            if not cool_plugin_instance:
                return json.dumps({'error': 'User registration not found'})

            # Establecer user_role como 'admin' si es None
            user_role = cool_plugin_instance.user_role or 'admin'

            # Generamos la URL
            CleanTitle = organization.lower().replace(" ", "-").replace("'", "").replace(".", "").replace("(", "").replace(")", "")
            CleanTitleStep2 = re.sub('[^A-Za-z0-9\-]+', '', CleanTitle)
            users = [{'name': format(name), 'capacity': user_role}]

            try:
                if int(new) == 1:
                    # Crear nueva organización
                    organizationapi = toolkit.get_action('organization_create')(
                        data_dict={'name': CleanTitleStep2, 'description': new_organization_description, 
                                  'title': organization, 'users': users})
                else:
                    # Agregar usuario a organización existente
                    organizationapi = toolkit.get_action('organization_member_create')(
                        data_dict={'id': CleanTitleStep2, 'username': format(name), 
                                  'role': user_role})

                # Actualizar status después de cualquier operación exitosa
                cool_plugin_instance.approved = f'approved by {toolkit.g.user}'
                db_session.commit()
                
                return json.dumps(organizationapi)
                
            except Exception as e:
                db_session.rollback()
                return json.dumps({'error': str(e)})
            finally:
                db_session.close()
                
        except Exception as e:
            return json.dumps({'error': str(e)})
        
    def show_admin():
        context = {'model': model,
                   'user': toolkit.g.user, 'auth_user_obj': toolkit.g.userobj}
        try:
            logic.check_access('sysadmin', context, {})
        except logic.NotAuthorized:
            toolkit.abort(403, 'Need to be system administrator')
        # Crear una sesión de SQLAlchemy
        engine = create_engine(toolkit.config.get('sqlalchemy.url'))
        Session = sessionmaker(bind=engine)
        session = Session()

        # Realizar una consulta para recuperar datos
        results = session.query(CoolPluginTable).all()
        #print(results)
        try:
            return render_template("admin.html", results=results)
        finally:
            session.close()


    def show_something():
        errornewuserform = False
        if request.method == 'GET':
            try:
                # Obtener parámetros de paginación
                page = request.args.get('page', 1, type=int)
                per_page = 50  # Número de items por página
                
                # Obtener el total de grupos y organizaciones
                groups_count = toolkit.get_action('group_list')(data_dict={'count': True})
                orgs_count = toolkit.get_action('organization_list')(data_dict={'count': True})
                
                # Calcular el offset para la paginación
                offset = (page - 1) * per_page
                
                # Obtener grupos y organizaciones paginados
                groups = toolkit.get_action('group_list')(
                    data_dict={
                        'include_dataset_count': True,
                        'all_fields': True,
                        'limit': per_page,
                        'offset': offset
                    })
                organization_list = toolkit.get_action('organization_list')(
                    data_dict={
                        'include_dataset_count': True,
                        'all_fields': True,
                        'limit': per_page,
                        'offset': offset
                    })
                
                # Calcular el número total de páginas
                total_pages = max(
                    (groups_count + per_page - 1) // per_page,
                    (orgs_count + per_page - 1) // per_page
                )
                
                return render_template(
                    "index.html",
                    groups=groups,
                    organization_list=organization_list,
                    errornewuserform=errornewuserform,
                    current_page=page,
                    total_pages=total_pages,
                    per_page=per_page
                )
            except Exception as e:
                logger.error(f"Error in GET method: {e}")
                abort(500)

        if request.method == 'POST':
            try:
                # Verificar reCAPTCHA solo en POST
                recaptcha_response = request.form.get('recaptcha_response')
                if not recaptcha_response or not verify_recaptcha(recaptcha_response):
                    logger.error("reCAPTCHA verification failed")
                    return render_template("index.html", errornewuserform=True, 
                                        error_message="reCAPTCHA verification failed")

                email = request.form['email']
                # Ensure lowercase
                name = request.form['wins_username'].lower()
                # Keep only alphanumeric characters
                fullname = request.form['fullname']
                password = request.form['wins_password']
                title_within_organization = request.form['title_within_organization']
                organization_name = request.form['organization_name']
                new_organization_name = request.form['new_organization_name']
                new_organization_description = request.form['new_organization_description']
                group_form = 0
                age = request.form['age']
                nationality = request.form['nationality']
                organizationType = request.form['organizationType']
                gender = request.form['gender']
                user_role = request.form.get('user_role', 'admin')  # Default to 'admin' if not specified

                if (group_form == "new_group"):
                    group_form = 1
                    new_group_name = request.form['new_group_name']
                    new_group_description = request.form['new_group_description']
                else:
                    new_group_name = "NA"
                    group_form = 0
                    new_group_description = "NA"
                
                if(organization_name == "new"):
                    organization_name = new_organization_name
                    new_organization_name = 1
                    user_role = 'admin'  # Force admin role for new organization creators
                else:
                    new_organization_name = 0
                    new_organization_description = "NA"
                # print(group_form)
                # print(new_group_name)
                # print(organization_name)

                newuser = [{'email': email ,'name': name, 'fullname': fullname, 'password': password}]
                #ckan.logic.action.create.user_create(context, data_dict)
                # Create a new user.

                # You must be authorized to create users.

                # Parameters:	
                # name (string) – the name of the new user, a string between 2 and 100 characters in length, containing only lowercase alphanumeric characters, - and _
                # email (string) – the email address for the new user
                # password (string) – the password of the new user, a string of at least 4 characters
                # id (string) – the id of the new user (optional)
                # fullname (string) – the full name of the new user (optional)
                # about (string) – a description of the new user (optional)
                # image_url (string) – the URL to an image to be displayed on the group's page (optional)
                # plugin_extras (dict) –
                # private extra user data belonging to plugins. Only sysadmin users may set this value. It should be a dict that can be dumped into JSON, and plugins should namespace their extras with the plugin name to avoid collisions with other plugins, eg:

                # {
                #     "name": "test_user",
                #     "email": "test@example.com",
                #     "plugin_extras": {
                #         "my_plugin": {
                #             "private_extra": 1
                #         },
                #         "another_plugin": {
                #             "another_extra": True
                #         }
                #     }
                # }
                # Check if user already exists
                try:
                    context = {'model': model, 'user': toolkit.c.user}
                    # Instead of using the validator directly, use get_action to check if user exists
                    existing_user = toolkit.get_action('user_show')(
                        context, {'id': name}
                    )
                    # User exists - skip user creation but continue with organization registration
                    logger.info(f"User {name} already exists, proceeding with organization registration")
                    user_data = {
                        'fullname': fullname,
                        'wins_username': name,
                        'email': email,
                        'organization_name': organization_name,
                        'title_within_organization': title_within_organization,
                        'organizationType': organizationType
                    }
                    
                    # Add data to CoolPluginTable for existing user
                    engine = create_engine(toolkit.config.get('sqlalchemy.url'))
                    Base.metadata.create_all(engine)
                    Session = sessionmaker(bind=engine)
                    session = Session()

                    db_model = CoolPluginTable(
                        fullname=fullname,
                        wins_username=name,
                        email=email,
                        title_within_organization=title_within_organization,
                        approved="Pending",
                        approvedgroup="Pending",
                        organization_name=organization_name,
                        new_organization_name=new_organization_name,
                        new_organization_description=new_organization_description,
                        age=age,
                        gender=gender,
                        organizationType=organizationType,
                        nationality=nationality,
                        user_role=user_role,
                    )

                    session.add(db_model)
                    session.commit()
                    
                    # Send notification to admins
                    send_admin_notification(user_data)
                    return render_template("index.html", newuser=True, errornewuserform=False)

                except toolkit.ObjectNotFound:
                    # User doesn't exist - continue with original user creation flow
                    logger.info(f"User {name} doesn't exist - continuing with user creation")
                    try:
                        logic.check_access('user_create', context)
                        groups = toolkit.get_action('user_create')(
                        data_dict={'name': name, 'email': email, 'password': password, 'fullname': fullname  })
                        # Preparar datos para la notificación
                        user_data = {
                            'fullname': fullname,
                            'wins_username': name,
                            'email': email,
                            'organization_name': organization_name,
                            'title_within_organization': title_within_organization,
                            'organizationType': organizationType
                        }
                        # Add data to CoolPluginTable
                        engine = create_engine(toolkit.config.get('sqlalchemy.url'))
                        Base.metadata.create_all(engine)
                        Session = sessionmaker(bind=engine)
                        session = Session()

                        db_model = CoolPluginTable(
                            fullname=fullname,
                            wins_username=name,
                            email=email,
                            title_within_organization=title_within_organization,
                            approved="Pending",
                            approvedgroup="Pending",
                            organization_name = organization_name,
                            new_organization_name = new_organization_name,
                            new_organization_description = new_organization_description,
                            age = age,
                            gender = gender,
                            organizationType = organizationType,
                            nationality = nationality,
                            user_role=user_role,
                        )

                        session.add(db_model)
                        session.commit()
                        # Enviar notificación a los administradores
                        send_admin_notification(user_data)
                        return render_template("index.html", newuser=True, errornewuserform=False)

                    except logic.NotAuthorized:
                        toolkit.abort(403, 'Not authorized to create users')               
            except Exception as e:
                if session:
                    session.rollback()
                logger.error(f"Error in POST method: {e}")
                return render_template("index.html", errornewuserform=True)
            finally:
                if session:
                    session.close()
        


    def reject(name, organization, reason):
            logger.debug(f"Starting rejection for user: {name}, organization: {organization}, reason: {reason}")
            try:
                context = {'model': model, 'user': toolkit.c.user}
                try:
                    logic.check_access('organization_create', context)
                except logic.NotAuthorized:
                    logger.error("User not authorized to reject users")
                    toolkit.abort(403, 'Not authorized to reject users')

                db_session = model.Session()
                try:
                    cool_plugin_instance = db_session.query(CoolPluginTable).filter_by(
                        wins_username=name, 
                        organization_name=organization
                    ).first()
                    
                    if not cool_plugin_instance:
                        logger.error("No corresponding instance found in CoolPluginTable")
                        return json.dumps({'error': 'Record not found'})

                    cool_plugin_instance.rejected = f'rejected by {toolkit.g.user}'
                    cool_plugin_instance.rejection_reason = reason
                    logger.debug(f"Updating instance: {cool_plugin_instance}")
                    
                    db_session.commit()
                    logger.debug("Successful commit")
                    
                    return json.dumps({'success': True, 'message': 'User rejected successfully'})
                except Exception as e:
                    logger.error(f"Error in rejection: {e}")
                    db_session.rollback()
                    return json.dumps({'error': str(e)})
                finally:
                    db_session.close()
            except Exception as e:
                logger.error(f"General error in rejection: {e}")
                return json.dumps({'error': str(e)})