from flask import render_template, request, abort
import ckan.plugins.toolkit as toolkit
import ckan.model as model
import ckan.logic as logic
from ckanext.colab.models.cool_plugin_table import CoolPluginTable, OrganizationRequestTable
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import re 
import json 
import logging
from ckanext.colab.lib.email_notifications import send_admin_notification
import requests
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import ckan.lib.uploader as uploader
import ckan.lib.helpers as h
from functools import lru_cache
import time

# Logging configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

Base = declarative_base()

# Cache with 5 minutes expiration time
_cache_timestamp = {}

def timed_lru_cache(seconds: int, maxsize: int = 128):
    """LRU cache que expira después de un tiempo específico"""
    def decorator(func):
        cached_func = lru_cache(maxsize=maxsize)(func)
        
        def wrapper(*args, **kwargs):
            # Generar clave única para los argumentos
            cache_key = str(args) + str(kwargs)
            current_time = time.time()
            
            # Verificar si el cache ha expirado
            if cache_key in _cache_timestamp:
                if current_time - _cache_timestamp[cache_key] > seconds:
                    # Cache expirado, limpiar
                    cached_func.cache_clear()
                    _cache_timestamp.clear()
            
            # Actualizar timestamp y retornar resultado cacheado
            _cache_timestamp[cache_key] = current_time
            return cached_func(*args, **kwargs)
        
        wrapper.cache_clear = cached_func.cache_clear
        return wrapper
    return decorator

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

@timed_lru_cache(seconds=300, maxsize=20)  # Cache de 5 minutos
def get_all_groups_cached():
    """Obtiene todos los grupos con cache"""
    try:
        return toolkit.get_action('group_list')(
            data_dict={'include_dataset_count': True, 'all_fields': True, 'limit': 500}
        )
    except Exception as e:
        logger.error(f"Error obteniendo lista de grupos: {e}")
        return []

@timed_lru_cache(seconds=300, maxsize=20)  # Cache de 5 minutos
def get_all_organizations_cached():
    """Obtiene todas las organizaciones con cache"""
    try:
        return toolkit.get_action('organization_list')(
            data_dict={'include_dataset_count': True, 'all_fields': True, 'limit': 500}
        )
    except Exception as e:
        logger.error(f"Error obteniendo lista de organizaciones: {e}")
        return []

class MyLogic():

    @staticmethod
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
    

    @staticmethod
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

            # Verificar si el usuario CKAN existe
            try:
                existing_user = toolkit.get_action('user_show')({'ignore_auth': True}, {'id': name})
                user_exists = True
                logger.info(f"CKAN user {name} already exists")
            except toolkit.ObjectNotFound:
                user_exists = False
                logger.warning(f"CKAN user {name} does not exist - this method should not be called for non-existent users")
                return json.dumps({
                    'error': f'CKAN user {name} does not exist. The user must complete registration first.',
                    'details': 'This approval method requires an existing CKAN user.'
                })

            # Generamos la URL
            CleanTitle = organization.lower().replace(" ", "-").replace("'", "").replace(".", "").replace("(", "").replace(")", "")
            CleanTitleStep2 = re.sub('[^A-Za-z0-9\-]+', '', CleanTitle)
            users = [{'name': format(name), 'capacity': user_role}]

            try:
                if int(new) == 1:
                    # Verificar si la organización ya existe antes de crearla
                    try:
                        existing_org = toolkit.get_action('organization_show')({'ignore_auth': True}, {'id': CleanTitleStep2})
                        # Si llegamos aquí, la organización ya existe
                        # Agregar usuario a organización existente en lugar de crear nueva
                        logger.warning(f"Organization {CleanTitleStep2} already exists, adding user as member instead")
                        organizationapi = toolkit.get_action('organization_member_create')(
                            data_dict={'id': CleanTitleStep2, 'username': format(name), 
                                      'role': user_role})
                    except toolkit.ObjectNotFound:
                        # La organización no existe, podemos crearla
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
                
                # Enviar notificación por email (opcional para el método legacy)
                try:
                    if cool_plugin_instance.email:
                        from ckan.lib import mailer
                        temp_user = type('obj', (object,), {
                            'email': cool_plugin_instance.email,
                            'name': name,
                            'display_name': cool_plugin_instance.fullname
                        })
                        approval_subject = f"[{toolkit.config.get('ckan.site_title')}] Your registration has been approved"
                        approval_body = f"Dear {cool_plugin_instance.fullname},\n\nYour registration has been approved and you have been added to {organization} as {user_role}.\n\nBest regards"
                        mailer.mail_user(temp_user, approval_subject, approval_body)
                except Exception as e:
                    logger.error(f"Failed to send approval email: {e}")
                
                return json.dumps(organizationapi)
                
            except Exception as e:
                db_session.rollback()
                return json.dumps({'error': str(e)})
            finally:
                db_session.close()
                
        except Exception as e:
            return json.dumps({'error': str(e)})

    @staticmethod
    def approve_post():
        """Handle POST requests for user approval"""
        try:
            context = {'model': model, 'user': toolkit.c.user}
            try:
                logic.check_access('organization_create', context)
            except logic.NotAuthorized:
                toolkit.abort(403, 'Not authorized to create organization')
            
            # Obtener datos del formulario POST
            wins_username = request.form.get('wins_username')
            organization_name = request.form.get('organization_name')
            new_organization_name = request.form.get('new_organization_name', '0')
            new_organization_description = request.form.get('new_organization_description', 'NA')
            selected_user_role = request.form.get('user_role', 'admin')
            
            if not wins_username or not organization_name:
                return json.dumps({'error': 'Missing required parameters'})
            
            db_session = model.Session()
            
            # Buscar la instancia del usuario
            cool_plugin_instance = db_session.query(CoolPluginTable).filter_by(
                wins_username=wins_username,
                organization_name=organization_name
            ).first()
            
            if not cool_plugin_instance:
                return json.dumps({'error': 'User registration not found'})

            # Usar el rol seleccionado por el administrador
            user_role = selected_user_role
            
            # Actualizar el rol en la base de datos
            cool_plugin_instance.user_role = user_role

            # Verificar si el usuario CKAN existe
            try:
                existing_user = toolkit.get_action('user_show')({'ignore_auth': True}, {'id': wins_username})
                user_exists = True
                logger.info(f"CKAN user {wins_username} already exists")
            except toolkit.ObjectNotFound:
                user_exists = False
                logger.info(f"CKAN user {wins_username} does not exist, will need to be created first")

            # Si el usuario no existe en CKAN, no podemos continuar
            if not user_exists:
                return json.dumps({
                    'error': f'CKAN user {wins_username} does not exist. The user must complete registration first.',
                    'details': 'User needs to register through the main form to create their CKAN account.'
                })

            # Limpiar el nombre de la organización para URL
            CleanTitle = organization_name.lower().replace(" ", "-").replace("'", "").replace(".", "").replace("(", "").replace(")", "")
            CleanTitleStep2 = re.sub('[^A-Za-z0-9\-]+', '', CleanTitle)
            users = [{'name': format(wins_username), 'capacity': user_role}]

            try:
                if new_organization_name == '1':
                    # Verificar si la organización ya existe antes de crearla
                    try:
                        existing_org = toolkit.get_action('organization_show')({'ignore_auth': True}, {'id': CleanTitleStep2})
                        # Si llegamos aquí, la organización ya existe
                        # Agregar usuario a organización existente en lugar de crear nueva
                        logger.warning(f"Organization {CleanTitleStep2} already exists, adding user as member instead")
                        organizationapi = toolkit.get_action('organization_member_create')(
                            data_dict={'id': CleanTitleStep2, 'username': format(wins_username), 
                                      'role': user_role})
                        organizationapi['message'] = f'User added to existing organization: {organization_name}'
                    except toolkit.ObjectNotFound:
                        # La organización no existe, podemos crearla
                        organizationapi = toolkit.get_action('organization_create')(
                            data_dict={'name': CleanTitleStep2, 'description': new_organization_description, 
                                      'title': organization_name, 'users': users})
                        organizationapi['message'] = f'New organization created: {organization_name}'
                else:
                    # Verificar que la organización existe antes de agregar el usuario
                    try:
                        existing_org = toolkit.get_action('organization_show')({'ignore_auth': True}, {'id': CleanTitleStep2})
                        # Agregar usuario a organización existente
                        organizationapi = toolkit.get_action('organization_member_create')(
                            data_dict={'id': CleanTitleStep2, 'username': format(wins_username), 
                                      'role': user_role})
                        organizationapi['message'] = f'User added to organization: {organization_name}'
                    except toolkit.ObjectNotFound:
                        return json.dumps({'error': f'Organization {organization_name} does not exist'})

                # Actualizar status después de cualquier operación exitosa
                cool_plugin_instance.approved = f'approved by {toolkit.g.user}'
                db_session.commit()
                
                # Enviar notificación por email al usuario aprobado
                try:
                    user_email = cool_plugin_instance.email
                    if user_email:
                        approval_subject = f"[{toolkit.config.get('ckan.site_title')}] Your registration has been approved"
                        approval_body = f"""Dear {cool_plugin_instance.fullname},

Your registration request has been approved by {toolkit.g.user}.

You have been added to the organization: {organization_name}
Your role in the organization is: {user_role}

You can now log in to the system using your username: {wins_username}

Best regards,
{toolkit.config.get('ckan.site_title')} Team
"""
                        # Crear un objeto usuario temporal para usar con mail_user
                        temp_user = type('obj', (object,), {
                            'email': user_email,
                            'name': wins_username,
                            'display_name': cool_plugin_instance.fullname
                        })
                        
                        from ckan.lib import mailer
                        mailer.mail_user(temp_user, approval_subject, approval_body)
                        logger.info(f"Approval notification sent to {user_email}")
                except Exception as email_error:
                    logger.error(f"Failed to send approval email: {email_error}")
                    # Don't fail the approval if email fails
                
                organizationapi['user'] = toolkit.g.user
                return json.dumps(organizationapi)
                
            except Exception as e:
                db_session.rollback()
                logger.error(f"Error in approve_post: {e}")
                return json.dumps({'error': str(e)})
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"General error in approve_post: {e}")
            return json.dumps({'error': str(e)})
        
    @staticmethod
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


    @staticmethod
    def show_something():
        errornewuserform = False
        if request.method == 'GET':
            try:
                # Obtener grupos desde cache (organizaciones se cargan via JavaScript)
                groups = get_all_groups_cached()
                return render_template("index.html", groups=groups, 
                                     errornewuserform=errornewuserform)
            except Exception as e:
                logger.error(f"Error in GET method: {e}")
                # En caso de error, retornar listas vacías
                return render_template("index.html", groups=[], 
                                     errornewuserform=errornewuserform)

        if request.method == 'POST':
            try:
                logger.info("POST request received at /colab")
                logger.debug(f"Form data keys: {list(request.form.keys())}")
                
                # Check if form was actually submitted
                if not request.form.get('form_submitted'):
                    logger.warning("Form submitted without form_submitted field")
                
                # Verificar reCAPTCHA primero
                recaptcha_response = request.form.get('recaptcha_response')
                recaptcha_enabled = toolkit.config.get('ckan.recaptcha.publickey') and toolkit.config.get('ckan.recaptcha.privatekey')
                
                if recaptcha_enabled and (not recaptcha_response or not verify_recaptcha(recaptcha_response)):
                    logger.error("reCAPTCHA verification failed")
                    groups = get_all_groups_cached()
                    return render_template("index.html", errornewuserform=True, 
                                        error_message="reCAPTCHA verification failed",
                                        groups=groups)

                # Get form data with error handling
                try:
                    email = request.form.get('email', '').strip()
                    # Ensure lowercase
                    name = request.form.get('wins_username', '').lower().strip()
                    # Keep only alphanumeric characters
                    fullname = request.form.get('fullname', '').strip()
                    password = request.form.get('wins_password', '')
                    confirm_password = request.form.get('confirm-password', '')
                    title_within_organization = request.form.get('title_within_organization', '').strip()
                    organization_name = request.form.get('organization_name', '').strip()
                    new_organization_name = request.form.get('new_organization_name', '').strip()
                    new_organization_description = request.form.get('new_organization_description', '').strip()
                    group_form = 0
                    date_of_birth = request.form.get('date_of_birth', '').strip()
                    nationality = request.form.get('nationality', '').strip()
                    organizationType = request.form.get('organizationType', '').strip()
                    gender = request.form.get('gender', '').strip()
                    # Handle "other" gender option
                    if gender == 'other':
                        gender_other = request.form.get('genderOther', '').strip()
                        if gender_other:
                            gender = gender_other
                    user_role = request.form.get('user_role', 'admin')  # Default to 'admin' if not specified
                    citizens4water = request.form.get('citizens4water', '')  # Get citizens4water checkbox value
                    
                    logger.info(f"Processing registration for user: {name}, email: {email}, org: {organization_name}")
                    
                    # Validate required fields
                    if not all([email, name, password, title_within_organization, organization_name, date_of_birth, nationality, gender]):
                        logger.error("Missing required fields")
                        groups = get_all_groups_cached()
                        return render_template("index.html", errornewuserform=True, 
                                            error_message="Please fill in all required fields",
                                            groups=groups)
                    
                    # Validate date_of_birth (must be 16+)
                    try:
                        from datetime import datetime, date
                        dob = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                        today = date.today()
                        age_years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                        if age_years < 16:
                            logger.error("User is under 16")
                            groups = get_all_groups_cached()
                            return render_template("index.html", errornewuserform=True,
                                                error_message="You must be at least 16 years old to register",
                                                groups=groups)
                    except Exception:
                        logger.error("Invalid date_of_birth format")
                        groups = get_all_groups_cached()
                        return render_template("index.html", errornewuserform=True,
                                            error_message="Invalid date of birth format. Use YYYY-MM-DD",
                                            groups=groups)

                    # Validate password match
                    if password != confirm_password:
                        logger.error("Passwords do not match")
                        groups = get_all_groups_cached()
                        return render_template("index.html", errornewuserform=True, 
                                            error_message="Passwords do not match",
                                            groups=groups)
                    
                    # Validate password length
                    if len(password) < 8:
                        logger.error("Password too short")
                        groups = get_all_groups_cached()
                        return render_template("index.html", errornewuserform=True, 
                                            error_message="Password must be at least 8 characters long",
                                            groups=groups)
                    
                except Exception as e:
                    logger.error(f"Error extracting form data: {e}")
                    groups = get_all_groups_cached()
                    return render_template("index.html", errornewuserform=True, 
                                        error_message="Error processing form data",
                                        groups=groups)

                if (group_form == "new_group"):
                    group_form = 1
                    new_group_name = request.form['new_group_name']
                    new_group_description = request.form['new_group_description']
                else:
                    new_group_name = "NA"
                    group_form = 0
                    new_group_description = "NA"
                
                # Handle new organization
                is_new_organization = False
                if organization_name == "new":
                    is_new_organization = True
                    organization_name = new_organization_name
                    user_role = 'admin'  # Force admin role for new organization creators
                else:
                    new_organization_description = "NA" if not new_organization_description else new_organization_description
                # print(group_form)
                # print(new_group_name)
                # print(organization_name)

                # Removed unused variable newuser
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
                        new_organization_name=1 if is_new_organization else 0,
                        new_organization_description=new_organization_description,
                            date_of_birth=dob,
                        gender=gender,
                        organizationType=organizationType,
                        nationality=nationality,
                        user_role=user_role,
                        citizens4water=citizens4water,
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
                        new_user = toolkit.get_action('user_create')(
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
                            new_organization_name = 1 if is_new_organization else 0,
                            new_organization_description = new_organization_description,
                            date_of_birth = dob,
                            gender = gender,
                            organizationType = organizationType,
                            nationality = nationality,
                            user_role=user_role,
                            citizens4water=citizens4water,
                        )

                        session.add(db_model)
                        session.commit()
                        # Enviar notificación a los administradores
                        send_admin_notification(user_data)
                        return render_template("index.html", newuser=True, errornewuserform=False)

                    except logic.NotAuthorized:
                        toolkit.abort(403, 'Not authorized to create users')               
            except Exception as e:
                if 'session' in locals() and session:
                    session.rollback()
                logger.error(f"Error in POST method: {e}")
                logger.error(f"Error traceback: ", exc_info=True)
                groups = get_all_groups_cached()
                return render_template("index.html", errornewuserform=True, groups=groups,
                                     error_message=f"An error occurred: {str(e)}")
            finally:
                if 'session' in locals() and session:
                    session.close()
        


    @staticmethod
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

    @staticmethod
    def show_organization_request_form():
        """Show organization request form for logged users"""
        if not toolkit.g.userobj:
            toolkit.abort(403, 'You must be logged in to request an organization')
        
        try:
            # Get organization types for dropdown
            org_types = ['Academic Institution', 'Government Agency', 'NGO', 'Private Company', 'Research Institute', 'International Organization', 'Other']
            
            return render_template("organization_request.html", 
                                 current_user=toolkit.g.userobj.name,
                                 org_types=org_types)
        except Exception as e:
            logger.error(f"Error showing organization request form: {e}")
            abort(500)

    @staticmethod
    def submit_organization_request():
        """Handle organization request form submission"""
        if not toolkit.g.userobj:
            toolkit.abort(403, 'You must be logged in to request an organization')
        
        if request.method != 'POST':
            return toolkit.redirect_to('colab.organization_request_form')
        
        try:
            # Get form data
            organization_name = request.form.get('organization_name', '').strip()
            organization_description = request.form.get('organization_description', '').strip()
            organization_type = request.form.get('organization_type', '').strip()
            admin_username = request.form.get('admin_username', toolkit.g.userobj.name).strip()
            
            # Validation
            if not organization_name:
                return render_template("organization_request.html", 
                                     error="Organization name is required",
                                     current_user=toolkit.g.userobj.name,
                                     org_types=['Academic Institution', 'Government Agency', 'NGO', 'Private Company', 'Research Institute', 'International Organization', 'Other'])
            
            if not organization_description:
                return render_template("organization_request.html", 
                                     error="Organization description is required",
                                     current_user=toolkit.g.userobj.name,
                                     org_types=['Academic Institution', 'Government Agency', 'NGO', 'Private Company', 'Research Institute', 'International Organization', 'Other'])
            
            # Validate admin username exists
            try:
                toolkit.get_action('user_show')({'ignore_auth': True}, {'id': admin_username})
            except toolkit.ObjectNotFound:
                return render_template("organization_request.html", 
                                     error=f"User '{admin_username}' does not exist",
                                     current_user=toolkit.g.userobj.name,
                                     org_types=['Academic Institution', 'Government Agency', 'NGO', 'Private Company', 'Research Institute', 'International Organization', 'Other'])
            
            # Handle image upload using CKAN's uploader system (like ckanext-pages)
            image_filename = None
            if 'organization_image' in request.files:
                file = request.files['organization_image']
                if file and file.filename:
                    try:
                        # Use CKAN's uploader system (using page_images namespace for Azure compatibility)
                        upload = uploader.get_uploader('page_images')
                        
                        # Create a mutable dict for the uploader with the correct file field
                        upload.update_data_dict({'organization_image': file}, 'organization_image', 
                                              'image_upload', 'clear_upload')
                        upload.upload(max_size=2)  # 2MB max
                        
                        if upload.filename:
                            # Debug: Log the type and value of upload.filename
                            logger.debug(f"upload.filename type: {type(upload.filename)}")
                            logger.debug(f"upload.filename value: {upload.filename}")
                            
                            # Extract just the filename string
                            if hasattr(upload.filename, 'filename'):
                                # If it's a FileStorage object, get the filename attribute
                                image_filename = upload.filename.filename
                                logger.debug(f"Extracted from FileStorage.filename: {image_filename}")
                            elif hasattr(upload.filename, 'name'):
                                # If it's a file-like object, get the name
                                image_filename = upload.filename.name
                                logger.debug(f"Extracted from name: {image_filename}")
                            else:
                                # If it's already a string, use it directly
                                image_filename = str(upload.filename)
                                logger.debug(f"Converted to string: {image_filename}")
                            
                            # Clean the filename to ensure it's just the basename
                            import os
                            image_filename = os.path.basename(image_filename)
                            
                            # Final validation that it's a string
                            image_filename = str(image_filename)
                            logger.info(f"Final image filename to store: {image_filename} (type: {type(image_filename)})")
                        else:
                            logger.warning("No file was uploaded")
                            
                    except toolkit.ValidationError as e:
                        logger.warning(f"File upload validation error: {e}. Continuing without image.")
                        image_filename = None
                    except Exception as e:
                        logger.warning(f"Unexpected error uploading image: {e}. Continuing without image.")
                        image_filename = None
            
            # Create database entry
            db_session = model.Session()
            
            # Ensure the table exists (temporary fix until migration is run)
            try:
                from ckanext.colab.models.cool_plugin_table import organization_request_table, metadata
                metadata.create_all(model.meta.engine, tables=[organization_request_table])
            except Exception as e:
                logger.debug(f"Table creation attempt: {e}")
            
            try:
                # Final validation: ensure image_filename is a simple string or None
                if image_filename is not None:
                    # Convert to string and validate it's not a complex object
                    image_filename_str = str(image_filename)
                    # Ensure it doesn't contain object representation signs
                    if '<' in image_filename_str or '>' in image_filename_str or 'FileStorage' in image_filename_str:
                        logger.warning(f"Invalid filename detected: {image_filename_str}. Setting to None.")
                        image_filename = None
                    else:
                        image_filename = image_filename_str
                        logger.info(f"Validated filename for database: {image_filename}")
                
                org_request = OrganizationRequestTable(
                    requester_username=toolkit.g.userobj.name,
                    organization_name=organization_name,
                    organization_description=organization_description,
                    organization_image_url=image_filename,  # Store only the filename
                    admin_username=admin_username,
                    organization_type=organization_type,
                    status='pending',
                    created_date=datetime.now()
                )
                
                db_session.add(org_request)
                db_session.commit()
                
                return render_template("organization_request.html", 
                                     success=True,
                                     current_user=toolkit.g.userobj.name,
                                     org_types=['Academic Institution', 'Government Agency', 'NGO', 'Private Company', 'Research Institute', 'International Organization', 'Other'])
                
            except Exception as e:
                db_session.rollback()
                logger.error(f"Database error in organization request: {e}")
                return render_template("organization_request.html", 
                                     error="An error occurred while processing your request",
                                     current_user=toolkit.g.userobj.name,
                                     org_types=['Academic Institution', 'Government Agency', 'NGO', 'Private Company', 'Research Institute', 'International Organization', 'Other'])
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"Error in organization request submission: {e}")
            return render_template("organization_request.html", 
                                 error="An unexpected error occurred",
                                 current_user=toolkit.g.userobj.name,
                                 org_types=['Academic Institution', 'Government Agency', 'NGO', 'Private Company', 'Research Institute', 'International Organization', 'Other'])

    @staticmethod
    def show_organization_admin():
        """Show organization requests admin panel"""
        context = {'model': model, 'user': toolkit.g.user, 'auth_user_obj': toolkit.g.userobj}
        try:
            logic.check_access('sysadmin', context, {})
        except logic.NotAuthorized:
            toolkit.abort(403, 'Need to be system administrator')
        
        try:
            # Ensure the table exists (temporary fix until migration is run)
            try:
                from ckanext.colab.models.cool_plugin_table import organization_request_table, metadata
                metadata.create_all(model.meta.engine, tables=[organization_request_table])
            except Exception as e:
                logger.debug(f"Table creation attempt in admin: {e}")
                
            engine = create_engine(toolkit.config.get('sqlalchemy.url'))
            Session = sessionmaker(bind=engine)
            session = Session()
            
            # Get organization requests
            org_requests = session.query(OrganizationRequestTable).all()
            
            return render_template("organization_admin.html", requests=org_requests)
        except Exception as e:
            logger.error(f"Error showing organization admin: {e}")
            abort(500)
        finally:
            session.close()

    @staticmethod
    def approve_organization_request():
        """Approve organization request"""
        context = {'model': model, 'user': toolkit.g.user, 'auth_user_obj': toolkit.g.userobj}
        try:
            logic.check_access('sysadmin', context, {})
        except logic.NotAuthorized:
            toolkit.abort(403, 'Need to be system administrator')
        
        if request.method != 'POST':
            return json.dumps({'error': 'POST method required'})
        
        try:
            request_id = request.form.get('request_id')
            if not request_id:
                return json.dumps({'error': 'Request ID is required'})
            
            db_session = model.Session()
            try:
                org_request = db_session.query(OrganizationRequestTable).filter_by(id=request_id).first()
                if not org_request:
                    return json.dumps({'error': 'Organization request not found'})
                
                # Clean organization name for URL
                clean_name = org_request.organization_name.lower().replace(" ", "-").replace("'", "").replace(".", "").replace("(", "").replace(")", "")
                clean_name = re.sub('[^A-Za-z0-9\-]+', '', clean_name)
                
                # Create organization
                org_data = {
                    'name': clean_name,
                    'title': org_request.organization_name,
                    'description': org_request.organization_description,
                    'users': [{'name': org_request.admin_username, 'capacity': 'admin'}]
                }
                
                if org_request.organization_image_url:
                    # Generate the full URL for the organization
                    if not org_request.organization_image_url.startswith(('http://', 'https://', '/')):
                        image_url = h.url_for_static(
                            'uploads/page_images/%s' % org_request.organization_image_url,
                            qualified=True
                        )
                    else:
                        image_url = org_request.organization_image_url
                    org_data['image_url'] = image_url
                
                org_result = toolkit.get_action('organization_create')({'ignore_auth': True}, org_data)
                
                # Update request status
                org_request.status = 'approved'
                org_request.approved_by = toolkit.g.user
                org_request.approved_date = datetime.now()
                
                db_session.commit()
                
                return json.dumps({
                    'success': True, 
                    'message': f'Organization "{org_request.organization_name}" created successfully',
                    'organization_id': org_result['id']
                })
                
            except Exception as e:
                db_session.rollback()
                logger.error(f"Error approving organization request: {e}")
                return json.dumps({'error': str(e)})
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"General error in organization approval: {e}")
            return json.dumps({'error': str(e)})

    @staticmethod
    def reject_organization_request():
        """Reject organization request"""
        context = {'model': model, 'user': toolkit.g.user, 'auth_user_obj': toolkit.g.userobj}
        try:
            logic.check_access('sysadmin', context, {})
        except logic.NotAuthorized:
            toolkit.abort(403, 'Need to be system administrator')
        
        if request.method != 'POST':
            return json.dumps({'error': 'POST method required'})
        
        try:
            request_id = request.form.get('request_id')
            rejection_reason = request.form.get('rejection_reason', '').strip()
            
            if not request_id:
                return json.dumps({'error': 'Request ID is required'})
            
            if not rejection_reason:
                return json.dumps({'error': 'Rejection reason is required'})
            
            db_session = model.Session()
            try:
                org_request = db_session.query(OrganizationRequestTable).filter_by(id=request_id).first()
                if not org_request:
                    return json.dumps({'error': 'Organization request not found'})
                
                # Update request status
                org_request.status = 'rejected'
                org_request.rejected_by = toolkit.g.user
                org_request.rejected_date = datetime.now()
                org_request.rejection_reason = rejection_reason
                
                db_session.commit()
                
                return json.dumps({
                    'success': True, 
                    'message': f'Organization request rejected'
                })
                
            except Exception as e:
                db_session.rollback()
                logger.error(f"Error rejecting organization request: {e}")
                return json.dumps({'error': str(e)})
            finally:
                db_session.close()
                
        except Exception as e:
            logger.error(f"General error in organization rejection: {e}")
            return json.dumps({'error': str(e)})