#/usr/bin/python
# -*- coding: utf-8 -*-

"""

    Springnote API library using OAuth

"""
__author__  = "Jang-hwan Kim"
__email__   = "janghwan at gmail dot com"
__version__ = 0.7

import env 
import oauth, sys, types, re, inspect
import httplib, urllib, socket, os.path

# try importing json: simplejson -> json -> FAIL
try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
        sys.exit("cannot find json library. try installing simplejson")


# default consumer token (as springnote python library)
# you should change this if you want to build your own application
DEFAULT_CONSUMER_TOKEN_KEY    = '162DSyqm28o355V7zEKw'
DEFAULT_CONSUMER_TOKEN_SECRET = 'MtiDOAWsFkH2yOLzOYkubwFK6THOA5iAJIR4MJnwKMQ'

# constants
HOST              = 'api.springnote.com'
REQUEST_TOKEN_URL = 'https://%s/oauth/request_token'           % HOST
ACCESS_TOKEN_URL  = 'https://%s/oauth/access_token/springnote' % HOST
AUTHORIZATION_URL = 'https://%s/oauth/authorize'               % HOST

# default options
default_verbose = False
default_dry_run = False


# exceptions
class SpringnoteError:
    class Base(Exception):
        def __init__(self, error):  self.error = error
        def __str__(self):          return self.error
    class NoNetwork(Base):      pass # if requested without network connection
    class InvalidOption(Base):  pass # if user gave invalid argument
    class ParseError(Base):     pass # if received json is invalid
    class Response(Base): # springnote.com error response
        # status codes and names, extracted from httplib
        http_status_map = {100: 'CONTINUE', 101: 'SWITCHING_PROTOCOLS', 102: 'PROCESSING', 200: 'OK', 201: 'CREATED', 202: 'ACCEPTED', 203: 'NON_AUTHORITATIVE_INFORMATION', 204: 'NO_CONTENT', 205: 'RESET_CONTENT', 206: 'PARTIAL_CONTENT', 207: 'MULTI_STATUS', 226: 'IM_USED', 300: 'MULTIPLE_CHOICES', 301: 'MOVED_PERMANENTLY', 302: 'FOUND', 303: 'SEE_OTHER', 304: 'NOT_MODIFIED', 305: 'USE_PROXY', 307: 'TEMPORARY_REDIRECT', 400: 'BAD_REQUEST', 401: 'UNAUTHORIZED', 402: 'PAYMENT_REQUIRED', 403: 'FORBIDDEN', 404: 'NOT_FOUND', 405: 'METHOD_NOT_ALLOWED', 406: 'NOT_ACCEPTABLE', 407: 'PROXY_AUTHENTICATION_REQUIRED', 408: 'REQUEST_TIMEOUT', 409: 'CONFLICT', 410: 'GONE', 411: 'LENGTH_REQUIRED', 412: 'PRECONDITION_FAILED', 413: 'REQUEST_ENTITY_TOO_LARGE', 414: 'REQUEST_URI_TOO_LONG', 415: 'UNSUPPORTED_MEDIA_TYPE', 416: 'REQUESTED_RANGE_NOT_SATISFIABLE', 417: 'EXPECTATION_FAILED', 422: 'UNPROCESSABLE_ENTITY', 423: 'LOCKED', 424: 'FAILED_DEPENDENCY', 426: 'UPGRADE_REQUIRED', 443: 'HTTPS_PORT', 500: 'INTERNAL_SERVER_ERROR', 501: 'NOT_IMPLEMENTED', 502: 'BAD_GATEWAY', 503: 'SERVICE_UNAVAILABLE', 504: 'GATEWAY_TIMEOUT', 505: 'HTTP_VERSION_NOT_SUPPORTED', 507: 'INSUFFICIENT_STORAGE', 510: 'NOT_EXTENDED'}

        def __init__(self, response, msg=None):
            self.msg    = msg
            self.status = response.status
            self.error  = response.read()
            try:                # parse json
                self.error = json.loads(self.error)
            except ValueError:  # handle non-json messages
                if '<html' in self.error and 'http-equiv="Content-Type"' in self.error and 'content="text/html;charset=UTF-8"' in self.error:
                    if   self.status == httplib.INTERNAL_SERVER_ERROR:  self.error = "Invalid Action"
                    elif self.status == httplib.NOT_FOUND:              self.error = "Not Found"
        def __str__(self):
            msg  = `self.status` +" "+ self.http_status_map[self.status]
            msg += self.format_body(self.error)
            if self.msg: 
                msg += ", " + self.msg
            return msg
        def format_body(self, e):
            if   isinstance(e, types.ListType): return "\n".join(map(self.format_body, e))
            elif isinstance(e, types.DictType): return " - %s: %s" % (e["error"]["error_type"], e["error"]["description"])
            else:                               return ": %s" % e

def is_verbose(verbose):
    if verbose is True or (verbose is None and default_verbose is True):
        return True
    return False
def is_file_type(data):
    ''' needs data.name and data.read() to act as a file '''
    if hasattr(data, 'name') and hasattr(data, 'read') and callable(data.read):
         return True
    return False


class Springnote(object):
    ''' handles every kind of requests sent to springnote.com, both 
    Authentication and Resources, using OAuth. '''
    signature_method       = oauth.OAuthSignatureMethod_HMAC_SHA1()
    BOUNDARY               = 'AaB03x' 
    DEFAULT_CONTENT_TYPE   = 'application/json'
    MULTIPART_CONTENT_TYPE = 'multipart/form-data; boundary=%s' % BOUNDARY

    def __init__(self, access_token=None, consumer_token=(DEFAULT_CONSUMER_TOKEN_KEY, DEFAULT_CONSUMER_TOKEN_SECRET), verbose=None):
        """ intialize consumer token, and optioanlly an access token.
        
        If consumer token is not given, it uses basic consumer token (registered 
        for the library itself). However, you need to specify the access token, 
        either previously saved or acquired through user authorization later on,
        to request the resources """
        self.consumer_token = self.format_token(consumer_token)
        self.set_access_token(access_token)

        self.verbose = verbose

    def set_access_token(self, *args):
        """ sets the access token. 
        can take various formats, arguments of strings, a tuple of key and 
        secret, or a class with .key and .secret attribute
        
        >> sn = Springnote()
        >> sn.set_access_token(('SOME_ACCESS', 'TOKEN'))
        <oauth.OAuthToken object ...>
        >> token = sn.set_access_token('SOME_ACCESS', 'TOKEN')
        <oauth.OAuthToken object ...>
        >> sn.set_access_token(token)
        <oauth.OAuthToken object ...>
        """
        self.access_token = self.format_token(*args)
        return self.access_token

    def fetch_request_token(self, verbose=None):
        """ fetch a request token from springnote.com as a consumer application

        need to use:
         1. POST method. do not use GET
         2. HTTPS connection
         3. HMAC-SHA1 as signature method
         4. no token to sign but consumer token

        >> request_token = Springnote.fetch_request_token()
        """
        response = self.springnote_request(
            'POST', url=REQUEST_TOKEN_URL,
            secure=True, sign_token=None, verbose=verbose)

        # parse request token
        if default_dry_run:
            return oauth.OAuthToken('FAKE_REQUEST_TOKEN_KEY', 'FAKE_REQUEST_TOKEN_SECRET')

        if response.status != httplib.OK:
            raise SpringnoteError.Response(response, 'make sure to use POST and HTTPS without any sign token')
        request_token = oauth.OAuthToken.from_string(response.read())

        if is_verbose(verbose):
            print "<< request token:", (request_token.key, request_token.secret)

        return request_token
    
    def authorize_url(self, request_token, verbose=None, callback=None):
        """ returns URL that user has to visit and authorize to get access token """
        params = { "oauth_token": request_token.key }
        if callback:
            params["oauth_callback"] = callback
    
        url = "%s?%s" % (AUTHORIZATION_URL, urllib.urlencode(params))
        return url
    
    def fetch_access_token(self, request_token, verbose=None):
        """ fetch access token from springnote.com with authorized request token

        need to:
         1. use POST method. do not use GET
         2. use HTTPS connection
         3. let user authorize request token
         4. HMAC-SHA1 as signature method
         5. sign with the request token with consumer token
        
        >> access_token = Springnote.fetch_access_token(request_token)
        """
        # request to springnote.com
        response = self.springnote_request(
            'POST', ACCESS_TOKEN_URL, 
            sign_token=request_token, secure=True, verbose=verbose)
    
        if response.status != httplib.OK:
            raise SpringnoteError.Response(response, 'make sure to use POST, HTTPS and sign with request token authorized by user')
    
        access_token = oauth.OAuthToken.from_string(response.read())
        self.set_access_token(access_token)
        return self.access_token

    @staticmethod
    def format_token(*args):
        """ handles various formats of tokens """
        # (('KEY', 'SECRET'))
        if len(args) == 1 and getattr(args[0], '__len__', False):
            args = args[0]

        # ('KEY', 'SECRET')
        if len(args) == 2:
            token, key = args
            return oauth.OAuthToken(token, key)

        # any object that responds to 'key' and 'secret'
        if len(args) == 1 and \
            getattr(args[0], 'key', False) and getattr(args[0], 'secret', False):
                return oauth.OAuthToken(args[0].key, args[0].secret)
        return

    def oauth_request(self, method, url, params=None, sign_token=None, verbose=False):
        ''' generates OAuth request, which is inserted in headers at springnote_request '''
        sign_token = self.format_token(sign_token or self.access_token)
        request = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer_token, sign_token, method, url, params or {})
        request.sign_request(Springnote.signature_method, self.consumer_token, sign_token)

        if is_verbose(verbose):
            print '>> oauth:'
            print ' * signature method :', Springnote.signature_method.get_name()
            print ' * consumer token :', (self.consumer_token.key, self.consumer_token.secret)
            print ' * sign token :', sign_token #(sign_token.key, sign_token.secret)

            print '>> oauth parameters:'
            for key in sorted(request.parameters.keys()):
                print " *", key, ':', request.parameters[key]

        return request

    def springnote_request(self, method, url, params={}, headers=None, body=None, 
            sign_token=None, secure=False, verbose=False):
        """ sends a request to springnote.com. Used in every case to communicate 
        with springnote.com, including both authentication and requesting for 
        springnote resources.

        sign_token is only None when first fetching a request token, uses request 
        token until it fetches an access token, and uses access token to fetch 
        the resources.

        secure is only True during authorization, and must be False at resource 
        request.

        >>> access_token = oauth.OAuthToken('key', 'secret')
        >>> http_response = Springnote(access_token).springnote_request( \
                "GET", "http://url.com/path")
        """
        oauth_request = self.oauth_request(method, url, params, \
            sign_token=(sign_token or self.access_token), verbose=verbose)

        headers = Springnote.set_headers(headers, oauth_request, method, body)
        body    = Springnote.set_body(body)

        if is_verbose(verbose):
            print '>> header:'
            for key, value in headers.iteritems():
                print " *", key, ':', value

            if body:
                print '>> body:'
                print `body`

            print '>> request:'
            print oauth_request.http_method, oauth_request.http_url
            print 'header:', headers
            if body: print 'body:', `body`
            print

        # create http(s) connection and request
        if is_verbose(verbose) and secure: print 'using HTTPS'
        if secure:  conn = httplib.HTTPSConnection(HOST)
        else:       conn = httplib.HTTPConnection(HOST)

        # request
        if default_dry_run: return
        try:
            conn.request(oauth_request.http_method, oauth_request.http_url, 
                        body=body, headers=headers)
        except socket.gaierror:
            raise SpringnoteError.NoNetwork("cannot reach '%s'" % oauth_request.http_url)
        return conn.getresponse()

    @staticmethod
    def set_headers(headers, oauth_request, method, body):
        headers = headers or {}
        content_type = Springnote.DEFAULT_CONTENT_TYPE
        if method != "GET" and is_file_type(body): # when POST or PUT attachment
            content_type = Springnote.MULTIPART_CONTENT_TYPE
        headers.setdefault('Content-Type', content_type)
        #    headers.setdefault('Content-Type', Springnote.MULTIPART_CONTENT_TYPE)
        ## normal
        #else:
        #    headers.setdefault('Content-Type', Springnote.DEFAULT_CONTENT_TYPE)
        headers.update(oauth_request.to_header())
        return headers

    @staticmethod
    def wrap_file_to_body(data, boundary=BOUNDARY):
        if is_file_type(data):
            data = "\r\n".join([
                '--%s' % boundary,
                'Content-Disposition: form-data; name="Filedata"; filename="%s"' % data.name,
                'Content-Transfer-Encoding: binary',
                'Content-Type: application/octet-stream',
                '',
                data.read(),
                '--%s--' % boundary,
            ])
        return data
    set_body = wrap_file_to_body


##
## -- OOP layer
##
class SpringnoteResource(object):
    """ abstract class for resources used in springnote. Page, Attachment and the
    rest inherits this class.
    provides various wrapper methods that calls Springnote.springnote_request().
    """
    springnote_attributes = []            # springnote attributes for each resource
    request_methods       = ['request']   # request methods for each resource

    def __init__(self, auth, parent=None):
        self.auth   = auth    # has .access_token and .consumer_token
        self.parent = parent  # parent Page object
        self.raw    = ''      # raw data fetched from request
        for attr in self.springnote_attributes:
            setattr(self, attr, None)
        return

    # consider `id' as an alias of `identifier'
    def _set_id(self, id):
        if hasattr(self, 'identifier'): self.identifier = id
        else:                           setattr(self, 'id', id)
    def _get_id(self):
        if   hasattr(self, 'identifier'): return self.identifier
        elif hasattr(self, 'id'):         return self.id
        else:   
            error_msg = "'%s' object has no attribute 'id'" % self.__class__.__name__
            raise AttributeError(error_msg)
    id = property(_get_id, _set_id)

    def request(self, path, method="GET", params={}, headers=None, data=None, 
                process_response=True, verbose=None):
        ''' calls handle_request and build resource from output '''
        if data:
            data = self.to_json()
        instance = self.handle_request(auth=self.auth, parent=self.parent,
                    path=path, method=method, params=params, headers=headers, 
                    data=data, process_response=process_response, verbose=verbose)
        self.replace_with(instance)
        return self

    @classmethod
    def handle_request(cls, auth, parent, path, method="GET", params={}, 
                headers=None, data=None, process_response=True, verbose=None):
        """ send request to springnote.com and create resource from response.
            used by every subclass of SpringnoteResource 
            
        note that HTTPS won't work. always use HTTP """

        url  = "http://%s/%s" % (HOST, path.lstrip('/'))
        use_https = False       # this should always be False

        if is_verbose(verbose):
            print '>> content'
            print ' * HTTP method:', method
            print ' * params:',      params
            print ' * path:',        path
            print ' * url:',         url
            print ' * headers:',     headers
            print ' * data:',        data

        # send request
        response = Springnote(auth.access_token, auth.consumer_token) \
            .springnote_request(
                method  = method,
                url     = url,
                params  = params,
                headers = headers,
                body    = data,
                secure  = use_https, 
                verbose = verbose
        )

        if default_dry_run: return
        if response.status != httplib.OK:
            raise SpringnoteError.Response(response, 'failed to %s %s' % (method,url))

        # handle response
        data = response.read()
        if not process_response: 
            new_instance = cls(auth=auth, parent=parent)
            new_instance.raw = data
            return new_instance
        return cls.from_json(data, auth, parent, verbose=verbose)

    def to_json(self):
        ''' wraps data into json format '''
        # set data in json format (ex. {'page': {'title': 'some title here' ..}}
        data = {}
        for attr in getattr(self, 'writable_attributes', self.springnote_attributes):
            value = getattr(self, attr, False)
            if value:
                data[attr] = value
        data = {self.__class__.__name__.lower(): data}
        # json
        data = json.dumps(data, ensure_ascii=False)
        # encode to utf-8
        if type(data) == str: 
            data = data.decode('utf-8')
        data = data.encode('utf-8')
        return data

    @classmethod
    def from_json(cls, data, auth, parent=None, verbose=None): 
        """ create and return new resource object from given json string

          * raw     : stores json response itself
          * resource: stores converted json response (dictionary)
        """
        if is_verbose(verbose):
            print '<< data:'
            print data
            print

        # build proper object
        object_name = cls.__name__.lower() # Page => 'page'
        try:
            structure = json.loads(data)
        except ValueError:
            raise SpringnoteError.ParseError('unable to load json: ' + `data`)

        if isinstance(structure, types.DictType):
            # build single data - {'page': {'id':3}}
            if object_name in structure:
                new_instance = cls(auth=auth, parent=parent)
                new_instance.raw = data

                # process resource specific tasks
                new_instance._set_resource(structure[object_name])
                return new_instance

            # wrap with object name if not given and retry - {'id':3}
            else:
                wrapped_data = '{"%s": %s}' % (object_name, data)
                new_instance = cls.from_json(wrapped_data, auth, parent, verbose=verbose)
                new_instance.raw = data
                return new_instance

        # build multiple resources - [{'page': {'id':3}}, {'page': {'id':4}}]
        elif type(structure) is list:
            build = lambda d: cls.from_json(json.dumps(d, ensure_ascii=False),
                        auth=auth, parent=parent, verbose=verbose)
            return map(build, structure)

        raise SpringnoteError.ParseError('unable to build resource from: ' + data)

    def replace_with(self, obj):
        ''' build attributes from object given, ignoring improper values '''
        for attr in dir(obj):
            value = getattr(obj, attr, None)
            # XXX: this seems dirty, doesn't it?
            if callable(value):         continue
            if attr.startswith('__'):   continue

            if value is not None:
                setattr(self, attr, value)
        del obj
        return self

    @staticmethod
    def _to_unicode(s):
        ''' '\\uc2a4\\ud504\\ub9c1\\ub178\\ud2b8' => u"스프링노트" '''
        #return eval('u"""%s"""' % s)
        def repl(match): 
            return unichr(int(match.group(1), 16))
        return re.sub(r"\\u([0-9a-fA-F]{4})", repl, s)


    def _set_resource(self, resource_dict):
        """ absorbs the dictionary data into its attributes """
        for key in self.springnote_attributes:
            # key may not exist in given dictionary. skip
            if key not in resource_dict:
                continue
            # set value
            value = resource_dict[key]
            # convert to unicode if string value
            if isinstance(value, types.StringTypes):
                value = self._to_unicode(value)
            setattr(self, key, value)
    def _get_resource(self):
        resource_dict = {}
        for key in self.springnote_attributes:
            resource_dict[key] = getattr(self, key)
        return resource_dict
    resource = property(_get_resource, _set_resource)

    def requires_value_for(self, *attribute_names):
        """ check value for given attribute names, raise exception if none.

        allows
         - recursive attribute names like 'parent.id' 
         - OR operation like ('id', 'index) 
         - (parent.id, (id,index)) requires parent.id AND (id OR index)
        """
        # format error message
        error_msg = []
        for name in attribute_names:        
            if isinstance(name, types.StringTypes): error_msg.append("'%s'" % name)
            elif isinstance(name, types.TupleType): error_msg.append("one of " + " or ".join(map(lambda x: "'%s'" % x, name)))
        error_msg = " and ".join(error_msg)
        error_msg = "needs %s to perform the request" % error_msg
        # check value for names 
        for name_tuple in attribute_names:
            if isinstance(name_tuple, types.StringTypes): name_tuple = (name_tuple,)
            # breaks if any name is found True
            anyTrue = False
            for name in name_tuple:             # name_tuple: (id, index)
                value = self
                # breaks if any subname is found False
                for subname in name.split('.'): # parent.id => (parent, id)
                    if not hasattr(value, subname) or getattr(value, subname) is None:
                        error_msg = "needs proper value in %s. " % name + error_msg
                        break
                    value = getattr(value, subname) # update value
                # checked every subname but was okay. can ignore other names
                else:
                    anyTrue = True
                    break
            # checked every name in tuple but none succeeded
            else:
                raise SpringnoteError.InvalidOption(error_msg)
        return True

    @classmethod
    def _set_path_params(cls, page, id=None, params={}, format=True, plural=True):
        ''' default method to build proper path and parameters.

        - page  : has page.id and page.note     (pages/123?domain=jangxyz)
        - id    : resource id, except for Page  (pages/123/attachments/456)
        - params: default params                (pages?sort=title)
        - plural: remove suffix 's' on resource name if False (pages/123/lock)
        - format: add '.json' to path if True   (pages.json)
        '''
        # path for page
        path = "/pages"
        if page.id:     path += "/%d" % page.id # /pages/123

        # path for additional resource, if any
        if cls is not Page: 
            if cls:     path += "/%s" % cls.__name__.lower()  # ../attachment
            if plural:  path += 's'             # ../attachments
            if id:      path += "/%d"  % id     # ../attachments/456
        if format:      path += ".json"         # ../attachments/456.json

        # update parameters
        params['note'] = page.note
        params = cls._update_params(params.copy())

        # apply parameters to path
        if params:  
            path += "?%s" % urllib.urlencode(params)

        return (path, params)

    @classmethod
    def _update_params(cls, kwarg):
        ''' default behaviour of processing parameters

        1. there is no 'note' parameter. change it to 'domain'
        2. remove None values '''
        kwarg['domain'] = kwarg.pop('note', None)
        params = {}
        for k,v in filter(lambda (k,v): v, kwarg.iteritems()):
            params[k] = kwarg[k]
        return params


class Page(SpringnoteResource):
    """ 스프링노트의 page에 대한 정보를 가져오거나, 수정할 수 있습니다.
        page의 하위 리소스에 접근할 수 있도록 해줍니다. """

    springnote_attributes = [ 
        "identifier",           # 페이지 고유 ID  예) 2
        "date_created",         # 페이지 최초 생실 일시(UTC)  예) datetime.datetime(2008, 1, 30, 10, 11, 16)
        "date_modified",        # 페이지 최종 수정 일시(UTC)  예) datetime.datetime(2008, 1, 30, 10, 11, 16)
        "rights",               # 페이지에 설정된 Creative Commons License  예) by-nc
        "creator",              # 페이지 소유자 OpenID
        "contributor_modified", # 최종 수정자 OpenID
        "title",                # 페이지 이름  예) TestPage
        "source",               # 페이지 원본.  예) &lt;p&gt; hello &lt;/p&gt; 
        "relation_is_part_of",  # 이 페이지의 부모 페이지의 ID  예) 2
        "tags"                  # 페이지에 붙은 태그  예) tag1,tag2
    ]
    writable_attributes = ["title", "source", "relation_is_part_of", "tags"]
    # arguments to check parameter validity
    check_parameters = { 
        'sort'     : lambda x: x in ['identifier', 'title', 'relation_is_par_of', 'date_modified', 'date_created'],
        'order'    : lambda x: x in ['desc', 'asc'],
        'offset'   : lambda x: types.IntType(x),
        'count'    : lambda x: types.IntType(x),
        'parent_id': lambda x: types.IntType(x),
        'q'        : lambda x: types.UnicodeType(x),
        'tags'     : lambda x: types.UnicodeType(x),
        'identifiers': lambda x: re.match("([0-9]+,)*[0-9]+", str(x)).group(0), 
    }
    request_methods = ['get', 'save', 'delete', 'list', 
        'search', 'get_root', 'get_parent', 'get_children',
    ]

    def __init__(self, auth, id=None, note=None, 
            title=None, source=None, relation_is_part_of=None, tags=None,
            parent=None):
        SpringnoteResource.__init__(self, auth)
        # 
        self.note   = note
        # springnote attributes
        self.id     = id
        self.title  = title
        self.source = source
        self.tags   = tags
        self.relation_is_part_of = relation_is_part_of

    @classmethod
    def _set_path_params(cls, page=None, **kwarg):
        ''' format path and params, according to page id and note '''
        page      = page      or Page(None)
        page.id   = kwarg.pop('id' , None) or page.id
        page.note = kwarg.pop('note', None) or page.note
        return super(Page, cls)._set_path_params(page, params=kwarg)

    @classmethod
    def _update_params(cls, kwarg):
        ''' update parameters from given dictionary, used in page listing. 
        checks for validity '''
        params = SpringnoteResource._update_params(kwarg.copy())
        for key, value in kwarg.iteritems():
            if key not in cls.check_parameters:
                continue

            check_method = cls.check_parameters[key]
            error_msg = "%s is not allowed for %s" % (value, key)
            try:
                correct_result = check_method(value)
                if not correct_result:
                    raise SpringnoteError.InvalidOption(error_msg)
                # apply value if result is True
                elif correct_result is True:
                    params[key] = value 
                # otherwise save the result value
                else:
                    params[key] = correct_result
            except:
                raise SpringnoteError.InvalidOption(error_msg)
        return params

    def writable_resource(self): 
        data = {}
        for attr in self.writable_attributes:
            value = getattr(self, attr, False)
            if value:
                data[attr] = value
        return data

    # -- 
    def get(self, verbose=None):
        """ fetch the page with current id. 
        hence the page instance MUST have id attribute """
        self.requires_value_for('id')
        path, params = self._set_path_params(self, id=self.id, note=self.note)
        return self.request(path, "GET", params=params, verbose=verbose)

    def save(self, verbose=None):
        """ save current page, either create or update.
        create a new page if there is no id, while update if given.
        ungiven parameters are ignored, not removed """
        if self.id: method = "PUT"  # update existing page
        else:       method = "POST" # create new page
        path, params = self._set_path_params(self, id=self.id, note=self.note)
        data = self.writable_resource()
    
        self.request(path, method, params=params, data=data, verbose=verbose)
        return self

    def delete(self, verbose=None):
        """ delete the page """
        self.requires_value_for('id')
        path, params = self._set_path_params(self, id=self.id, note=self.note)
        return self.request(path, "DELETE", params=params, verbose=verbose)

    @classmethod
    def list(cls, auth, note=None, verbose=None, **kwarg):
        ''' get list of pages that match the criteria
        
        NOTE: not all attributes are loaded, only the following are:
            [title, relation_is_part_of, uri, identifier, date_modified]
        '''
        kwarg.update(id=None)
        if note: kwarg.update(note=note)

        path, params = Page._set_path_params(**kwarg) # ignores id
        pages = cls.handle_request(auth, None, path, "GET", params, 
                                    verbose=verbose)

        # connect parents
        page_dictionary = {}
        [page_dictionary.setdefault(page.id, page) for page in pages]
        for page in pages:
            page.parent = page_dictionary.get(page.relation_is_part_of, None)

        return pages

    # additional methods
    @classmethod
    def search(cls, auth, query, note=None, verbose=None, **kwarg):
        ''' search page for given query. using list() method '''
        kwarg.update(q=query)
        return cls.list(auth, note=note, verbose=verbose, **kwarg)

    @classmethod
    def get_root(cls, auth, note=None, verbose=None):
        ''' get root page, using list() method
        
        NOTE: not all attributes are loaded, only the following are:
            [title, relation_is_part_of, uri, identifier, date_modified]
        '''
        pages = cls.list(auth, note=note, verbose=verbose)
        root_page = filter(lambda p: p.relation_is_part_of is None, pages)[0]
        return root_page

    def get_parent(self, verbose=None):
        ''' get parent page, using get(id=) method '''
        if self.relation_is_part_of:
            self.parent = Page(self.auth, id=self.relation_is_part_of).get(verbose=verbose)
            return self.parent

    def get_children(self, verbose=None):
        ''' get children pages, using list(parent_id=) method '''
        children = Page.list(self.auth, parent_id=self.id, verbose=verbose)
        for page in children:   
            page.parent = self
        return children


class Attachment(SpringnoteResource):
    springnote_attributes = [ 
        "identifier",          # 첨부 고유 ID 예) 2
        "title",               # 첨부 파일 이름 예) test.jpg
        "description",         # 첨부 파일 크기(단위는 바이트) 예) 8000
        "date_created",        # 첨부 최초 생성 일시(UTC) 예) 2008-01-30T10:11:16Z
        "relation_is_part_of", # 첨부 파일이 속한 페이지의 ID 예) 1
    ]
    request_methods = ['list', 'get', 'upload', 'download', 'delete']
    def __init__(self, parent, id=None, filename=None, file=None, auth=None):
        SpringnoteResource.__init__(self, auth or parent.auth, parent=parent)
        self.id = id
        self.relation_is_part_of = parent.id

        # file attributes
        self.title = filename
        self.content, self.description, self.date_created = None, None, None
        if file:     
            self._set_file(file)

    def _set_file(self, file):
        ''' set title, content, description '''
        self.title       = file.name
        self.content     = file.read()
        self.description = len(self.content)
    def _get_file(self):
        ''' return a fake file object with name and read() it '''
        class File: 
            def __init__(self, name, content):
                self.name = name
                self.read = lambda: content
            #def __eq__(self, file_object):
            #    try:
            #        return self.name == file_object.name and \
            #            self.read() == file_object.read()
            #    except:
            #        return False
        if self.title and self.content:
            return File(self.title, self.content)
        return None
    file = property(_get_file, _set_file)

    def to_json(self):
        ''' Attachment.to_json only needs to wrap file object into json '''
        return Springnote.wrap_file_to_body(self.file)
            
    @classmethod
    def list(cls, page, auth=None, verbose=None):
        path, params = Attachment._set_path_params(page)
        return cls.handle_request(auth or page.auth, page,
                                    path, "GET", params, verbose=verbose)

    def get(self, verbose=None):
        """ reload the metadata of attachment, but not the file itself. 
        requires id and parent.id """
        self.requires_value_for('id', 'parent.id')
        path, params = self._set_path_params(self.parent, self.id, format=True)
        self.request(path, "GET", params, verbose=verbose)

    def download(self, filename=None, verbose=None):
        """ fetch the attachment file. requires id and parent.id """
        self.requires_value_for('id', 'parent.id')
        path, params = self._set_path_params(self.parent, self.id, format=False)
        self.request(path, "GET", params, process_response=False, verbose=verbose)
        self.content = self.raw

        return self

    def delete(self, verbose=None):
        """ delete the attachment. requires id and parent.id """
        self.requires_value_for('id', 'parent.id')
        path, params = Attachment._set_path_params(self.parent, self.id)
        return self.request(path, "DELETE", params=params, verbose=verbose)

    def upload(self, verbose=None):
        """ upload a file as attachment. requires file and parent.id

        if id is given, it updates an existing file
        if not,         creates a new file """
        self.requires_value_for('parent.id', 'file')
        if self.id:  method = "PUT"   # update existing attachment
        else:        method = "POST"  # create new attachment

        path, params = Attachment._set_path_params(self.parent, id=self.id)
        headers = {'Content-Type': Springnote.MULTIPART_CONTENT_TYPE}
        return self.request(path, method, params=params, headers=headers, 
                            data=self.file, verbose=verbose)


class Comment(SpringnoteResource):
    springnote_attributes = [ 
        "identifier",          # 고유 ID 예) 1
        "date_created",        # 최초 생성 일시(UTC)예) 2008-01-30T10:11:16Z
        "relation_is_part_of", # 첨부 파일이 속한 페이지의 ID 예) 1
        "creator",             # 작성자 nickname
        "source",              # 내용
    ]
    request_methods = ['list']

    def __init__(self, parent, auth=None):
        SpringnoteResource.__init__(self, auth or parent.auth, parent=parent)
        self.relation_is_part_of = parent.id

    @classmethod
    def list(cls, page, auth=None, verbose=None):
        path, params = cls._set_path_params(page)
        return cls.handle_request(auth or page.auth, page,
                                    path, "GET", params, verbose=verbose)

class Collaboration(SpringnoteResource):
    springnote_attributes = [ 
        "rights_holder", # 협업자의 OpenID
        "access_rights", # 협업자가 가진 권한 예) reader, writer, guest, creator
        "date_created",  # 협업을 시작한 시간(UTC) 예) 2008-01-30T10:11:16Z
    ]
    request_methods = ['list']

    def __init__(self, parent, auth=None):
        SpringnoteResource.__init__(self, auth or parent.auth, parent=parent)
        self.relation_is_part_of = parent.id

    @classmethod
    def list(cls, page, auth=None, verbose=None):
        path, params = cls._set_path_params(page, plural=False)
        return cls.handle_request(auth or page.auth, page,
                                    path, "GET", params, verbose=verbose)


class Lock(SpringnoteResource):
    springnote_attributes = [ 
        "creator",             # 현재 페이지를 수정중인 사용자 OpenID
        "date_expired",        # 잠금이 해제되는 (예상) 시간(UTC) 예) 2008-01-30T10:11:16Z
        "relation_is_part_of", # 잠금 리소스가 속한 페이지의 ID
    ]
    request_methods = ['get', 'acquire']

    def __init__(self, parent, auth=None):
        SpringnoteResource.__init__(self, auth or parent.auth, parent=parent)
        self.relation_is_part_of = parent.id

    def get(self, verbose=None):
        """ fetch status of lock """
        self.requires_value_for('parent.id')
        path, params = self._set_path_params(self.parent, plural=False)
        return self.request(path, "GET", params, verbose=verbose)

    def acquire(self, verbose=None):
        """ try to acquire a lock to edit page (POST) """
        self.requires_value_for('parent.id')
        path, params = self._set_path_params(self.parent, plural=False)
        return self.request(path, "POST", params, verbose=verbose)

class Revision(SpringnoteResource):
    # there is no 'date_modified', 'contributor_modified', 'rights', and 'tags'
    springnote_attributes = [ 
        "identifier",          # 히스토리 고유 ID
        "creator",             # 만든 사람 OpenID
        "date_created",        # 생성된 시간(UTC) 예) 2008-01-30T10:11:16Z
        "relation_is_part_of", # 히스토리가 속한 페이지의 ID
        "source",              # 페이지 내용          -- only at get()
        "description",         # 히스토리에 대한 설명 -- only at list()
    ]
    request_methods = ['get', 'list']

    def __init__(self, parent, index=None, id=None, auth=None):
        SpringnoteResource.__init__(self, auth or parent.auth, parent=parent)
        self.id = id
        self.relation_is_part_of = parent.id
        self.index = index

    @classmethod
    def list(cls, page, auth=None, verbose=None):
        ''' get list of page revisions

        NOTE: not all attributes are loaded, only the following are:
            [ date_created, identifier, description, creator ]
        ''' 
        path, params = cls._set_path_params(page)
        return cls.handle_request(auth or page.auth, page,
                                    path, "GET", params, verbose=verbose)

    def get(self, verbose=None):
        ''' get specific revision of a page 
        
        if id is given then fetch the corresponding rev, or
        if index is given first fetch the entire revision list, 
        sort it by create_date and fetch the index-th rev.
        '''
        self.requires_value_for('parent.id', ('id','index'))
        if self.id is None:
            revs = self.list(self.parent, verbose=verbose)
            revs = sorted(revs, key=lambda x: x.date_created)
            if len(revs) < - self.index:
                error_msg = "there is no %d-th revision, only %d" % (self.index, len(revs))
                raise SpringnoteError.InvalidOption(error_msg)
            self.id = revs[self.index].id
        path, params = self._set_path_params(self.parent, id=self.id)
        return self.request(path, "GET", params, verbose=verbose)


# black-and-white magic: dynamically build methods into class
def run_resource_method(parent, function_name, resource, method_name, *args, **kwarg):
    ''' detach function_name and call appropriate resource.method(parent) '''
    method  = getattr(resource, method_name)
    verbose = kwarg.pop('verbose', None)
    if method.im_self is None:                      # instance method
        instance = resource(parent, *args, **kwarg)
        method   = getattr(instance, method_name)
        return method(verbose=verbose)
    else:                                           # class method
        method = getattr(resource, method_name)
        return method(parent, verbose=verbose, *args, **kwarg)
def register_request_methods(parent, *children):
    ''' binds request methods from children resources to the parent resource.

    read request methods from children resources, and
    generate a 'request_resource' style method and bind it to the parent.

    examples:
     * page.get_attachment()        is  Attachment(page).get()
     * sn.list_pages(verbose=True)  is  Page.list(sn, verbose=True)
    '''
    def generate_method(method_name, resource, method):
        return lambda parent, *args, **kwarg: \
                    run_resource_method(parent, method_name, resource, method, 
                                            *args, **kwarg)
    #
    for child in children:                              # eg, Attachment
        for request_method in child.request_methods:    # eg, 'download'
            method_name = request_method + "_" + child.__name__.lower()
            # add '-s' to classmethods. eg, 'list_attachments'
            if getattr(child, request_method).im_self:
                method_name += "s"

            method = generate_method(method_name, child, request_method)
            setattr(parent, method_name, method)     # eg, Page.get_lock
            setattr(method, '__name__', method_name) # eg, Page.get_lock.__name__

# bind request methods to parent resource
register_request_methods(Springnote, Page)
register_request_methods(Page, Attachment, Comment, Lock, Revision, Collaboration)

