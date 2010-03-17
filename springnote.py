#/usr/bin/python
# -*- coding: utf-8 -*-

"""

    Springnote API library using OAuth

"""
__author__  = "Jang-hwan Kim"
__email__   = "janghwan at gmail dot com"
__version__ = 0.5

import env 

import oauth, sys, types
import simplejson as json
import httplib, urllib, socket

# default consumer token (as springnote python library)
# you should not use this if you want to build your own application
DEFAULT_CONSUMER_TOKEN_KEY    = '162DSyqm28o355V7zEKw'
DEFAULT_CONSUMER_TOKEN_SECRET = 'MtiDOAWsFkH2yOLzOYkubwFK6THOA5iAJIR4MJnwKMQ'

default_verbose = False
default_dry_run = False

class SpringnoteError:
    class Base(Exception):
        def __init__(self, error):
            self.error = error
        def __str__(self):
            error_tuple = lambda x: (x["error"]["error_type"], x["error"]["description"])
            error_tuple_str = lambda x: "%s: %s" % error_tuple(x)
            if isinstance(self.error, dict):
                return error_tuple_str(self.error)
            elif isinstance(self.error, list):
                error_msgs = [error_tuple_str(error) for error in self.error]
                return '\n'.join(error_msgs)
            else:
                return self.error
    class InvalidOption(Base): pass
    class ParseError(Base):   pass
    class Unauthorized(Base): pass
    class NotFound(Base):     pass
    class Network(Base):      pass

    class Response(Base):
        # status codes and names, extracted from httplib
        status_map = {100: 'CONTINUE', 101: 'SWITCHING_PROTOCOLS', 102: 'PROCESSING', 200: 'OK', 201: 'CREATED', 202: 'ACCEPTED', 203: 'NON_AUTHORITATIVE_INFORMATION', 204: 'NO_CONTENT', 205: 'RESET_CONTENT', 206: 'PARTIAL_CONTENT', 207: 'MULTI_STATUS', 226: 'IM_USED', 300: 'MULTIPLE_CHOICES', 301: 'MOVED_PERMANENTLY', 302: 'FOUND', 303: 'SEE_OTHER', 304: 'NOT_MODIFIED', 305: 'USE_PROXY', 307: 'TEMPORARY_REDIRECT', 400: 'BAD_REQUEST', 401: 'UNAUTHORIZED', 402: 'PAYMENT_REQUIRED', 403: 'FORBIDDEN', 404: 'NOT_FOUND', 405: 'METHOD_NOT_ALLOWED', 406: 'NOT_ACCEPTABLE', 407: 'PROXY_AUTHENTICATION_REQUIRED', 408: 'REQUEST_TIMEOUT', 409: 'CONFLICT', 410: 'GONE', 411: 'LENGTH_REQUIRED', 412: 'PRECONDITION_FAILED', 413: 'REQUEST_ENTITY_TOO_LARGE', 414: 'REQUEST_URI_TOO_LONG', 415: 'UNSUPPORTED_MEDIA_TYPE', 416: 'REQUESTED_RANGE_NOT_SATISFIABLE', 417: 'EXPECTATION_FAILED', 422: 'UNPROCESSABLE_ENTITY', 423: 'LOCKED', 424: 'FAILED_DEPENDENCY', 426: 'UPGRADE_REQUIRED', 443: 'HTTPS_PORT', 500: 'INTERNAL_SERVER_ERROR', 501: 'NOT_IMPLEMENTED', 502: 'BAD_GATEWAY', 503: 'SERVICE_UNAVAILABLE', 504: 'GATEWAY_TIMEOUT', 505: 'HTTP_VERSION_NOT_SUPPORTED', 507: 'INSUFFICIENT_STORAGE', 510: 'NOT_EXTENDED'}

        def __init__(self, response):
            body = response.read()
            try:
                errors = json.loads(body)
            except ValueError:
                errors = body

            status_name = self.status_map[response.status].replace('_', ' ')
            self.status = response.status
            self.error  = "%d %s: %s" % (response.status, status_name, errors)


def is_verbose(is_verbose):
    if (is_verbose is None and default_verbose is True) or is_verbose is True:
        return True
    else:
        return False

def is_file_type(data):
     ''' all you need is data.name and data.read() to act as a file '''
     if not getattr(data, 'name', False):
          return False
     if getattr(data, 'read', False) and getattr(data.read, '__call__', False):
          return True
     return False


class Springnote:
    ''' Springnote의 constant를 담고 request 등 기본적인 업무를 하는 클래스 '''
    HOST              = 'api.springnote.com'
    REQUEST_TOKEN_URL = 'https://%s/oauth/request_token'           % HOST
    ACCESS_TOKEN_URL  = 'https://%s/oauth/access_token/springnote' % HOST
    AUTHORIZATION_URL = 'https://%s/oauth/authorize'               % HOST
    signature_method  = oauth.OAuthSignatureMethod_HMAC_SHA1()
    consumer_token    = oauth.OAuthConsumer(DEFAULT_CONSUMER_TOKEN_KEY, DEFAULT_CONSUMER_TOKEN_SECRET)

    BOUNDARY          = 'AaB03x' 

    def __init__(self, access_token=None, consumer_token=(DEFAULT_CONSUMER_TOKEN_KEY, DEFAULT_CONSUMER_TOKEN_SECRET), verbose=None):
        """ Springnote 인스턴스를 초기화합니다.
        
         - consumer_token: 개발자가 따로 정의하고 싶은 consumer token을 (key, secret) tuple로 넣어줍니다. 넣지 않으면 라이브러리의 기본 token을 사용합니다.
         - access_token: 이전에 사용자가 승인하여 얻은 access token이 있으면 그것을 바로 넣어줄 수 있습니다. 만료가 되지 않았다면 바로 사용할 수 있습니다.
        """
        Springnote.consumer_token = oauth.OAuthConsumer(*consumer_token)
        self.auth = self.SpringnoteAuth(self)

        # set access token if already known
        self.access_token = None
        if access_token:
            self.set_access_token(access_token)

        self.verbose = verbose

    def oauth_request(self, method, url, params={}, sign_token=None, verbose=False):
        ''' springnote_request에서 사용할 OAuth request를 생성합니다. 
        
        여기서 생성된 oauth request는 문자열 형태로 header에 포함됩니다.  '''
        sign_token = self.format_token(sign_token or self.access_token)
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(
            Springnote.consumer_token, sign_token, method, url, params)
        oauth_request.sign_request(
            Springnote.signature_method, Springnote.consumer_token, sign_token)

        if is_verbose(verbose):
            print '>> oauth:'
            print ' * signature method :', Springnote.signature_method.get_name()
            print ' * consumer token :', (Springnote.consumer_token.key, Springnote.consumer_token.secret)
            print ' * sign token :', sign_token #(sign_token.key, sign_token.secret)

            print '>> oauth parameters:'
            for key in sorted(oauth_request.parameters.keys()):
                print " *", key, ':', oauth_request.parameters[key]

        return oauth_request


    def springnote_request(self, method, url, params={}, headers=None, body=None, sign_token=None, secure=False, verbose=False):
        """ Springnote에서 사용하는 request를 생성합니다. 

        oauth 인증을 위해 request token과 access token을 요청할 때와
        일반적인 springnote resource 요청할 때 사용합니다.

        >>> access_token = oauth.OAuthToken('key', 'secret')
        >>> http_response = Springnote(access_token).springnote_request( \
                "GET", "http://url.com/path")
        """
        oauth_request = self.oauth_request(method, url, params, \
            sign_token=(sign_token or self.access_token), verbose=verbose)

        # set headers
        #if 'content-type' not in map(lambda x: x.lower(), headers.keys()):
        #    headers['Content-Type'] = 'application/json'
        if headers is None:
            if method != "GET" and is_file_type(body):
                headers = {'Content-Type': "multipart/form-data; boundary=%s" % Springnote.BOUNDARY}
            elif '.json' in url: 
                headers = {'Content-Type': 'application/json'}
            else:
                headers = {}
        headers.update(oauth_request.to_header())

        # set body
        if is_file_type(body):
            body = Springnote.create_query_multipart_str(body)

        if is_verbose(verbose):
            print '>> header:'
            for key, value in headers.iteritems():
                print " *", key, ':', value

            if body:
                print '>> body:'
                print body

            print '>> request:'
            print oauth_request.http_method, oauth_request.http_url
            print 'header:', headers
            if body: print 'body:', body
            print

        # create http(s) connection and request
        if secure:
            if is_verbose(verbose): print 'using HTTPS'
            conn = httplib.HTTPSConnection(Springnote.HOST)
        else:
            conn = httplib.HTTPConnection(Springnote.HOST)

        # response
        try:
            if not default_dry_run:
                conn.request(oauth_request.http_method, oauth_request.http_url, body=body, headers=headers)
        except socket.gaierror:
            raise SpringnoteError.Network("%s에 접근할 수가 없습니다." % oauth_request.http_url)
        return conn.getresponse()


    @staticmethod
    def create_query_multipart_str(data, boundary=BOUNDARY):
        return "\r\n".join([
            '--%s' % boundary,
            'Content-Disposition: form-data; name="Filedata"; filename="%s"' % data.name,
            'Content-Transfer-Encoding: binary',
            'Content-Type: application/octet-stream',
            '',
            data.read(),
            '--%s--' % boundary,
        ])


    class SpringnoteAuth:
        ''' takes care of authorizing step in springnote. eventually retrieves an access token, 
        with which Springnote request data.

        The step is used as the following:
         1. fetches request token from springnote.com
            >> sn = Springnote()
            >> request_token = sn.auth.fetch_request_token() 
            # request token is saved internally
         2. guide user to authorize at springnote url
            >> url = sn.auth.authorize_url()
            >> print 'go to this url and approve', url
            >> raw_input('Press enter when complete.')
         3. exchange signed request token with access token
            >> sn.auth.fetch_access_token(request_token) 
            # access token is saved internally
        '''

        def __init__(self, springnote):
            self.sn = springnote

        def fetch_request_token(self, verbose=None):
            """ consumer의 자격으로 springnote.com으로부터 request token을 받아옵니다.
            
            >> request_token = Springnote.fetch_request_token()
            """
            response = self.sn.springnote_request(
                'POST', url=Springnote.REQUEST_TOKEN_URL, 
                secure=True, verbose=verbose)

            if not default_dry_run:
                if response.status != httplib.OK:
                    raise SpringnoteError.Response(response)
                self.request_token = oauth.OAuthToken.from_string(response.read())
            else:
                self.request_token = oauth.OAuthToken('FAKE_REQUEST_TOKEN_KEY', 'FAKE_REQUEST_TOKEN_SECRET')

            if is_verbose(verbose):
                print "<< request token:", (self.request_token.key, self.request_token.secret)

            return self.request_token
    
        def authorize_url(self, verbose=None, callback=None):
            """ request token을 받고 난 뒤, user에게 승인받을 url을 알려줍니다. """
            if not hasattr(self, 'request_token'):
                self.fetch_request_token(verbose=verbose)
    
            params = { "oauth_token": self.request_token.key }
            if callback:
                params["oauth_callback"] = callback
    
            url = "%s?%s" % (Springnote.AUTHORIZATION_URL, urllib.urlencode(params))
            return url
    
    
        def fetch_access_token(self, request_token=None, verbose=None):
            """ consumer의 자격으로 springnote.com에 request token을 주고 access token을 받아옵니다.
            access token은 request token이 있어야 하며, fetch_request_token()이 사전에 불렸어야 합니다.
            """
            self.request_token = request_token or self.request_token
            if 'request_token' not in vars(self):
                sys.stderr.write('you must call fetch_request_token first and approve\n')
                #self.request_token = self.fetch_request_token()
                return
    
            # request to springnote.com
            response = self.sn.springnote_request(
                'POST', Springnote.ACCESS_TOKEN_URL, 
                sign_token=self.request_token, secure=True, verbose=verbose)
    
            if response.status != httplib.OK:
                raise SpringnoteError.Response(response)
    
            access_token = oauth.OAuthToken.from_string(response.read())
            self.sn.set_access_token(access_token)
            return access_token
    
        def set_access_token(self, token, key):
            return sn.set_access_token(token, key)

        def is_authorized(self):
            """ returns True if has access token

            >> sn = Springnote()
            >> sn.auth.is_authorized()
            False
            """
            return sn.access_token != None

    @staticmethod
    def format_token(*args):
        """ 사용자가 OAuth.token이든 tuple이든 보내면 포맷을 잡아줍니다 """
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

        if args != (None):
            print "I don't know what you want me to do with", args
        return


    def set_access_token(self, *args):
        """ 직접 access token을 지정합니다. """
        self.access_token = self.format_token(*args)
        return self.access_token

    # --- Page sugar ---
    def get_page(self, id, note=None, params={}, verbose=None):
        """ /pages/:page_id.json에 접근하여 page를 가져옵니다. """
        return Page(self.access_token).get(id, note, params, verbose=verbose)

    def get_pages(self, note=None, params={}, verbose=None):
        """ 전체 page의 리스트를 가져옵니다.  """
        return Page(self.access_token).list(note, params, verbose=verbose)

    def create_page(self, title=None, source=None, tags=None, relation_is_part_of=None, note=None, params={}, verbose=None):
        """ /pages.json에 접근하여 새 page를 생성합니다. """
        return Page(self.access_token, note=note,
            title=title, source=source, tags=tags, 
            relation_is_part_of=relation_is_part_of,
        ).create(params, verbose=verbose)


    def update_page(self, id, title=None, source=None, tags=None,  relation_is_part_of=None, note=None, params={}, verbose=None):
        """ /pages/:page_id.json에 접근하여 기존 페이지를 수정합니다. """
        if note:  params['domain'] = note
        path = "/pages/%d.json" % id
        date = {}
        if title:  data['title' ] = title
        if source: data['source'] = source

        new_page = Page(self.access_token)
        new_page = new_page.request(path, "PUT", params, data, verbose=verbose)
        return new_page

    # --- Comments sugar ---
    def get_comments(self, id, note=None, params={}, verbose=None):
        raise NotImplementedError('you should implement it!')




class SpringnoteResource:
    """ springnote에서 사용하는 리소스의 부모 클래스. 
        Page, Attachment 등이 이 클래스를 상속합니다 """
    attributes = [] # 각 리소스가 사용하는 attribute

    def __init__(self, access_token, parent=None):
        self.access_token = access_token # 모든 request 시에 필요한 access token
        self.parent       = parent
        self.resource     = None         # 스프링노트의 리소스를 담는 dictionary 
        self.raw          = ''           # request의 결과로 가져온 raw data
        return

    def request(self, path, method="GET", params={}, data=None, verbose=None):
        """ springnote에 request를 보내고, 받은 결과를 토대로 리소스를 생성합니다.
            SpringnoteResource를 상속 받는 모든 하위클래스에서 사용합니다. """

        url     = "http://%s/%s" % (Springnote.HOST, path.lstrip('/'))
        headers = {'Content-Type': 'application/json'}
        if data: # set body if given (ex. {'page': ...})
            data = {self.__class__.__name__.lower(): data}
            data = json.dumps(data, ensure_ascii=False)
            if type(data) == str: 
                data = data.decode('utf-8')
            data = data.encode('utf-8')
        use_https = False

        if is_verbose(verbose):
            print '>> content'
            if use_https:
                print ' * uses HTTPS connection'
            print ' * HTTP method:', method
            print ' * params:',      params
            print ' * path:',        path
            print ' * url:',         url
            print ' * data:',        data
            print ' * headers:',     headers

        # send request
        response = Springnote(self.access_token).springnote_request(
                    method=method, url=url, params=params, 
                    headers=headers, body=data,
                    sign_token = self.access_token, 
                    secure     = use_https, 
                    verbose    = verbose
        )
        if not default_dry_run:
            if response.status != httplib.OK:
                raise SpringnoteError.Response(response)
            return self._build_model_from_response(response.read(), verbose=verbose)


    def _build_model_from_response(self, data, verbose=None): 
        """ springnote의 response에 따라 모델을 만듭니다. 

          * self.raw: response 본문이 저장됩니다.
          * self.resource: response의 내용이 dictionary 형태로 저장됩니다.
        """
        self.raw = data
        if is_verbose(verbose):
            print '<< data:'
            print data
            print
        # build proper object
        object_name = self.__class__.__name__.lower() # Page => 'page'
        structure = json.loads(data)
        # build multiple data
        if type(structure) is list:
            multiple_resources = []
            for resource_dict in structure:
                new_instance = self.__class__(self.access_token, parent=self.parent)
                new_instance.resource = resource_dict[object_name]
                new_instance.process_resource(new_instance.resource)
                multiple_resources.append( new_instance )
            return multiple_resources
        # build single data        
        elif object_name in data:
            self.resource = json.loads(data)[object_name]
            # process resource specific tasks
            self.process_resource(self.resource)
            return self
        else:
            raise ParseError('unable to parse as predefined model: ' + data)

    @staticmethod
    def _to_unicode(s):
        return eval('u"""%s"""' % s)

    def process_resource(self, resource_dict):
        """ resource마다 따로 필요한 후처리 작업을 해줍니다. 

        각 resource마다 이 메소드를 재정의해서 필요한 후처리를 할 수 있습니다. 
        기본적으로 .id attribute를 추가합니다.
        """
        # set direct accessor (ex: page.identifier == 2)
        [setattr(self, key, value) for key, value in resource_dict.iteritems()]
        # unicode
        for key, value in resource_dict.iteritems():
            if isinstance(value, types.StringTypes):
                setattr(self, key, self._to_unicode(value))
        # alias id
        if "identifier" in resource_dict:
            setattr(self, "id", resource_dict["identifier"])
        self.resource = resource_dict
        return resource_dict


class Page(SpringnoteResource):
    """ 스프링노트의 page에 대한 정보를 가져오거나, 수정할 수 있습니다.
        page의 하위 리소스에 접근할 수 있도록 해줍니다. """

    attributes = [
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

    def __init__(self, access_token, note=None, id=None, 
            title=None, source=None, relation_is_part_of=None, tags=None, parent=None):
        """ can give writable_attribute arguments, so you can save easily later """
        SpringnoteResource.__init__(self, access_token)
        self.note   = note
        self.id     = id
        self.title  = title
        self.source = source
        self.relation_is_part_of = relation_is_part_of
        self.tags   = tags

    def process_resource(self, resource_dict):
        """ +tags를 배열로 변환한다. """
        SpringnoteResource.process_resource(self, resource_dict)
        if "tags" in resource_dict:
            self.tags = filter(None, self.tags.split(','))
        return resource_dict

    def __writable_resources(self):
        if self.resource is None:
            self.update_resource()

        writable_resource = {}
        for key, value in self.resource.iteritems():
            if key in self.writable_attributes:
                writable_resource[key] = getattr(self, key)
        # convert list of tags into string
        if 'tags' in self.resource:
            writable_resource['tags'] = ' '.join(getattr(self, 'tags'))
        return writable_resource

    #--

    def get(self, verbose=None):
        if self.id is None:
            raise SpringnoteError.InvalidOption("need page id to perform get()")
        path, params = self._set_path_params()
        return self.request(path, "GET", params=params, verbose=verbose)


    def save(self, verbose=None):
        if self.id: method = "PUT"  # update existing page
        else:       method = "POST" # create new page
        path, params = self._set_path_params()

        data = {}
        for attr in self.writable_attributes:
            value = getattr(self, attr, False)
            if value:
                data[attr] = value
    
        self.request(path, method, params=params, data=data, verbose=verbose)
        return self

    def delete(self, verbose=None):
        if self.id is None:
            raise SpringnoteError.InvalidOption("need page id to perform delete()")
        path, params = self._set_path_params()
        return self.request(path, "DELETE", params=params, verbose=verbose)

    @staticmethod
    def _update_params(kwarg):
        ''' update parameters, from dictionary '''
        import re
        _parameters_check = {
            'sort'  : ['identifier', 'title', 'relation_is_par_of', 'date_modified', 'date_created'],
            'order' : ['desc', 'asc'],
            'offset': types.IntType,
            'count' : types.IntType,
            'q'     : types.StringTypes,
            'tags'  : types.StringTypes,
            'identifiers': re.compile("([0-9]+,)*[0-9]+"), 
        }
        params = {}
        for key, value in kwarg.iteritems():
            if key not in _parameters_check:
                continue
            check_method = _parameters_check[key]
            # string in list
            if isinstance(check_method, types.ListType):
                if value in check_method: params[key] = value
                else:
                    msg = "%s is not allowed for %s" % (value, key)
                    raise SpringnoteError.InvalidOption(msg)
            # is string types
            elif check_method is types.StringTypes:
                params[key] = unicode(value)
            # is some type
            elif isinstance(check_method, types.TypeType):
                try:
                    params[key] = check_method(value)
                except ValueError:
                    msg = "%s is not allowed for %s" % (value, key)
                    raise SpringnoteError.InvalidOption(msg)
            # is regex pattern
            elif isinstance(check_method, re._pattern_type):
                if check_method.match(value): params[key] = value
                else:
                    msg = "%s is not allowed for %s" % (value, key)
                    raise SpringnoteError.InvalidOption(msg)
        return params


    @staticmethod
    def _set_path_params_static(**kwarg):
        ''' format path and params, according to page id and note '''
        if 'note' in kwarg: note = kwarg['note']
        else:               note = None
        if 'id'   in kwarg: id   = kwarg['id']
        else:               id   = None

        # update params
        if id is None:  params = Page._update_params(kwarg)
        else:           params = {}
        if note:
            params['domain'] = note

        # update path
        if id:      path  = "/pages/%d.json" % id
        else:       path  = "/pages.json"
        if params:  path += "?%s" % urllib.urlencode(params)

        return (path, params)

    def _set_path_params(self, **kwarg):
        ''' format path and params, according to page id and note '''
        if 'note' not in kwarg: kwarg['note'] = self.note
        if 'id'   not in kwarg: kwarg['id']   = self.id

        return Page._set_path_params_static(**kwarg)

    @classmethod
    def list(cls, access_token, verbose=None, **kwarg):
        kwarg.update(id=None)
        path, params = Page._set_path_params_static(**kwarg) # ignores id
        # XXX: this won't work for processing response!
        return cls(access_token).request(path, "GET", params, verbose=verbose)
        
    @classmethod
    def search(cls, access_token, query, verbose=None, **kwarg):
        kwarg.update(id=None, q=query)
        return cls.list(access_token, verbose=verbose, **kwarg)


