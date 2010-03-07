#!/usr/bin/python

'''
Test Springnote.springnote_request, by mocking out the actual connection

    * uses httplib


'''
import test_env
import unittest, types
from pmock import *
from pmock_xtnd import *

from hamcrest import *;
from hamcrest_xtnd import *

import springnote

def mock_httplib_module():
    global original_httplib
    original_httplib = springnote.httplib
    springnote.httplib = Mock() # mock httplib

def restore_httplib_module():
    springnote.httplib = original_httplib

class HttpParamsTestCase(unittest.TestCase):
    @unittest.setup
    def mock_httplib(self):
        mock_httplib_module()
        self.conn    = Mock() # mock connection instance
        self.httplib = springnote.httplib
        self.sn = springnote.Springnote()

    @unittest.teardown
    def restore_httplib(self):
        restore_httplib_module()

    @unittest.test
    def http_connection_should_be_requested_and_responsed(self):
        """
            conn = httplib.HTTPConnection(...)
            conn.request(...)
            conn.getresult()
        """
        self.httplib \
            .expects(once()) .method("HTTPConnection") \
            .will(return_value(self.conn))
        self.conn .expects(once()) .method("request") \
            .after("HTTPConnection", self.httplib)
        self.conn .expects(once()) .getresponse() .after("request")

        self.sn.springnote_request("GET", "http://url.com/data.json", secure=False)

    @unittest.test
    def should_pass_method_url_headers_i_gave(self):
        """
            conn.request("PUT", "http://url.com/data.json", headers={'key': 'value'})
        """
        http_method = "PUT"
        url = "http://url.com/data.json"
        headers = {'header-key': 'value'}

        # mock
        self.httplib.expects(once()).method("HTTPConnection").will(return_value(self.conn))
        self.conn.expects(once()).getresponse()
        self.conn .expects(once()) \
            .method("request") \
            .with_at_least(eq(http_method), eq(url), \
                headers=dict_including(headers.copy()))

        #
        self.sn.springnote_request(http_method, url, headers=headers, secure=False)

    @unittest.test
    def you_can_use_https_by_giving_secure_argument_true(self):
        """
            conn = httplib.HTTPSConnection(...)
            conn.request(...)
            conn.getresult()
        """
        conn = Mock()
        springnote.httplib \
            .expects(once()).method("HTTPSConnection") \
            .will(return_value(conn))
        conn.expects(once()).method("request") \
            .after("HTTPSConnection", springnote.httplib)
        conn.expects(once()).getresponse().after("request")

        self.sn.springnote_request("GET", "http://url.com/data.json", secure=True)

    @unittest.test
    def default_content_type_is_json(self):
        """
            conn.request("PUT", "http://url.com/data.json", headers={'key': 'value'})
        """
        json_content_type = {'Content-Type': 'application/json'}

        # mock
        self.httplib.expects(once()).method("HTTPConnection").will(return_value(self.conn))
        self.conn.expects(once()).getresponse()
        self.conn .expects(once()) .method("request") \
            .with_at_least(headers=dict_including(json_content_type))

        #
        self.sn.springnote_request("GET", "http://url.com/data.json")

    @unittest.test
    def file_object_body_should_be_converted_to_multipart_str(self):
        """
            when a file object is given as a body,
            it needs to convert to multipart string. 

            an example is shown below:

                '--AaB03x\r\n'                                     \
                'Content-Disposition: form-data; name="Filedata"; filename="filename.py"\r\n' \
                'Content-Transfer-Encoding: binary\r\n'            \
                'Content-Type: application/octet-stream\r\n\r\n'   \
                '*** This is where the content of file is. ***\r\n' \
                '--AaB03x--\r\n'
        """
        data = Mock()
        data.name = "test_file.txt"
        data_content = "** TEST FILE **"
        data.expects(once()).read().will(return_value(data_content))

        # mock
        self.httplib.expects(once()).method("HTTPConnection").will(return_value(self.conn))
        self.conn.expects(once()).getresponse()
        self.conn.expects(once()).method("request") \
            .with_at_least(body=string_contains('Content-Disposition: form-data;')) \
            .with_at_least(body=string_contains('name="Filedata"')) \
            .with_at_least(body=string_contains('filename="%s"' % data.name)) \
            .with_at_least(body=string_contains(data_content))

        #
        self.sn.springnote_request("POST", "http://url.com/data", body=data)
        
    @unittest.test
    def content_type_should_not_be_json_when_posting_file(self):
        ''' when given POST and file object as data, even if url finishes with
        .json, header should not have {'Content-Type': 'application/json'} '''
        data = Mock()
        data.name = "test_file.txt"
        data_content = "** TEST FILE **"
        data.expects(once()).read().will(return_value(data_content))

        # mock
        self.httplib.expects(once()).method("HTTPConnection").will(return_value(self.conn))
        self.conn.expects(once()).getresponse()
        self.conn.expects(once()).method("request") \
            .with_at_least(headers=not_contains_value("application/json"))

        #
        self.sn.springnote_request("POST", "http://url.com/upload.json", body=data)


class OauthRequestTestCase(unittest.TestCase):
    @unittest.test
    def should_have_consumer_token(self):
        oauth_req = springnote.Springnote().oauth_request("GET", "http://url.com/data.json")
        consumer_key = springnote.Springnote.consumer_token.key
        assert_that(oauth_req.parameters['oauth_consumer_key'], is_(consumer_key))

    @unittest.test
    def should_take_method_and_url(self):
        http_method, url = "GET", "http://url.com/data.json"
        oauth_req = springnote.Springnote().oauth_request(http_method, url)
        assert_that(oauth_req.http_method, is_(http_method))
        assert_that(oauth_req.http_url,    is_(url))

    @unittest.test
    def should_have_signature_method(self): 
        oauth_req = springnote.Springnote().oauth_request("GET", "http://url.com/data.json")
        consumer_key = springnote.Springnote.consumer_token.key
        assert_that(oauth_req.parameters, has_key('oauth_signature_method'))
        assert_that(oauth_req.parameters, has_key('oauth_signature'))

    @unittest.test
    def should_have_basic_oauth_properties(self): 
        token = springnote.oauth.OAuthToken('key', 'secret')
        oauth_req = springnote.Springnote(access_token=token).oauth_request("GET", "http://url.com/data.json")

        property_names = [ 'oauth_consumer_key', 'oauth_token', 
            'oauth_signature_method', 'oauth_signature', 
            'oauth_timestamp', 'oauth_nonce', 'oauth_version' ]
        for name in property_names:
            assert_that(oauth_req.parameters, has_key(name))

    @unittest.test
    def access_token_key_should_be_saved_to_sign_consumer_token(self):
        token = springnote.oauth.OAuthToken('key', 'secret')
        oauth_req = springnote.Springnote(access_token=token).oauth_request("GET", "http://url.com/data.json")
        assert_that(oauth_req.parameters['oauth_token'], token.key)

        
    @unittest.test
    def oauth_parameters_should_be_packed_in_header(self): 
        """ parameters are joined by comma, and resides in request header under key 'Authorization'
        """
        class OAuthParamConstraint(types.ObjectType):
            def __repr__(self): return "%s.includes_valid_oauth_param()" % __name__
            def eval(self, arg):
                if 'Authorization' not in arg:
                    return False
                property_names = [ 'oauth_consumer_key', 'oauth_timestamp', 
                            'oauth_signature_method', 'oauth_signature', 
                            'oauth_nonce', 'oauth_version' ]
                for name in property_names:
                    if "%s=" % name not in arg['Authorization']:
                        return False
                else:
                    return True
        includes_valid_oauth_param = OAuthParamConstraint

        # mock
        mock_httplib_module() # springnote.httplib
        conn = Mock()
        springnote.httplib.expects(once()).method("HTTPConnection") \
            .will(return_value(conn))
        conn.expects(once()).getresponse()
        conn.expects(once()).method("request") \
            .with_at_least(headers=includes_valid_oauth_param())

        #
        springnote.Springnote().springnote_request("GET", "http://url.com/data.json", secure=False)

        # restore 
        restore_httplib_module()


if __name__ == '__main__':
    unittest.main()

