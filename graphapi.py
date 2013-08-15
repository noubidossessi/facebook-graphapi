# -*- coding:utf-8 -*-
# Facebook Graph API Explorer. This will walk through the graph api.
#
# Features: 
#   - Get ID for a Facebook's group
#   - Create a dummy profile to interract with the Facebook's group
#   - Create a dummy Facebook's application using the dummy profile
#   - Get AppID and AppSecret for the dummy app page
#   - Use Python client for Facebook Api to get an access token
#   * Query the group for its fields (owner, creation_date, update_date,
#           picture, link, id,...). 
#           See https://developers.facebook.com/docs/reference/api/group/ for details
#   * Query the group for its members
#   * Query the group for its events
#   * Query the group for its picture
#   * Query the group for its docs
#   * Query the group for its feed
#   - Create database layout using web2py DAL   (TO BE IMPLEMENTED)
#       - The database layout is provided in app/models/facebook.py
#   - Pull data from Facebook if this is the first time the app is used
#       - For that, just query the database to check if there is existing data
#       in the database. If not, that means the app is running the first time
#       So we need to just PULL data from Facebook
#   - If "select from the database tables" returns data, we need to update the
#   content with new posts, comments, subscriptions, and get 
    
import facebook # Import facebook.py to use python client for facebook API
from gluon import * # To import web2py libraries and tools
                    # In occurence, current

from urlparse import urlparse   # To get query string from url. Most used
                                # in get_query_parameters()
# Get database access layer from current
table_name_prefix = 'facebook'
db = current.db

app_id = '239533669516062'
app_secret = '706a63e3fec89fbc35e0c92eac57ad66'
access_token = 'CAADZA2sdIgx4BAEVgPkiSvtD689tGOTmhbeZBIkeXboNsxDBMSgMOCq4uZAfZBCrsQmcDrPPZB98t5jCMlzoPZBqa2lhBWwVL0kEf7FezcvbJv3eydjnZA4dR8ZAe27JLl8rFcWTw9BnJnh8AwCb8217EJkFVSbUBH0ZD'
facebook_profile_id = '100003123256932'
facebook_id = '335662792434' # Facebook Group ID
facebook_post_id = '335662792434_10150431047037435'

def get_query_parameters(url):
    """

        Takes an url as argument and returns the query parameters
        parameters: {parameter:value, ...}

        For instance:
            url = 'http://abc.test.it/now?a=3&h=7'
            parameters = get_query_parameters(url) 
            parameters returns:
                {'a':3, 'h':7}
    """

    query = urlparse(url).query
    parameters = facebook.parse_qs(query)
    parameters = {key:value for key,value in parameters.iteritems()}

    # We are interested in extracting all parameters except access token
    if 'access_token' in parameters:
        del parameters['access_token']
        pass

    return parameters
    

class Base(dict):
    @staticmethod
    def factory(object_type, facebook_id, graph, *args, **kwargs):
        object_types = {
                'group' : FcbGroup,
                'user' : FcbUser,
                }

        assert object_type in object_types, "Unknown object type"

        return object_types[object_type](facebook_id, graph=graph, *args, **kwargs)

    def __init__(self, facebook_id, *args, **kwargs):
        """
            fields = dict( {field_name: supported} )
            field_name: object field, str, refer to facebook graph API documentation
            supported : boolean, True if supported by the database, False if cannot be stored in the
            database

            connexions = dict {connexion: supported}
        """
        # Verify that graph object is provided
        assert 'graph' in kwargs, "A facebook.GraphAPI object should be provided"
        assert isinstance(kwargs['graph'], facebook.GraphAPI), "graph\
                should be of type facebook.GraphAPI"

        self.graph = kwargs.pop('graph')
        self.facebook_id = facebook_id

        assert isinstance(self.graph, facebook.GraphAPI), "graph parameter should be instance of GraphAPI"

        self.fields = {
                'id':True,      # The object ID, string
                'name':True,    # The name of the object, string
                }

        self.references = {     # True if attribute.type = list:reference
                                # False if attribute.type = reference
                }

        # Database table columns FcbGroup.fields that are supported by the application. In fact that
        # means that FcbGroup.fields[field] returns True for field in FcbGroup.fields. But because
        # of database keywords or because of convenience needs, the table column used by the
        # database may differ from the field name used by Facebook Graph api. Then
        # FcbGroup.table_fields maps Facebook Graph API field to database table column
        self.table_fields = {               # Mapping between facebook fields and table fields. For efficiency,
                                            # Only field names which change are referenced here 
                'id':'facebook_id',
                }
        self.__table_name = str()          # To be set by the child class
        self.__table_columns = list()         # columns in the database
        self.connections = dict()       # Facebook's object connections

        # Update attributes with child properties
        variable_attributes = ['fields',  
                'table_fields', 
                'connections',
                'references',]
        if kwargs:
            if 'facebook_table' in kwargs:
                facebook_table = kwargs.pop('facebook_table')
                self.table_name = facebook_table 

            for attr in variable_attributes:
                if attr in kwargs:
                    # kwargs.pop(key) to remove from the dictionnary. It will
                    # remain some (key value) pairs in the kwargs. Those key
                    # value pairs will be used to initialize the object since
                    # it is itself a dictionnary. 
                    value = kwargs.pop(attr)
                    # Value should be a dictionnary
                    assert type(value) is dict, u"%s attribute should be a\
                            dictionnary" % attr
                    field = getattr(self, attr)
                    field.update(value)
                    
        # Define table columns
        # Add table columns whose name are adapted. This is done in
        # FcbGroup.table_fields
        # Most of the time Facebook id attribute will be changed to avoid
        # collision with attribute autogenerated by ORM framework. Another
        # side effect of not changing id attribute is that there will be clash
        # for foreign key to id attributes since there should be, most of the
        # time integer, but those from facebook are strings.
        self.__table_columns.extend([table_field \
                for field, table_field in self.table_fields.iteritems()\
                if self.fields[field]])

        # FcbGroup.fields contains all fields provided by Facebook Graph API with their support
        # status in the application here provided.  

        # Database table columns FcbGroup.fields that are supported by the application. In fact that
        # means that FcbGroup.fields[field] returns True for field in FcbGroup.fields. But because
        # of database keywords or because of convenience needs, the table column used by the
        # database may differ from the field name used by Facebook Graph api. Then
        # FcbGroup.table_fields maps Facebook Graph API fields to desired
        # table columns 

        for field in self.fields:
            if self.fields[field]\
                    and field not in self.table_fields:
                        self.__table_columns.append(field)
                        pass

        # Retrieve the table from the database
        self.table = getattr(db, self.table_name)

        # Call the parent child and use it to initialize the object with
        # remaining (key, value) pairs in kwargs.
        super(Base, self).__init__(**kwargs)
        pass

    def __getitem__(self,key):
        # An other implementation which allows to get a list of items from the
        # dictionnary
        if isinstance(key, (tuple,list)):
            return [super(Base,self).__getitem__(m) for m in key if m in\
                    self]
        else:
            return super(Base,self).__getitem__(key)\
                    if key in self else None

    @property
    def table_name(self):
        return u'%s_%s' % (table_name_prefix, self.__table_name)

    @table_name.setter
    def table_name(self, table_name):
        self.__table_name = table_name

    @property
    def table_columns(self):
        return self.__table_columns or None

    @table_columns.setter
    def table_columns(self, column_names):
        # table_columns can be a tuple or a list, in wich case we ensure that
        # the column is not already existant in the self.table_columns because
        # a list doesn't update but instead just append. There is no
        # integrated mean to verify that the column already exists in the
        # database. 
        # table_columns is a list. The class user can provide a list of
        # columns or a tuple of columns. 
        if isinstance(column_names, (tuple, list)):
            [self.__table_columns.append(column_name)\
                    for column_name in column_names\
                    if column_name not in self.__table_columns] 
        else:
            # If provided data is not a list, it should be a string. If not
            # already took into account, it will be added to the list
            assert isinstance(column_names, str), "Either a list or a str expected"
            self.__table_columns.append(column_names) 
            if column_names not in self.__table_columns:
                self.__table_columns.append(column_names)

    def exists(self, *args, **kwargs):
        assert hasattr(self, 'facebook_id'), "Missing Object ID"
        rows = db(self.table.facebook_id == self.facebook_id)
        if rows.count():
            return True
        else:
            return False

    def get(self, function, *args, **kwargs):

        assert isinstance(function, type(self.get)), "Expecting a function\
                as first argument"

        response = None
        try:
            response = function(*args, **kwargs)
        except (facebook.AppOAuthError, facebook.PasswordOAuthError,
                facebook.ExpiredOAuthError, facebook.InvalidOAuthError), e:
            # Extend access Token life. 
            # This method returs {'access_token': TOKEN, 'expires': EXPIRES}
            result = self.graph.extend_access_token(app_id, app_secret)
            self.graph.access_token = result['access_token']

            # Once token life is extended replay
            response = function(*args, **kwargs)
        except facebook.ServerError, e:
            # The server is throttling, retry later
            pass
        except facebook.UserError, e:
            # API Permission Denied or API Permission
            # The user has to grant the application
            # Inform the administrator by sending him a mail. Then we need
            # here the mail information of the administrator.
            pass
        except facebook.UserOAuthError, e:
            # User needs to log on www.facebook.com or m.facebook.com
            pass
        except facebook.AppOAuthError, e:
            # User removed the app from its settings
            pass
        except facebook.UnconfirmedOAuthError, e:
            # User needs to log on www.facebook.com or m.facebook.com
            pass
        except Exception, e:
            print e
            pass

        return response


    def get_object(self, *args, **kwargs):
        self.facebook_object = self.get(self.graph.get_object, 
                self.facebook_id, *args, **kwargs)

        return self.facebook_object

    def get_connection(self, connection, **kwargs):
        assert connection in self.connections, "Connection not supported"

        # Obtain data from Facebook
        # Use built-in get method because it takes care of all exception
        # handling
        response = self.get(self.graph.get_connections,\
                self.facebook_id, 
                connection, 
                as_generator=True,
                fields='id', 
                **kwargs)
        result = []
        for page, url in response:
            for item in page:
                result.append(item)
                pass
            pass

        return result

    def filter_object(self, facebook_object):
        """
            filter_object will remove from fields all fields not supported
            by the framework. The parameter is response because most 
            
            facebook_object: dictionary containing Facebook object fields for
                    current object

        
        """
        # metadata information can be requested to identify the type of
        # object to instantiate
        metadata = None
        if 'metatadata' in facebook_object:
            metadata = facebook_object['metadata']

        # Get only fields supported by the framework by removing not
        # supported fields looking in self.fields
        facebook_object_keys = facebook_object.keys()
        for field in facebook_object_keys:
            if field not in self.fields or not self.fields[field]:
                facebook_object.pop(field)

        # Now just fields supported by the framework are remaining. It's
        # time to add metadata information if it has been requested
        if metadata:
            facebook_object['metadata'] = metadata
            pass

        return facebook_object

    def update(self, *args, **kwargs):
        """
            Update the group object
        """

        assert hasattr(self, 'facebook_object'), "call self.get_object first"
        # args is a tuple of positionned arguments
        # kwargs is a dictionary of named arguments
        # assert args, "There should be at list one argument"

        def update_arg(arg):
            """
                For non string values, instantiate a new object
                For instance a group has an owner whos is represented by a
                User object.
                A Post has many comments which are represented by many
                Comment objects
                A comment may have many message tags

            """
            def update_object(Object):
                # Get object ID
                try:
                    facebook_id = Object['id']
                except Exception, e:
                    print Object
                    print 
                    print e
                    import sys
                    sys.exit()

                # Get facebook object with metadata
                facebook_object = \
                        self.graph.get_object(facebook_id,
                                metadata=1)
                
                # Get object type
                object_type = facebook_object['metadata']['type']
                
                # Remove metadata information
                del facebook_object['metadata']

                # Instanciate the object
                Object = Base.factory(object_type,
                        facebook_id,
                        graph=self.graph)
                Object.update(facebook_object)
                
                return Object

            # Update the dictionary with key and values in arg
            references = self.references
            for reference in references:        # For each referenced field
                if reference in arg:            # if referenced field data
                                                # is in arg
                    if references[reference]:   # references[reference]:True
                                                # if the attribute type
                                                # defined in database
                                                # models is list:reference else
                                                # False
                        for i, Object in enumerate(arg[reference]):
                            arg[reference][i] = update_object(Object)
                            pass
                        pass
                    else:                       # references[reference]:False
                        arg[reference] = update_object(arg[reference])
                        pass
                    pass
                pass

            return arg

        # Update the dictionnary with self.facebook_object data
        facebook_object_filtered = self.filter_object(self.facebook_object)
        facebook_object_updated = update_arg(facebook_object_filtered)
        super(Base, self).update(facebook_object_updated)

        # Update the dictionnary with optional positional and keyed
        # arguments
        for arg in args:
            assert hasattr(arg, 'keys'), "Arguments should be iterable"

            arg = self.filter_object(arg)
            arg = update_arg(arg)
        
        if kwargs:
            kwargs = self.filter_object(kwargs)
            kwargs = update_arg(kwargs)
            pass

        # Update, here we call dict.update method
        super(Base, self).update(*args, **kwargs)

        # Add table_fields values
        for field,table_field in self.table_fields.iteritems():
            # table_fields : {facebook_field : table_field}
            # Initialize self[table_field] = self[facebook_field]
            self[table_field] = self[field]
        pass
                    

    def db_update(self, *args, **kwargs):
        # Verify that facebook_object exists
        assert hasattr(self, 'facebook_object'), "call self.get_object() first"

        # Create a dictionnary from the list of table_columns
        data = dict().fromkeys(self.table_columns)

        # Populate the dictionnary with data in self
        for key in data:
            try:
                data[key] = self[key]
            except KeyError, e:
                # Key is missing, not provided
                pass


        # Update kwargs with collected data
        kwargs.update(data)

        if self.exists():
            # if args: there is a key specified for lookup
            if args:
                self.table.update_or_insert(*args, **kwargs)
            else:
                self.table.update_or_insert(**kwargs)

            # Retrieve the record ID in our database
            self.record_id = record_id = \
                    db(self.table.facebook_id ==
                            self.facebook_id).select().first()['id']
            return record_id
        else:
            self.record_id = record_id = self.table.insert(**kwargs)
            return record_id

    def db_truncate(self, *args, **kwargs):
        self.table.truncate()
        pass

    pass

class FcbUser(Base):
    def __init__(self, facebook_id, graph, facebook_table='user'):
        # Update the list of fields for Facebook User
        fields = {
                'first_name':True,        # The URL for the group's icon, string
                'last_name':True,       # Array containing a valid URL, cover_id and image offset. Just the url is kept
                'gender':True,       # The profile that created this group, string
                'username':True, # A brief description of the group, string
                'link': True,       # The URL for the group's website, string
                'locale':True,     # The privacy setting of the group
                'updated_time':True,# The last time the group was updated
                }

        # Update the list of connexions supported by the app

        super(FcbUser, self).__init__(facebook_id, graph=graph, fields = fields,
                facebook_table = facebook_table)

        self.get_object()
        self.update()
        pass

class FcbComment(Base):
    """
        Child class should extend providing:
            reference to object
            list of custom coumns
    """

    def __init__(self, facebook_id, graph, facebook_table, **kwargs):
        # Avoid direct instantiation
        if type(self) == FcbPost:
            raise TypeError, "FcbComment must be subclassed"

        fields = dict()
        table_fields = dict()
        references = dict()
        connections = dict()

        # Update attributes from subclasses
        if 'fields' in kwargs:
            fields.update(kwargs['fields'])
            pass
        if 'table_fields' in kwargs:
            table_fields.update(kwargs['table_fields'])
            pass
        if 'references' in kwargs:
            references.update(kwargs['references'])
            pass
        if 'connections' in kwargs:
            references.update(kwargs['connections'])
            pass

        # Update the list of fields for Facebook Group
        fields.update({
            'from':True,        
            'to':False,
            'message':True,       
            'message_tags':False, 
            'actions':False,
            'application':False,
            'created_time':True,
            'updated_time':True,
            'like_count':False,
            'comment_count':True,
            })

        # Update the list of table_fields

        table_fields.update({
                'id':'facebook_id',
                'from':'facebook_user',
                'to':'facebook_object_to',
                })
        references.update({          # True if attribute.type = list:reference
                                # False if attribute.type = reference
                'facebook_user' : False,   
                'actions':True,
                'with_tags':True,
                'place':False,
                })

        # Update the list of connexions supported by the app
        connections.update({
            'comments': False,
            'likes': False,
            })

        self.graph = graph                          # Initialize facebook.GraphAPI
 
        super(FcbPost, self).__init__(facebook_id, fields=fields, graph=graph, 
                connections=connections, references=references,
                facebook_table = facebook_table, table_fields=table_fields)
   
        self.get_object()
        self.update()

        # Extend self.columns to support non Facebook fields
        # In fact self.columns is built using:
        #   - Supported fields provided by self.fields
        #   - Table fields provided by self.table_fields
        # But there could be extra columns used by a specific framework for
        # linking data and for data management purposes. Thoses columns can
        # be enumerated after initializing the object. 

        pass


class FcbGroupComment(FcbPost):
    """
        Post sent to a group page
    """

    def __init__(self, facebook_id, graph, facebook_table='group_comment'):
        # Update the list of references
        # references are not updated because this attribute defines which
        # facebook fields refer to an object to be created.
        # 
        #references = {
        #        'facebook_group': False,    # This references a facebook
        #                                    # group to which this post is
        #                                    # tied to. False means that
        #                                    # this attribute is not a list
        #                                    # of references
        #        }
        super(FcbGroupPost, self).__init__(facebook_id, graph,
                facebook_table=facebook_table, )

        self.table_columns = [
                'facebook_group_post',
                ]

    def db_update(self, facebook_group):
        # A post has a reference to either a group or an event, in the
        # framework of this work. In other words, a post is an item of the
        # feed which is a list of posts. In our framework only events and
        # groups have a feed. So we have to mention which object we are
        # refering to. The subclass, when instantiated, will define the
        # parent object and its ID which will be used here

        record_id = super(FcbGroupPost,
                self).db_update(facebook_group_post=facebook_group_post)
        return record_id

  

class FcbPost(Base):
    """
        Child class should extend providing:
            reference to object's feed (group, event, ....)
            list of custom columns (adding them to self.table_columns after
            calling base class)

    
    """
    def __init__(self, facebook_id, graph, facebook_table, **kwargs):
        # Avoid direct instantiation
        if type(self) == FcbPost:
            raise TypeError, "FcbPost must be sublcassed"

        fields = dict()
        table_fields = dict()
        references = dict()
        connections = dict()

        # Update attributes from subclasses
        if 'fields' in kwargs:
            fields.update(kwargs['fields'])
            pass
        if 'table_fields' in kwargs:
            table_fields.update(kwargs['table_fields'])
            pass
        if 'references' in kwargs:
            references.update(kwargs['references'])
            pass
        if 'connections' in kwargs:
            references.update(kwargs['connections'])
            pass

        # Update the list of fields for Facebook Group
        fields.update({
            'from':True,        
            'to':False,       
            'message':True,       
            'message_tags':False, 
            'picture': True,       
            'link':True,     
            'caption':True,
            'description': True, 
            'source': True,
            'properties': False, 
            'icon': False,
            'actions':False,
            'privacy':False,
            'type':True,
            'place':True,
            'story':False,
            'story_tags':False,
            'with_tags':False,
            'comments' : False,     
            'object_id':True,
            'application':False,
            'created_time':True,
            'updated_time':True,
            'shares':True,
            'include_hidden':True,
            'status_type':True,
            })

        # Update the list of table_fields

        table_fields.update({
                'id':'facebook_id',
                'from':'facebook_user',
                'to':'facebook_object_to',
                })
        references.update({          # True if attribute.type = list:reference
                                # False if attribute.type = reference
                'facebook_user' : False,   
                'actions':True,
                'with_tags':True,
                'place':False,
                })

        # Update the list of connexions supported by the app
        connections.update({
            'comments': False,
            'likes': False,
            })

        self.graph = graph                          # Initialize facebook.GraphAPI
 
        super(FcbPost, self).__init__(facebook_id, fields=fields, graph=graph, 
                connections=connections, references=references,
                facebook_table = facebook_table, table_fields=table_fields)
   
        self.get_object()
        self.update()

        # Extend self.columns to support non Facebook fields
        # In fact self.columns is built using:
        #   - Supported fields provided by self.fields
        #   - Table fields provided by self.table_fields
        # But there could be extra columns used by a specific framework for
        # linking data and for data management purposes. Thoses columns can
        # be enumerated after initializing the object. 

        self.table_columns = [
                'paging_next',
                'paging_previous',
                'paging_cursor_before',
                'paging_cursor_after',
                ]
        pass

    def get_comments(self):
        self.comments = comments =  self.get_connection('comments')

        return comments

    def set_comments(self):
        assert hasattr(self, 'comments'), "Call self.get_comments first"

        for _comment in self.comments:
            comment = FcbGroupComment(_member['id'], self.graph)
            comment.db_update(self.facebook_id)
            pass
        pass



class FcbGroupPost(FcbPost):
    """
        Post sent to a group page
    """

    def __init__(self, facebook_id, graph, facebook_table='group_post'):
        # Update the list of references
        # references are not updated because this attribute defines which
        # facebook fields refer to an object to be created.
        # 
        #references = {
        #        'facebook_group': False,    # This references a facebook
        #                                    # group to which this post is
        #                                    # tied to. False means that
        #                                    # this attribute is not a list
        #                                    # of references
        #        }
        super(FcbGroupPost, self).__init__(facebook_id, graph,
                facebook_table='group_post', )

        self.table_columns = [
                'facebook_group',
                ]

    def db_update(self, facebook_group):
        # A post has a reference to either a group or an event, in the
        # framework of this work. In other words, a post is an item of the
        # feed which is a list of posts. In our framework only events and
        # groups have a feed. So we have to mention which object we are
        # refering to. The subclass, when instantiated, will define the
        # parent object and its ID which will be used here

        record_id = super(FcbGroupPost,
                self).db_update(facebook_group=facebook_group)
        return record_id

  
class FcbGroup(Base):
    def __init__(self, facebook_id, graph, facebook_table='group'):

        # Update the list of fields for Facebook Group
        fields = {
            'icon':True,        # The URL for the group's icon, string
            'cover':True,       # Array containing a valid URL, cover_id and image offset. Just the url is kept
            'owner':True,       # The profile that created this group, string
            'description':True, # A brief description of the group, string
            'link': True,       # The URL for the group's website, string
            'privacy':True,     # The privacy setting of the group
            'updated_time':True,# The last time the group was updated
            }

        # Update the list of references
        references = {          # True if attribute.type = list:reference
                                # False if attribute.type = reference
                'owner' : False,    
                }

        # Update the list of connexions supported by the app
        connections = {
            'events': False,
            'feed': False,
            'members':True,
            'picture':False,
            'docs':False,
            }

        self.graph = graph                          # Initialize facebook.GraphAPI
 
        super(FcbGroup, self).__init__(facebook_id, fields=fields, graph=graph, 
                connections=connections, references=references,
                facebook_table = facebook_table)
   
        self.get_object()
        self.update()

        pass

    def update(self, *args, **kwargs):
        """
            Update the group object
        """

        assert hasattr(self, 'facebook_object'), "Get object first"
        super(FcbGroup, self).update(self.facebook_object, *args, **kwargs)


    def get_members(self):
        self.members = members = self.get_connection('members')
        
        return members

    def set_members(self):
        assert hasattr(self, 'members'), "Call self.get_members first"

        for _member in self.members:
            member = FcbUser(_member['id'], self.graph)
            member.db_update()
            pass
        pass

    def get_feed(self):
        self.feed = feed = self.get_connection('feed')
        return feed

    def set_feed(self):
        assert hasattr(self, 'feed'), "Call self.get_feed first"

        for _post in self.feed:
            post = FcbGroupPost(_post['id'], self.graph)
            post.db_update(self.facebook_id)
            pass
        pass


    def truncate(self,):
        """
            This will truncate the database table and then remove all data in
            this table and related ones. This is provided to ease debugging.
        """
        pass

    pass
 

def main():

    # Browse https://developers.facebook.com/apps. Then Login in to go to the
    # deveoppers' page of the dummy profile you created for the app

    # Set facebook_group_id
    facebook_group_id = '335662792434'

    # Get access token from facebook

    graph = facebook.GraphAPI(access_token)
    group = FcbGroup(facebook_group_id, graph)

    # Update group information and data. If there is no data in the database, then
    # we pull data instead from Facebook
    # group.update()

if __name__ == '__main__':
    main()
