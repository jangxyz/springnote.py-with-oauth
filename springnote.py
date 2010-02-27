#/usr/bin/python
# -*- coding: utf-8 -*-

"""

    Springnote API library using OAuth

"""
VERSION = 0.1

import env 

import oauth, sys
import simplejson as json
import httplib, urllib
import socket

# default consumer token (as springnote python library)
# FIXME: change this to make your own consumer!
CONSUMER_TOKEN_KEY    = '162DSyqm28o355V7zEKw'
CONSUMER_TOKEN_SECRET = 'MtiDOAWsFkH2yOLzOYkubwFK6THOA5iAJIR4MJnwKMQ'

default_verbose = False
default_dry_run = False

def is_verbose(is_verbose):
    if (is_verbose is None and default_verbose is True) or is_verbose is True: return True
    else: return False

class Springnote:
    ''' Springnote의 constant를 담고 request 등 기본적인 업무를 하는 클래스 '''
    HOST              = 'api.springnote.com'
    REQUEST_TOKEN_URL = 'https://%s/oauth/request_token'           % HOST
    ACCESS_TOKEN_URL  = 'https://%s/oauth/access_token/springnote' % HOST
    AUTHORIZATION_URL = 'https://%s/oauth/authorize'               % HOST
    signature_method  = oauth.OAuthSignatureMethod_HMAC_SHA1()
    consumer_token    = oauth.OAuthConsumer(CONSUMER_TOKEN_KEY, CONSUMER_TOKEN_SECRET)

    def __init__(self, consumer_token=(CONSUMER_TOKEN_KEY, CONSUMER_TOKEN_SECRET), access_token=None, verbose=None):
        """ Springnote 인스턴스를 초기화합니다.
        
         - consumer_token: 개발자가 따로 정의하고 싶은 consumer token을 (key, secret) tuple로 넣어줍니다. 넣지 않으면 라이브러리의 기본 token을 사용합니다.
         - access_token: 이전에 사용자가 승인하여 얻은 access token이 있으면 그것을 바로 넣어줄 수 있습니다. 만료가 되지 않았다면 바로 사용할 수 있습니다.
        """
        Springnote.consumer_token = oauth.OAuthConsumer(*(consumer_token))
        self.auth = self.SpringnoteAuth(self)

        # set access token if already known
        self.access_token = None
        if access_token:
            self.set_access_token(*access_token)

        self.verbose = verbose


    @staticmethod
    def springnote_request(method, url, params={}, headers={}, body=None, sign_token=None, secure=False, verbose=False):
        """ Springnote에서 사용하는 request를 생성합니다. 

        oauth 인증을 위해 request token과 access token을 요청할 때와
        일반적인 springnote resource 요청할 때 사용합니다.
        """
        # create oauth request
        oauth_request = oauth.OAuthRequest.from_consumer_and_token(
            Springnote.consumer_token, sign_token, method, url, params)
        oauth_request.sign_request(
            Springnote.signature_method, Springnote.consumer_token, sign_token)

        headers.update(oauth_request.to_header())
        if 'content-type' not in map(lambda x: x.lower(),headers.keys()):
            headers['Content-Type'] = 'application/json'

        if is_verbose(verbose):
            print '>> oauth:'
            print ' * signature method :', Springnote.signature_method.get_name()
            print ' * consumer token :', (Springnote.consumer_token.key, Springnote.consumer_token.secret)
            print ' * sign token :', sign_token #(sign_token.key, sign_token.secret)

            print '>> oauth parameters:'
            for key in sorted(oauth_request.parameters.keys()):
                print " *", key, ':', oauth_request.parameters[key]

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
            conn = httplib.HTTPSConnection(Springnote.HOST)
        else:
            conn = httplib.HTTPConnection(Springnote.HOST)
        try:
            if not default_dry_run:
                conn.request(oauth_request.http_method, oauth_request.http_url, body=body, headers=headers)
        except socket.gaierror:
            raise SpringnoteError.Network("%s에 접근할 수가 없습니다." % oauth_request.http_url)
        return conn.getresponse()


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
            response = Springnote.springnote_request(
                'POST', url=Springnote.REQUEST_TOKEN_URL, secure=True, 
                verbose=verbose)

            if default_dry_run:
                self.request_token = oauth.OAuthToken('FAKE_REQUEST_TOKEN_KEY', 'FAKE_REQUEST_TOKEN_SECRET')
            else:
                if response.status != httplib.OK:
                    raise SpringnoteError.Response(response)
                self.request_token = oauth.OAuthToken.from_string(response.read())

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
            response = Springnote.springnote_request(
                'POST', Springnote.ACCESS_TOKEN_URL, 
                sign_token=self.request_token, secure=True, verbose=verbose)
    
            if response.status != httplib.OK:
                raise SpringnoteError.Response(response)
    
            access_token = oauth.OAuthToken.from_string(response.read())
            self.sn.set_access_token(access_token.key, access_token.secret)
            return access_token
    
        def set_access_token(self, token, key):
            return sn.access_token(token, key)

        def is_authorized(self):
            """ returns True if has access token

            >> sn = Springnote()
            >> sn.auth.is_authorized()
            False
            """
            return sn.access_token != None

    def set_access_token(self, token, key):
        """ 직접 access token을 지정합니다. """
        self.access_token = oauth.OAuthToken(token, key)
        return self.access_token

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
    class Network(Base):      pass

    class Response(Base):
        # status codes and names, extracted from httplib
        status_map = {100: 'CONTINUE', 101: 'SWITCHING_PROTOCOLS', 
            102: 'PROCESSING', 200: 'OK', 201: 'CREATED', 202: 'ACCEPTED', 
            203: 'NON_AUTHORITATIVE_INFORMATION', 204: 'NO_CONTENT', 
            205: 'RESET_CONTENT', 206: 'PARTIAL_CONTENT', 207: 'MULTI_STATUS', 
            226: 'IM_USED', 300: 'MULTIPLE_CHOICES', 301: 'MOVED_PERMANENTLY', 
            302: 'FOUND', 303: 'SEE_OTHER', 304: 'NOT_MODIFIED', 
            305: 'USE_PROXY', 307: 'TEMPORARY_REDIRECT', 400: 'BAD_REQUEST', 
            401: 'UNAUTHORIZED', 402: 'PAYMENT_REQUIRED', 403: 'FORBIDDEN', 
            404: 'NOT_FOUND', 405: 'METHOD_NOT_ALLOWED', 
            406: 'NOT_ACCEPTABLE', 407: 'PROXY_AUTHENTICATION_REQUIRED', 
            408: 'REQUEST_TIMEOUT', 409: 'CONFLICT', 410: 'GONE', 
            411: 'LENGTH_REQUIRED', 412: 'PRECONDITION_FAILED', 
            413: 'REQUEST_ENTITY_TOO_LARGE', 414: 'REQUEST_URI_TOO_LONG', 
            415: 'UNSUPPORTED_MEDIA_TYPE', 
            416: 'REQUESTED_RANGE_NOT_SATISFIABLE', 417: 'EXPECTATION_FAILED', 
            422: 'UNPROCESSABLE_ENTITY', 423: 'LOCKED', 
            424: 'FAILED_DEPENDENCY', 426: 'UPGRADE_REQUIRED', 
            443: 'HTTPS_PORT', 500: 'INTERNAL_SERVER_ERROR', 
            501: 'NOT_IMPLEMENTED', 502: 'BAD_GATEWAY', 
            503: 'SERVICE_UNAVAILABLE', 504: 'GATEWAY_TIMEOUT', 
            505: 'HTTP_VERSION_NOT_SUPPORTED', 507: 'INSUFFICIENT_STORAGE', 
            510: 'NOT_EXTENDED'}

        def __init__(self, response):
            body = response.read()
            try:
                errors = json.loads(body)
            except ValueError:
                errors = body

            status_name = self.status_map[response.status].replace('_', ' ')
            self.status = response.status
            self.error  = "%d %s: %s" % (response.status, status_name, errors)

def main():
    # parse options
    argv = sys.argv[1:]
    verbose = False
    access_token = None
    for argument in argv[:]:
        if argument == '--dry':
            global default_dry_run
            default_dry_run = True
            argv.pop(0)
        elif argument == '--access-token': # format 'keykeykey:secretsecret'
            argv.pop(0)
            access_token = argv.pop(0).split(':')
        elif argument == '--verbose':
            verbose = True
            argv.pop(0)

    if len(argv) < 3:
        print "Usage:", sys.argv[0], '--dry', 'get', 'page', 123
        print
        print " * [--dry|--verbose|--access-token ACCESS_TOKEN:ACCESS_KEY]"
        print " * get|put|post|delete|search"
        print " * page|note|attachment|comment"
        print " * [id]"
        print 
        sys.exit()

    if not verbose:
        sys.stderr.write("you can see more detailed information with --verbose option\n\n")
    method   = argv[0].upper()
    resource = argv[1].rstrip('s')
    target = None
    if len(argv) >= 3:
        target = int(argv[2])

    ##
    print method, resource, target or ''
    sn = Springnote()
    # go through authorization process
    if access_token is None:
        # 1. receive a request token
        request_token = sn.auth.fetch_request_token(verbose=verbose)
        print 'request token received:', (request_token.key, request_token.secret)

        # 2. user approves the request token
        print 'go to this url and approve:', sn.auth.authorize_url()
        raw_input('Press enter when complete. ')

        # 3. receive access token
        access_token = sn.auth.fetch_access_token(request_token, verbose=verbose)
        access_token_option = '--access-token %s:%s' % (access_token.key, access_token.secret)
        print 'your access token is ', (access_token.key, access_token.secret)
        print 'you can save it somewhere else and reuse it later like this:'
        print ' ', sys.argv[0], access_token_option, method, resource, target or ''
        print
    # use given access token
    else:
        sn.set_access_token(*access_token)
    ##
    if resource == 'page':
        import pprint
        if method == 'GET':
            if target is not None:
                url = "http://api.springnote.com/pages/%d.json" % target
                http_response = springnote.Springnote.springnote_request(
                    "GET", url, sign_token=access_token)
                pprint.pprint(http_response.read())
            else:
                url = "http://api.springnote.com/pages.json"
                http_response = springnote.Springnote.springnote_request(
                    "GET", url, sign_token=access_token)
                pprint.pprint(http_response.read())


if __name__ == '__main__':
    main()

