#/usr/bin/python
# -*- coding: utf-8 -*-

"""

    Springnote API library using OAuth

"""
__author__  = "Jang-hwan Kim"
__email__   = "janghwan at gmail dot com"
__version__ = 0.6

import env 

import oauth, sys, types, re
import httplib, urllib, socket, os.path

# json import order: simplejson -> json -> FAIL
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
    ''' needs data.name and data.read() to act as a file '''
    if not getattr(data, 'name', False):
        return False
    if getattr(data, 'read', False) and getattr(data.read, '__call__', False):
        return True
    return False


class Springnote(object):
    ''' Springnote의 constant를 담고 request 등 기본적인 업무를 하는 클래스 '''
    signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()
    BOUNDARY         = 'AaB03x' 

    def __init__(self, access_token=None, consumer_token=(DEFAULT_CONSUMER_TOKEN_KEY, DEFAULT_CONSUMER_TOKEN_SECRET), verbose=None):
        """ consumer token을 초기화하고, 경우에 따라 access token도 있으면 
        초기화해서 바로 사용할 수 있습니다.
        
         - consumer_token: 개발자가 정의하고 싶은 consumer token을 
             (key, secret) tuple로 넣어줍니다. 
             넣지 않으면 라이브러리의 기본 token을 사용합니다.
         - access_token: 사용자가 전에 승인하여 얻은 access token이
             있으면 그것을 바로 넣어줄 수 있습니다. 
             만료가 되지 않았다면 바로 사용할 수 있습니다.
             없으면 사용자 동의 하에 새로 받을 수 있습니다.
        """
        self.consumer_token = self.format_token(consumer_token)
        self.set_access_token(access_token)

        self.verbose = verbose

    def oauth_request(self, method, url, params={}, sign_token=None, verbose=False):
        ''' springnote_request에서 사용할 OAuth request를 생성합니다. 
        
        여기서 생성된 oauth request는 문자열 형태로 header에 포함됩니다.  '''
        sign_token = self.format_token(sign_token or self.access_token)
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(
            self.consumer_token, sign_token, method, url, params)
        oauth_request.sign_request(
            Springnote.signature_method, self.consumer_token, sign_token)

        if is_verbose(verbose):
            print '>> oauth:'
            print ' * signature method :', Springnote.signature_method.get_name()
            print ' * consumer token :', (self.consumer_token.key, self.consumer_token.secret)
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
        if headers is None:
            headers = {}
        if method != "GET" and is_file_type(body):
            headers['Content-Type'] = 'multipart/form-data; boundary=%s' % Springnote.BOUNDARY
        elif '.json' in url: 
            headers['Content-Type'] = 'application/json'
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
            conn = httplib.HTTPSConnection(HOST)
        else:
            conn = httplib.HTTPConnection(HOST)

        # response
        try:
            if not default_dry_run:
                conn.request(oauth_request.http_method, oauth_request.http_url, body=body, headers=headers)
        except socket.gaierror:
            raise SpringnoteError.Network("%s에 접근할 수가 없습니다." % oauth_request.http_url)
        return conn.getresponse()


    @staticmethod
    def create_query_multipart_str(file, boundary=BOUNDARY):
        return "\r\n".join([
            '--%s' % boundary,
            'Content-Disposition: form-data; name="Filedata"; filename="%s"' % file.name,
            'Content-Transfer-Encoding: binary',
            'Content-Type: application/octet-stream',
            '',
            file.read(),
            '--%s--' % boundary,
        ])

    def set_access_token(self, *args):
        """ 직접 access token을 지정합니다. 
        
        >> sn = Springnote()
        >> sn.set_access_token(('SOME_ACCESS', 'TOKEN'))
        <oauth.OAuthToken object ...>
        >> sn.set_access_token('SOME_ACCESS', 'TOKEN')
        <oauth.OAuthToken object ...>
        """
        self.access_token = self.format_token(*args)
        return self.access_token

    def fetch_request_token(self, verbose=None):
        """ consumer의 자격으로 springnote.com으로부터 request token을 받아옵니다.
        
        >> request_token = Springnote.fetch_request_token()
        """
        response = self.springnote_request(
            'POST', url=REQUEST_TOKEN_URL, 
            secure=True, sign_token=None, verbose=verbose)

        # parse request token
        if not default_dry_run:
            if response.status != httplib.OK:
                raise SpringnoteError.Response(response)
            request_token = oauth.OAuthToken.from_string(response.read())
        else:
            request_token = oauth.OAuthToken('FAKE_REQUEST_TOKEN_KEY', 'FAKE_REQUEST_TOKEN_SECRET')

        if is_verbose(verbose):
            print "<< request token:", (request_token.key, request_token.secret)

        return request_token
    
    def authorize_url(self, request_token, verbose=None, callback=None):
        """ request token을 받고 난 뒤, user에게 승인받을 url을 알려줍니다. """
        params = { "oauth_token": request_token.key }
        if callback:
            params["oauth_callback"] = callback
    
        url = "%s?%s" % (AUTHORIZATION_URL, urllib.urlencode(params))
        return url
    
    def fetch_access_token(self, request_token, verbose=None):
        """ consumer의 자격으로 springnote.com에 request token을 주고 access token을 받아옵니다.
        access token은 request token이 있어야 하며, fetch_request_token()이 사전에 불렸어야 합니다.
        """
        # request to springnote.com
        response = self.springnote_request(
            'POST', ACCESS_TOKEN_URL, 
            sign_token=request_token, secure=True, verbose=verbose)
    
        if response.status != httplib.OK:
            raise SpringnoteError.Response(response)
    
        access_token = oauth.OAuthToken.from_string(response.read())
        self.set_access_token(access_token)
        return self.access_token

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
        return


    # --- Page sugar ---
    def get_page(self, note=None, id=None, title=None, 
            source=None, relation_is_part_of=None, tags=None, verbose=None):
        """ /pages/:page_id.json에 접근하여 page를 가져옵니다. """
        return Page(self.access_token, note, id, title, source, 
            relation_is_part_of, tags).get(verbose)

    def get_pages(self, note=None, verbose=None, **kwarg):
        """ 전체 page의 리스트를 가져옵니다.  """
        return Page(self.access_token).list(note, verbose=verbose, **kwarg)

    # --- Comments sugar ---
    def get_comments(self, id, note=None, params={}, verbose=None):
        raise NotImplementedError('you should implement it!')

## -- OOP layer
class SpringnoteResource(object):
    """ springnote에서 사용하는 리소스의 부모 클래스. 
        Page, Attachment 등이 이 클래스를 상속합니다 """
    springnote_attributes = [] # 각 리소스가 사용하는 attribute

    def __init__(self, auth, parent=None):
        self.auth     = auth    # .access_token과 .consumer_token을 갖고 있는 객체. Springnote 이면 충분하다.
        self.parent   = parent
        self.resource = {}      # 스프링노트의 리소스를 담는 dictionary 
        self.raw      = ''      # request의 결과로 가져온 raw data
        for attr in self.springnote_attributes:
            setattr(self, attr, None)
        return

    def request(self, path, method="GET", params={}, data=None, 
                post_process=True, verbose=None):
        """ springnote에 request를 보내고, 받은 결과를 토대로 리소스를 생성합니다.
            SpringnoteResource를 상속 받는 모든 하위클래스에서 사용합니다. """

        url     = "http://%s/%s" % (HOST, path.lstrip('/'))
        #headers = {'Content-Type': 'application/json'}
        headers = {}
        if data: # set body if given (ex. {'page': ...})
            if not is_file_type(data):
                data = {self.__class__.__name__.lower(): data}
                data = json.dumps(data, ensure_ascii=False)
                sys.stdout.flush()
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
        response = Springnote(self.auth.access_token, self.auth.consumer_token) \
            .springnote_request(method=method, url=url, params=params, 
                    headers = headers,   
                    body    = data,
                    secure  = use_https, 
                    verbose = verbose
        )
        if not default_dry_run:
            if response.status != httplib.OK:
                raise SpringnoteError.Response(response)
            self.raw = response.read()
            if post_process:
                return self._build_model_from_response(self.raw, verbose=verbose)
            else:   
                return self


    def _build_model_from_response(self, data, verbose=None): 
        """ springnote의 response에 따라 모델을 만듭니다. 

          * self.raw: response 본문이 저장됩니다.
          * self.resource: response의 내용이 dictionary 형태로 저장됩니다.
        """
        cls = self.__class__
        self.raw = data
        if is_verbose(verbose):
            print '<< data:'
            print data
            print
        # build proper object
        object_name = cls.__name__.lower() # Page => 'page'
        structure = json.loads(data)
        # build multiple data
        if type(structure) is list:
            multiple_resources = []
            for resource_dict in structure:
                new_instance = cls(auth=self.auth, parent=self.parent)
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
            raise SpringnoteError.ParseError('unable to parse as predefined model: ' + data)

    @staticmethod
    def _to_unicode(s):
        #return eval('u"""%s"""' % s)
        def repl(match): return unichr(int(match.group(1), 16))
        return re.sub(r"\\u([0-9a-fA-F]{4})", repl, s)

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

    def requires_value_for(self, *attribute_names):
        ''' check value for given attribute names, raise InvalidOption if none.
        recursive attribute names like 'parent.id' work '''
        # format error message
        error_msg = map(lambda x: "'%s'" % x, attribute_names)
        error_msg = " and ".join(error_msg)
        if len(attribute_names) == 2:
            error_msg = "both " + error_msg
        elif len(attribute_names) > 2: 
            error_msg = "all " + error_msg
        error_msg = "needs %s to perform the request" % error_msg
        # check recursive names
        for name in attribute_names:
            value = self
            for subname in name.split('.'):
                if not hasattr(value, subname):
                    error_msg = "missing %s. %s" % (name, error_msg)
                    raise SpringnoteError.InvalidOption(error_msg)
                value = getattr(value, subname)
        else:
            return True

    @classmethod
    def _set_path_params(cls, page, id=None, format=True, plural=True):
        path = "/pages/%d/%s" % (page.id, cls.__name__.lower())
        if plural:  path += 's'
        if id:      path += "/%d"  % id
        if format:  path += ".json"

        params = {}
        if page.note:
            params = {'domain': page.note}
            path  += "?domain=%s" % page.note

        return path, params


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
    # name of attributes used when save()
    writable_attributes = ["title", "source", "relation_is_part_of", "tags"]
    check_parameters = { # arguments to check parameters
        'sort'     : ['identifier', 'title', 'relation_is_par_of', 'date_modified', 'date_created'],
        'order'    : ['desc', 'asc'],
        'offset'   : types.IntType,
        'count'    : types.IntType,
        'parent_id': types.IntType,
        'q'        : types.StringTypes,
        'tags'     : types.StringTypes,
        'identifiers': re.compile("([0-9]+,)*[0-9]+"),
    }

    def __init__(self, auth, id=None, note=None, 
            title=None, source=None, relation_is_part_of=None, tags=None,
            parent=None):
        SpringnoteResource.__init__(self, auth)
        # 
        self.note     = note
        self.resource = {}
        # springnote attributes
        self.id     = id
        self.title  = title
        self.source = source
        self.tags   = tags
        self.relation_is_part_of = relation_is_part_of

    def process_resource(self, resource_dict):
        """ + tags를 배열로 변환한다. """
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

    @staticmethod
    def _set_path_params_static(**kwarg):
        ''' format path and params, according to page id and note '''
        # update note and id
        if 'note' in kwarg: note = kwarg['note']
        else:               note = None
        if 'id'   in kwarg: id   = kwarg['id']
        else:               id   = None

        # update path and parameters
        if id:
            path  = "/pages/%d.json" % id
            params = {}
        else:
            path  = "/pages.json"
            params = Page._update_params(kwarg)
        if note: 
            params['domain'] = note

        # apply params to path
        if params:  
            path += "?%s" % urllib.urlencode(params)

        return (path, params)

    def _set_path_params(self, **kwarg):
        if 'note' not in kwarg: kwarg['note'] = self.note
        if 'id'   not in kwarg: kwarg['id']   = self.id
        return Page._set_path_params_static(**kwarg)

    @classmethod
    def _update_params(cls, kwarg):
        ''' update parameters from given dictionary 
        only used in page listing. '''
        params = {}
        for key, value in kwarg.iteritems():
            if key not in cls.check_parameters:
                continue

            check_method = cls.check_parameters[key]
            error_msg = "%s is not allowed for %s" % (value, key)
            # list of strings
            if isinstance(check_method, types.ListType):
                if value in check_method: params[key] = value
                else:   raise SpringnoteError.InvalidOption(error_msg)
            # string (or unicode)
            elif check_method is types.StringTypes:
                params[key] = unicode(value)
            # primitive type
            elif isinstance(check_method, types.TypeType):
                try:
                    params[key] = check_method(value)
                except ValueError:
                    raise SpringnoteError.InvalidOption(error_msg)
            # regex
            elif isinstance(check_method, re._pattern_type):
                if check_method.match(value): params[key] = value
                else:
                    raise SpringnoteError.InvalidOption(error_msg)
        return params

    # -- 
    def get(self, verbose=None):
        """ fetch the page with current id. 
        hence the page instance MUST have id attribute """
        self.requires_value_for('id')
        path, params = self._set_path_params()
        return self.request(path, "GET", params=params, verbose=verbose)


    def save(self, verbose=None):
        """ save the current page.
        create a new page if there is no id, while update if given.
        ungiven parameters are ignored, not removed """
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
        """ delete the page """
        self.requires_value_for('id')
        path, params = self._set_path_params()
        return self.request(path, "DELETE", params=params, verbose=verbose)


    @classmethod
    def list(cls, auth, note=None, verbose=None, **kwarg):
        ''' get list of pages, that matches the criterion 
        
        NOTE: not all attributes are loaded, only the following are:
            [title, relation_is_part_of, uri, identifier, date_modified]
        '''
        kwarg.update(id=None)
        if note: 
            kwarg.update(note=note)

        path, params = Page._set_path_params_static(**kwarg) # ignores id
        return cls(auth=auth).request(path, "GET", params, verbose=verbose)
        
    @classmethod
    def search(cls, auth, query, note=None, verbose=None, **kwarg):
        kwarg.update(q=query)
        return cls.list(auth, note=note, verbose=verbose, **kwarg)

    @classmethod
    def get_root(cls, auth, note=None, verbose=None):
        ''' get root page. uses list() method
        
        NOTE: not all attributes are loaded, only the following are:
            [title, relation_is_part_of, uri, identifier, date_modified]
        '''
        pages = cls.list(auth, note=note, verbose=verbose)
        root_page = filter(lambda p: p.relation_is_part_of is None, pages)[0]
        return root_page

class Attachment(SpringnoteResource):
    springnote_attributes = [ 
        "identifier",          # 첨부 고유 ID 예) 2
        "title",               # 첨부 파일 이름 예) test.jpg
        "description",         # 첨부 파일 크기(단위는 바이트) 예) 8000
        "date_created",        # 첨부 최초 생성 일시(UTC) 예) 2008-01-30T10:11:16Z
        "relation_is_part_of", # 첨부 파일이 속한 페이지의 ID 예) 1
    ]
    def __init__(self, parent, id=None, filename=None, file=None, auth=None):
        SpringnoteResource.__init__(self, auth or parent.auth, parent=parent)
        self.id, self.relation_is_part_of = id, parent.id

        # file attributes
        self.title = filename
        self.content, self.description, self.date_created = None, None, None
        if file:     self.set_file(file)
        if filename: self.title = filename

    def set_file(self, file):
        ''' set title, content, description '''
        self.title, self.content = file.name, file.read()
        self.description         = len(self.content)
    def get_file(self):
        ''' return a fake file object with name and read() it '''
        class File: 
            def __init__(self, name, content):
                self.name = name
                self.read = lambda: content
            def __eq__(self, object):
                try:
                    return self.name == object.name and \
                        self.read() == object.read()
                except:
                    return False
        if self.title and self.content:
            return File(self.title, self.content)
        return None
    file = property(get_file, set_file)

    @classmethod
    def _set_path_params(cls, page, id=None, format=True):
        path = "/pages/%d/attachments" % page.id
        if id:      path += "/%d"  % id
        if format:  path += ".json"

        params = {}
        if page.note:
            params = {'domain': page.note}
            path += "?domain=%s" % page.note

        return path, params
            
    @classmethod
    def list(cls, page, auth=None, verbose=None):
        path, params = Attachment._set_path_params(page)
        return cls(auth=auth, parent=page) \
                .request(path, "GET", params, verbose=verbose)

    def get(self, verbose=None):
        """ reload the metadata of attachment, but not the file itself. 
        requires id and parent.id """
        self.requires_value_for('id', 'parent.id')
        path, params = self._set_path_params(self.parent, self.id, format=True)
        self.request(path, "GET", params, verbose=verbose)

    def download(self, filename=None, filepath=None, overwrite=False, verbose=None):
        """ fetch the attachment file. requires id and parent.id 
        
        tries to save the download to file if filename (and filepath) is given.
        it tries to use the default if filename is set to True, 
        but note that download() does not cannot retreive the filename.

        if there already is a file in the specified path and name, 
        it will not save it unless you've set the overwrite to True.

        to sum up, saving as a file fails if:
            * default (filename is None)
            * filename is True, but self.title is not set
            * filename is some string, but there already exist a file (overwrite=False)
        """
        self.requires_value_for('id', 'parent.id')
        path, params = self._set_path_params(self.parent, self.id, format=False)
        self.request(path, "GET", params, post_process=False, verbose=verbose)
        # own post process - tries to save file
        self.content = self.raw
        if filename is True:  filename = self.title
        if filepath:          filename = os.path.join(filepath, filename)
        if filename:
            if overwrite or not os.path.exists(filename):
                open(filename, 'w')

        return self

    def delete(self, verbose=None):
        """ delete the attachment. requires id and parent.id """
        self.requires_value_for('id', 'parent.id')
        path, params = Attachment._set_path_params(self.parent, self.id)
        return self.request(path, "DELETE", params=params, verbose=verbose)

    def upload(self, verbose=None):
        """ upload a file as attachment. requires file and parent.id

        if id is given, it updates an existing file
        and if not, creates a new file """
        self.requires_value_for('parent.id', 'file')
        if self.id:  method = "PUT"   # update existing attachment
        else:        method = "POST"  # create new attachment

        path, params = Attachment._set_path_params(self.parent, id=self.id)
        return self.request(path, method, params=params, data=self.file, 
                            verbose=verbose)


class Comment(SpringnoteResource):
    springnote_attributes = [ 
        "identifier",          # 고유 ID 예) 1
        "date_created",        # 최초 생성 일시(UTC)예) 2008-01-30T10:11:16Z
        "relation_is_part_of", # 첨부 파일이 속한 페이지의 ID 예) 1
        "creator",             # 작성자 nickname
        "source",              # 내용
    ]

    @classmethod
    def list(cls, page, auth=None, verbose=None):
        path, params = cls._set_path_params(page)
        return cls(auth=auth or page.auth, parent=page) \
                .request(path, "GET", params, verbose=verbose)


class Collaboration(SpringnoteResource):
    springnote_attributes = [ 
        "rights_holder", # 협업자의 OpenID
        "access_rights", # 협업자가 가진 권한 예) reader, writer, guest, creator
        "date_created",  # 협업을 시작한 시간(UTC) 예) 2008-01-30T10:11:16Z
    ]
    @classmethod
    def list(cls, page, auth=None, verbose=None):
        path, params = cls._set_path_params(page, plural=False)
        return cls(auth=auth or page.auth, parent=page) \
            .request(path, "GET", params, verbose=verbose)


class Lock(SpringnoteResource):
    springnote_attributes = [ 
        "creator",             # 현재 페이지를 수정중인 사용자 OpenID
        "date_expired",        # 잠금이 해제되는 (예상) 시간(UTC) 예) 2008-01-30T10:11:16Z
        "relation_is_part_of", # 잠금 리소스가 속한 페이지의 ID
    ]
    def __init__(self, parent, auth=None):
        SpringnoteResource.__init__(self, auth or parent.auth, parent=parent)
        self.relation_is_part_of = parent.id

    def get(self, verbose=None):
        """ fetch status of lock """
        self.requires_value_for('parent.id')
        path, params = self._set_path_params(self.parent, plural=False)
        # XXX: json format of Lock does is not wrapped by 'lock'. springnote bug??
        self.request(path, "GET", params, post_process=False, verbose=verbose)
        # own post process
        self.raw = '{"lock": %s}' % self.raw
        return self._build_model_from_response(self.raw, verbose=verbose)

    def acquire(self, verbose=None):
        """ try to acquire a lock (POST)"""
        self.requires_value_for('parent.id')
        path, params = self._set_path_params(self.parent, plural=False)
        # XXX: json format of Lock does is not wrapped by 'lock'. springnote bug??
        self.request(path, "POST", params, post_process=False, verbose=verbose)
        # own post process
        self.raw = '{"lock": %s}' % self.raw
        return self._build_model_from_response(self.raw, verbose=verbose)


class Revision(SpringnoteResource):
    # there is no 'date_modified', 'contributor_modified', 'rights', and 'tags'
    springnote_attributes = [ 
        "identifier",          # 히스토리 고유 ID
        "creator",             # 만든 사람 OpenID
        "date_created",        # 생성된 시간(UTC) 예) 2008-01-30T10:11:16Z
        "relation_is_part_of", # 히스토리가 속한 페이지의 ID
        "source",              # 페이지 내용 -- only at get()
        "description",         # 히스토리에 대한 설명 -- only at list()
    ]
    def __init__(self, parent, auth=None, id=None):
        SpringnoteResource.__init__(self, auth or parent.auth, parent=parent)
        self.id = id
        self.relation_is_part_of = parent.id

    @classmethod
    def list(cls, page, auth=None, verbose=None):
        ''' get list of page revisions
        NOTE: not all attributes are loaded, only the following are:
            [ date_created, identifier, description, creator ]
        ''' 
        path, params = cls._set_path_params(page)
        return cls(auth=auth or page.auth, parent=page) \
                .request(path, "GET", params, verbose=verbose)

    def get(self, verbose=None):
        self.requires_value_for('parent.id', 'id')
        path, params = self._set_path_params(self.parent, id=self.id)
        return self.request(path, "GET", params, verbose=verbose)

