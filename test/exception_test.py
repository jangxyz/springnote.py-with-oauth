#!/usr/bin/python
'''
    Test exceptions when using springnote.py
'''
import test_env
from   test_env import *

import unittest

from pmock      import *
from pmock_xtnd import *
from hamcrest      import *
from hamcrest_xtnd import *

import springnote

class HttplibRequestMockedTestCase(unittest.TestCase):
    def setUp(self):
        # httplib module being mocked 
        self.o_httplib = springnote.httplib

        # mocks
        self.response      = Mock()
        self.conn          = Mock()
        springnote.httplib = Mock()
        # httplib mock
        self.httplib = springnote.httplib
        self.httplib.NOT_FOUND             = 404
        self.httplib.INTERNAL_SERVER_ERROR = 500
        self.httplib .expects(once()) .method("HTTPConnection") \
            .will(return_value(self.conn))

        # connection mock
        self.conn .expects(once()) .method("request")
        self.conn .expects(once()) .method("getresponse") \
            .will(return_value(self.response)) \
            #.after('request')

        # response mock
        self.response.read = lambda: '{}'
        self.response.status = 200

        self.sn = springnote.Springnote()

    def tearDown(self):
        # restore mocked resources
        springnote.httplib = self.o_httplib

class NoNetworkExceptionTestCase(HttplibRequestMockedTestCase):
    def setUp(self):
        super(NoNetworkExceptionTestCase, self.__class__).setUp(self)

    @unittest.test
    def no_network_connection_should_raise_exception(self):
        ''' NoNetwork is raised when springnote_request() is called witout network connection '''
        # mock exception
        import socket
        self.conn.expects(once()).method("request") \
            .will(raise_exception(socket.gaierror("no network")))

        # run
        run = lambda: self.sn.springnote_request("GET", "some.url/with/path")
        should_raise(springnote.SpringnoteError.NoNetwork, when=run)

    @unittest.test
    def network_connection_should_not_raise_exception(self):
        ''' NoNetwork is not raised when springnote_request() is called with network connection '''
        self.sn.springnote_request("GET", "some.url/with/path")

class ParseErrorTestCase(unittest.TestCase):
    @unittest.test
    def from_json_should_raise_parse_error_if_invalid_json_given(self):
        ''' from_json should raise ParseEror if json data is invalid '''
        bad_json = '{{{{"page": {' \
            '"tags": "test", ' \
            '"title": "TestPage" ' \
        '}}]]'

        run = lambda: springnote.Page.from_json(data=bad_json, auth=None)
        should_raise(springnote.SpringnoteError.ParseError, when=run)

    @unittest.test
    def from_json_should_raise_parse_error_if_json_is_different_resource(self):
        ''' from_json should raise ParseError if it cannot build resource from json data '''
        bad_json = '[1,2,3]'
        
        run = lambda: springnote.Page.from_json(data=bad_json, auth=None)
        should_raise(springnote.SpringnoteError.ParseError, when=run)

    @unittest.test
    def from_json_should_not_raise_parse_error_on_valid_json(self):
        ''' from_json should not raise ParseError on valid json data '''
        good_json = '{"page": {' \
            '"rights": null, ' \
            '"source": "\\u003Cp\\u003ENone\\u003C/p\\u003E\\n", ' \
            '"creator": "http://deepblue.myid.net/", ' \
            '"date_created": "2007/10/26 05:30:08 +0000", ' \
            '"contributor_modified": "http://deepblue.myid.net/", ' \
            '"date_modified": "2008/01/08 10:55:36 +0000", ' \
            '"relation_is_part_of": 1, ' \
            '"identifier": 4, ' \
            '"tags": "test", ' \
            '"title": "TestPage" ' \
        '}}'
        
        springnote.Page.from_json(data=good_json, auth=None)

class InvalidOptionTestCase(unittest.TestCase):
    def setUp(self):
        self.sn = springnote.Springnote()
    @unittest.test
    def raised_if_proper_argument_is_not_given(self):
        ''' InvalidOption is raised if proper argument is not given 
        for example, trying to fetch a page without an id.
        '''
        page    = springnote.Page(self.sn)
        page.id = None
        run     = lambda: page.get()

        should_raise(springnote.SpringnoteError.InvalidOption, when=run)
        should_not_call_method(springnote.Springnote, 'springnote_request', 
            when = run)

    @unittest.test
    def not_raised_if_given_proper_argument(self):
        ''' InvalidOption is not raised with proper argument '''
        page    = springnote.Page(self.sn)
        page.id = 123
        run     = lambda: page.get()

        should_call_method(springnote.Springnote, 'springnote_request', when=run)

    @unittest.test
    def raised_if_invalid_parameter_is_set(self):
        ''' InvalidOption is raised if not-permittable parameter is given '''
        run = lambda: springnote.Page.list(self.sn, sort='anything') # invalid sort
        should_raise(springnote.SpringnoteError.InvalidOption, when=run)

    @unittest.test
    def not_raised_with_valid_parameters(self):
        ''' InvalidOption is not raised with permittable parameters '''
        run = lambda: springnote.Page.list(self.sn, 
            # each of the parameters are valid (not the whole)
            sort        = 'title', # sort by title
            order       = 'desc',  # in descending order
            count       = 10,      # retrieve 10 pages
            offset      = 3,       # on the 3rd page
            q           = 'query',  # search by word 'query'
            tags        = 'python', # with tag 'python' included
            identifiers = "563954,1123", # retrieve only the following pages
        ) 

        should_call_method(springnote.Springnote, 'springnote_request', when=run)
        should_raise(springnote.SpringnoteError.InvalidOption,
            when = lambda: springnote.Page.list(self.sn, sort='anything') # invalid sort
        )

class Response401TestCase(HttplibRequestMockedTestCase):
    def setUp(self):
        super(Response401TestCase, self.__class__).setUp(self)
        self.response.status = 401  # always return 401

    @unittest.test
    def invalid_request_for_request_token(self):
        ''' 401 is raised when invalid request for request token 
        
        don't forget to:
         1. POST method.
         2. use HTTPS.
         3. no token to sign.
        '''
        # mock response
        resp_data = '''[{"error": {"error_type": "InvalidOauthRequest", "description": "signature_invalid, base string: POST\u0026https%3A%2F%2Fapi.springnote.com%2Foauth%2Frequest_token\u0026oauth_consumer_key%3D1y64mD1KSo885Eq4Vz2w%26oauth_nonce%123456789A%26oauth_signature_method%3DHMAC-SHA1%26oauth_timestamp%3D1270374296%26oauth_token%3DINVALID%26oauth_version%3D1.0"}}]'''
        self.response.read = lambda: resp_data
        self.httplib.expects(once()).method("HTTPSConnection") \
            .will(return_value(self.conn))

        self.sn.set_access_token('INVALID', 'TOKEN')
        run = lambda: self.sn.fetch_request_token()
        #self.tearDown(); self.sn = springnote.Springnote(('INVALID', 'TOKEN')); run()
        should_raise(springnote.SpringnoteError.Response, when=run)

    @unittest.test
    def invalid_request_for_access_token(self):
        ''' 401 is raised when requesting access token with invalid request token 
        
        don't forget to:
         1. POST method
         2. use HTTPS
         3. let the user authorize request token
         3. sign with the request token
        '''
        # mock response
        resp_data = '''[{"error": {"error_type": "InvalidOauthRequest", "description": "request_token_invalid()"}}]'''
        self.response.read = lambda: resp_data
        self.httplib.expects(once()).method("HTTPSConnection") \
            .will(return_value(self.conn))

        request_token = springnote.Springnote.format_token('', '')
        run = lambda: self.sn.fetch_access_token(request_token)
        should_raise(springnote.SpringnoteError.Response, when=run)

    @unittest.test
    def invalid_access_token(self):
        ''' 401 is raised when invalid access token is used '''
        # mock response
        resp_data = '''[{"error": {"error_type": "InvalidOauthRequest", "description": "access_token_invalid(KEY:INVALID)"}}]'''
        self.response.read = lambda: resp_data

        self.sn.set_access_token('KEY:INVALID', 'SECRET:ACCESS_TOKEN')
        run = lambda: self.sn.get_page(id=563954)
        should_raise(springnote.SpringnoteError.Response, when=run)

    @unittest.test
    def invalid_oauth_request(self):
        ''' 401 is raised when invalid oauth request is generated.
        happens frequently when wrong parameters are set '''
        # mock response
        resp_data = '''[{"error": {"error_type": "InvalidOauthRequest", "description": "signature_invalid, base string: GET\\u0026http%3A%2F%2Fapi.springnote.com%2Fpages.json\\u0026identifiers%3D563954%26oauth_consumer_key%3D162DSyqm28o355V7zEKw%26oauth_nonce%3D50873559%26oauth_signature_method%3DHMAC-SHA1%26oauth_timestamp%3D1270376540%26oauth_token%3D0597eM6BZAQWiEdtX6LtA%26oauth_version%3D1.0"}}]'''
        self.response.read = lambda: resp_data

        method = "GET"
        url    = "http://api.springnote.com/pages.json?identifiers=563954"
        params = {} # invalid params - you need identifiers as parameters
        page = springnote.Page(self.sn)
        run = lambda: page.request(url, method, params)
        should_raise(springnote.SpringnoteError.Response, when=run)

class Response403TestCase(HttplibRequestMockedTestCase):
    def setUp(self):
        super(Response403TestCase, self.__class__).setUp(self)
        self.response.status = 403

    @unittest.test
    def unauthorized_access(self):
        ''' 403 is raised when accessing other's private resource '''
        resp_data = '''[{"error": {"error_type": "NoPermission", "description": "NoPermission"}}]'''
        self.response.read = lambda: resp_data

        run = lambda: springnote.Page(self.sn, id=123).get()
        should_raise(springnote.SpringnoteError.Response, when=run)

class Response404TestCase(HttplibRequestMockedTestCase):
    def setUp(self):
        super(Response404TestCase, self.__class__).setUp(self)
        self.response.status = 404

    @unittest.test
    def accessing_unexisting_page(self):
        ''' 404 is raised in json format when accessing non-existing resource '''
        resp_data = '''[{"error": {"error_type": "NotFound", "description": "NotFound"}}]'''
        self.response.read = lambda: resp_data

        run = lambda: springnote.Page(self.sn, id=3).get()
        #self.tearDown(); self.sn = springnote.Springnote(); run()
        should_raise(springnote.SpringnoteError.Response, when=run)

    @unittest.test
    def wrong_path_raises_404(self):
        ''' 404 is raised in html format when requesting invalid path '''
        resp_data = '''<html><head><meta content="text/html;charset=UTF-8" http-equiv="Content-Type" /></head><body></body></html>'''
        self.response.read = lambda: resp_data

        method = "GET"
        path   = 'http://api.springnote.com/pages.json' # should be path, not url!
        page = springnote.Page(self.sn)
        run = lambda: page.request(path, method)
        #run()
        should_raise(springnote.SpringnoteError.Response, when=run)


class Response500TestCase(HttplibRequestMockedTestCase):
    def setUp(self):
        super(Response500TestCase, self.__class__).setUp(self)
        self.response.status = 500

    @unittest.test
    def requesting_to_invalid_url_raises_500(self):
        ''' 500 is raised in html format sometimes when invalid url is requested.

        for example,
            POST http://api.springnote.com/pages/attachments.json (no page id)
        this is funny, because GET and DELETE returns 404. (who cares, they're all just errors anyway)
        '''
        resp_data = '''<html><head><meta http-equiv="Content-Type" content="text/html;charset=UTF-8" /></head><body></body></html>'''
        self.response.read = lambda: resp_data

        method = "POST"
        url    = "http://api.springnote.com/pages/attachments.json"
        attach = springnote.Attachment(springnote.Page(self.sn))
        run = lambda: attach.request(url, method)
        should_raise(springnote.SpringnoteError.Response, when=run)
        
    @unittest.test
    def post_attachment_without_file_raises_500(self):
        ''' 500 is raised in json format when invalid action is performed.

        for example, POSTing attachment without any file data.
        '''
        resp_data = '''[{"error": {"error_type": "InvalidAction", "description": "InvalidAction"}}]'''
        self.response.read = lambda: resp_data

        method = "POST"
        path   = '/pages/563954/attachments.json'
        attach = springnote.Attachment(springnote.Page(self.sn))
        run = lambda: attach.request(path, method) # no file!
        should_raise(springnote.SpringnoteError.Response, when=run)

if __name__ == '__main__':
    unittest.main()

