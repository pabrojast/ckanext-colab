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
# from ckan.logic.action.get import config_option_show
# import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText

Base = declarative_base()

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
        # image_url (string) – the URL to an image to be displayed on the group’s page (optional)
        # type (string) – the type of the group (optional, default: 'group'), IGroupForm plugins associate themselves with different group types and provide custom group handling behaviour for these types Cannot be ‘organization’
        # state (string) – the current state of the group, e.g. 'active' or 'deleted', only active groups show up in search results and other lists of groups, this parameter will be ignored if you are not authorized to change the state of the group (optional, default: 'active')
        # approval_status (string) – (optional)
        # extras (list of dataset extra dictionaries) – the group’s extras (optional), extras are arbitrary (key: value) metadata items that can be added to groups, each extra dictionary should have keys 'key' (a string), 'value' (a string), and optionally 'deleted'
        # packages (list of dictionaries) – the datasets (packages) that belong to the group, a list of dictionaries each with keys 'name' (string, the id or name of the dataset) and optionally 'title' (string, the title of the dataset)
        # groups (list of dictionaries) – the groups that belong to the group, a list of dictionaries each with key 'name' (string, the id or name of the group) and optionally 'capacity' (string, the capacity in which the group is a member of the group)
        # users (list of dictionaries) – the users that belong to the group, a list of dictionaries each with key 'name' (string, the id or name of the user) and optionally 'capacity' (string, the capacity in which the user is a member of the group)
        # Returns:	
        # the newly created group (unless ‘return_id_only’ is set to True in the context, in which case just the group id will be returned)

        # Return type:	
        # dictionary
        try:
            context = {'model': model, 'user': toolkit.c.user}
            try:
                logic.check_access('organization_create', context)
            except logic.NotAuthorized:
                toolkit.abort(403, 'Not authorized to create organization')
            #generamos la url 
            CleanTitle = group.lower().replace(" ", "-").replace("'", "").replace(".", "").replace("(", "").replace(")", "")
            #mantenemos los - 
            CleanTitleStep2 = re.sub('[^A-Za-z0-9\-]+', '', CleanTitle)
            #agregamos al usuario
            users = [{'name': format(name),'capacity': 'admin' }]
            #si es un grupo nuevo lo creamos
            db_session = model.Session()
            if(int(new) == 1):
            
                try:
                    # Recuperamos la instancia del objeto desde la base de datos
                    cool_plugin_instance = db_session.query(CoolPluginTable).filter_by(new_group_name=group).first()
               
                    # Modificamos el campo 'group'
                    cool_plugin_instance.group = 0
                    # Modificamos el status
                    cool_plugin_instance.approvedgroup = 'approved by '+toolkit.g.user
                    
                    # Guardamos los cambios en la base de datos
                    db_session.commit()
                    
                    # Devolvemos el objeto modificado
                    #return json.dumps(cool_plugin_instance.__dict__)
                except Exception as e:
                    # Manejar errores según sea necesario
                    db_session.rollback()
                    jsonerror={'error': str(e)}
                    return json.dumps(jsonerror)
                    #return json.dumps({'error': str(e)})
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
                    
                    # Devolvemos el objeto modificado
                    #return json.dumps(cool_plugin_instance.__dict__)
                except Exception as e:
                    # Manejar errores según sea necesario
                    db_session.rollback()
                    jsonerror={'error': str(e)}
                    return json.dumps(jsonerror)
                    #return json.dumps({'error': str(e)})
                finally:
                    db_session.close()  
                organizationapi = toolkit.get_action('group_member_create')(
                data_dict={'id': CleanTitleStep2, 'username': format(name), 'role': 'admin'   })          
            return json.dumps(organizationapi)
        except Exception as e:
            jsonerror={'error': str(e)}
            return json.dumps(jsonerror)
    

    def approve(name, organization, new, new_organization_description):

        # ckan.logic.action.create.organization_create(context: Context, data_dict: dict[str, Any])→ Union[str, dict[str, Any]]¶
        # Create a new organization.

        # You must be authorized to create organizations.

        # Plugins may change the parameters of this function depending on the value of the type parameter, see the IGroupForm plugin interface.

        # Parameters:
        # name (string) – the name of the organization, a string between 2 and 100 characters long, containing only lowercase alphanumeric characters, - and _
        # id (string) – the id of the organization (optional)
        # title (string) – the title of the organization (optional)
        # description (string) – the description of the organization (optional)
        # image_url (string) – the URL to an image to be displayed on the organization’s page (optional)
        # state (string) – the current state of the organization, e.g. 'active' or 'deleted', only active organizations show up in search results and other lists of organizations, this parameter will be ignored if you are not authorized to change the state of the organization (optional, default: 'active')
        # approval_status (string) – (optional)
        # extras (list of dataset extra dictionaries) – the organization’s extras (optional), extras are arbitrary (key: value) metadata items that can be added to organizations, each extra dictionary should have keys 'key' (a string), 'value' (a string), and optionally 'deleted'
        # packages (list of dictionaries) – the datasets (packages) that belong to the organization, a list of dictionaries each with keys 'name' (string, the id or name of the dataset) and optionally 'title' (string, the title of the dataset)
        # users (list of dictionaries) – the users that belong to the organization, a list of dictionaries each with key 'name' (string, the id or name of the user) and optionally 'capacity' (string, the capacity in which the user is a member of the organization)

        # Returns:
        # the newly created organization (unless ‘return_id_only’ is set to True in the context, in which case just the organization id will be returned)

        # Return type:
        # dictionary
        try:
            context = {'model': model, 'user': toolkit.c.user}
            try:
                logic.check_access('organization_create', context)
            except logic.NotAuthorized:
                toolkit.abort(403, 'Not authorized to create organization')
            #generamos la url 
            CleanTitle = organization.lower().replace(" ", "-").replace("'", "").replace(".", "").replace("(", "").replace(")", "")
            #mantenemos los - 
            CleanTitleStep2 = re.sub('[^A-Za-z0-9\-]+', '', CleanTitle)
            #agregamos al usuario
            users = [{'name': format(name),'capacity': 'admin' }]
            #si es una organizacion nueva creamos la organizacion
            if(int(new) == 1):
                organizationapi = toolkit.get_action('organization_create')(
                data_dict={'name': CleanTitleStep2, 'description': new_organization_description, 'title': organization, 'users':users  })
                db_session = model.Session()
                try:
                    # Recuperamos la instancia del objeto desde la base de datos
                    cool_plugin_instance = db_session.query(CoolPluginTable).filter_by(organization_name=organization).first()
                    
                    # Modificamos el campo 'approved'
                    cool_plugin_instance.approved = 'approved by '+toolkit.g.user
                    
                    # Guardamos los cambios en la base de datos
                    db_session.commit()
                    
                    # Devolvemos el objeto modificado
                    #return json.dumps(cool_plugin_instance.__dict__)
                except Exception as e:
                    # Manejar errores según sea necesario
                    db_session.rollback()
                    #return json.dumps({'error': str(e)})
                finally:
                    db_session.close()
            #si no es una nueva organizacion agregamos al usuario
            if(int(new) == 0):
                # ckan.logic.action.create.organization_member_create(context, data_dict)
                # Make a user a member of an organization.

                # You must be authorized to edit the organization.

                # Parameters:	
                # id (string) – the id or name of the organization
                # username (string) – name or id of the user to be made member of the organization
                # role (string) – role of the user in the organization. One of member, editor, or admin
                # Returns:	
                # the newly created (or updated) membership

                # Return type:	
                # dictionary
                organizationapi = toolkit.get_action('organization_member_create')(
                data_dict={'id': CleanTitleStep2, 'username': format(name), 'role': 'admin'   })
                db_session = model.Session()
                try:
                    # Recuperamos la instancia del objeto desde la base de datos
                    cool_plugin_instance = db_session.query(CoolPluginTable).filter_by(organization_name=organization).first()
                    
                    # Modificamos el campo 'approved'
                    cool_plugin_instance.approved = 'approved by '+toolkit.g.user
                    
                    # Guardamos los cambios en la base de datos
                    db_session.commit()
                    
                    # Devolvemos el objeto modificado
                    #return json.dumps(cool_plugin_instance.__dict__)
                except Exception as e:
                    # Manejar errores según sea necesario
                    db_session.rollback()
                    #return json.dumps({'error': str(e)})
                finally:
                    db_session.close()
            return json.dumps(organizationapi)
        
        except Exception as e:
            jsonerror={'error': str(e)}
            return json.dumps(jsonerror)
        
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
        return render_template("admin.html", results=results)
        session.close()


    def show_something():
        errornewuserform = False
        if request.method == 'GET':
            #get the groups
            groups = toolkit.get_action('group_list')(
            data_dict={'include_dataset_count': True, 'all_fields': True, 'limit' : 1000})
            newuser = False
            organization_list = toolkit.get_action('organization_list')(
            data_dict={'include_dataset_count': True, 'all_fields': True, 'limit' : 1000})
            #you will get something like
            #[{'approval_status': 'approved', 'created': '2023-11-15T17:04:44.712875', 'description': '', 'display_name': 'ukgov', 'id': 'ff5b411d-dedd-4560-ac93-b59621644e61', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'ukgov', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': '', 'type': 'group'}, {'approval_status': 'approved', 'created': '2023-11-15T17:04:44.713652', 'description': '', 'display_name': 'test1', 'id': 'c1738e32-ced0-41dd-bb7d-251df5aa46b1', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'test1', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': '', 'type': 'group'}, {'approval_status': 'approved', 'created': '2023-11-15T17:04:44.714297', 'description': '', 'display_name': 'test2', 'id': 'cc89cb78-cfb1-47ff-9f17-e9551fa0f1ac', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'test2', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': '', 'type': 'group'}, {'approval_status': 'approved', 'created': '2023-11-15T17:04:44.714706', 'description': '', 'display_name': 'penguin', 'id': '9670daa2-0b07-4a8a-87e4-6313400c40df', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'penguin', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': '', 'type': 'group'}, {'approval_status': 'approved', 'created': '2023-11-15T17:03:48.152620', 'description': 'These are books that David likes.', 'display_name': "Dave's books", 'id': '4f25f1e7-48c9-4bc0-81f7-044a91b8d527', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'david', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': "Dave's books", 'type': 'group'}, {'approval_status': 'approved', 'created': '2023-11-15T17:03:48.153429', 'description': 'Roger likes these books.', 'display_name': "Roger's books", 'id': 'ff2f73ff-dff5-4de6-8f46-efc5dc44cd43', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'roger', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': "Roger's books", 'type': 'group'}]
            return render_template("index.html", groups=groups, organization_list = organization_list , errornewuserform = errornewuserform )
        if request.method == 'POST':
            email = request.form['email']
            #aseguramos minuscula
            name = request.form['wins_username'].lower()
            # Mantener solo caracteres alfanuméricos
            fullname =  request.form['fullname']
            password = request.form['wins_password']
            title_within_organization = request.form['title_within_organization']
            #authorization_start_date = request.form['authorization_start_date']
            organization_name = request.form['organization_name']
            new_organization_name = request.form['new_organization_name']
            new_organization_description = request.form['new_organization_description']
            group_form = 0
            age = request.form['age']
            nationality = request.form['nationality']
            organizationType = request.form['organizationType']
            gender = request.form['gender']

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
            # image_url (string) – the URL to an image to be displayed on the group’s page (optional)
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
            # Verificar la autorización antes de crear un usuario
            context = {'model': model, 'user': toolkit.c.user}
            try:
                logic.check_access('user_create', context)
            except logic.NotAuthorized:
                toolkit.abort(403, 'Not authorized to create users')
            try:
                groups = toolkit.get_action('user_create')(
                data_dict={'name': name, 'email': email, 'password': password, 'fullname': fullname  })
                #print(groups)


                # # Obtener la configuración SMTP de CKAN
                # smtp_server = config_option_show(context, {'key': 'smtp.server'})
                # smtp_user = config_option_show(context, {'key': 'smtp.user'})
                # smtp_password = config_option_show(context, {'key': 'smtp.password'})
                # smtp_mail_from = config_option_show(context, {'key': 'smtp.mail_from'})

                # # Configuración del correo electrónico
                # email_destinatario = "projas@cazalac.org"  # Dirección del destinatario

                # # Función para enviar correo electrónico
                # def enviar_correo(asunto, mensaje):
                #     msg = MIMEMultipart()
                #     msg['From'] = smtp_mail_from
                #     msg['To'] = email_destinatario
                #     msg['Subject'] = asunto

                #     msg.attach(MIMEText(mensaje, 'plain'))

                #     server = smtplib.SMTP(smtp_server)
                #     server.starttls()
                #     server.login(smtp_user, smtp_password)
                #     server.sendmail(smtp_mail_from, email_destinatario, msg.as_string())
                #     server.quit()

                # # Ejemplo de uso
                # enviar_correo("New User", "Este es un mensaje de prueba.")


            except:
                errornewuserform = True
                return render_template("index.html", errornewuserform = errornewuserform, newuser=False)
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
                #authorization_start_date=authorization_start_date,
                approved="Pending",
                approvedgroup="Pending",
                organization_name = organization_name,
                new_organization_name = new_organization_name,
                new_organization_description = new_organization_description,
                age = age,
                gender = gender,
                organizationType = organizationType,
                nationality = nationality
            )

            session.add(db_model)
            session.commit()
            session.close()
        


            return render_template("index.html", newuser=newuser , errornewuserform = errornewuserform)

    # def do_something(name):
    #     return "Welcome to ckan !".format(name)
    

    # def help_it(num):
    #     return random.randint(num, num + 100)
    
    # def add():
    #     db_model = CoolPluginTable(
    #         random_number=random.randint(1, 10000),
    #         name="random thing",
    #         dataset_name="test-dataset",
    #         created_at= _time.now()
    #     )

    #     db_model.save()

    #     return "Success!"
    

    # def get():
    #     dataset = "test-dataset"
    #     result = CoolPluginTable().get_by_package(name=dataset)

    #     return str(result[0].random_number)
    

    # def update():
    #     dataset = "test-dataset"
    #     result = CoolPluginTable().get_by_package(name=dataset)
    #     for res in result:
    #         res.random_number=random.randint(1, 10000)
    #         res.commit()
        
    #     return "Success!"
    

    # def delete():
    #     dataset = "test-dataset"
    #     result = CoolPluginTable().get_by_package(name=dataset)
    #     for res in result:
    #         res.random_number=random.randint(1, 10000)
    #         res.delete()
    #         res.commit()
        
    #     return "Success!"


    # def only_admin_can_access_me():
    #     context = {'model': model,
    #                'user': toolkit.g.user, 'auth_user_obj': toolkit.g.userobj}
    #     try:
    #         logic.check_access('sysadmin', context, {})
    #     except logic.NotAuthorized:
    #         toolkit.abort(403, 'Need to be system administrator to administer')
        
    #     dataset_id = request.form.get('dataset_id')
    #     return "Hello Admin with Dataset {}!".format(dataset_id)