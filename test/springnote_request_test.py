#!/usr/bin/python

'''
Test Springnote.springnote_request, by mocking out the actual connection

    * uses httplib


'''
import test_env
import unittest
from pmock import *; from pmock_xtnd import *
_object = object; from hamcrest import *; object = _object
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
        self.sn = springnote.Springnote

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

        self.sn.springnote_request("GET", "http://url.com", secure=False)

    @unittest.test
    def should_pass_method_url_headers_i_gave(self):
        """
            conn.request("PUT", "http://url.com/", headers={'key': 'value'})
        """
        http_method = "PUT"
        url = "http://url.com/"
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

        self.sn.springnote_request("GET", "http://url.com", secure=True)

    @unittest.test
    def default_content_type_is_json(self):
        """
            conn.request("PUT", "http://url.com/", headers={'key': 'value'})
        """
        json_content_type = {'Content-Type': 'application/json'}

        # mock
        self.httplib.expects(once()).method("HTTPConnection").will(return_value(self.conn))
        self.conn.expects(once()).getresponse()
        self.conn .expects(once()) .method("request") \
            .with_at_least(headers=dict_including(json_content_type))

        #
        self.sn.springnote_request("GET", "http://url.com/", secure=False)



class OauthRequestTestCase(unittest.TestCase):
    @unittest.test
    def should_have_consumer_token(self):
        oauth_req = springnote.Springnote.oauth_request("GET", "http://url.com")
        consumer_key = springnote.Springnote.consumer_token.key
        assert_that(oauth_req.parameters['oauth_consumer_key'], is_(consumer_key))

    @unittest.test
    def should_take_method_and_url(self):
        http_method, url = "GET", "http://url.com/"
        oauth_req = springnote.Springnote.oauth_request(http_method, url)
        assert_that(oauth_req.http_method, is_(http_method))
        assert_that(oauth_req.http_url,    is_(url))

    @unittest.test
    def should_have_signature_method(self): 
        oauth_req = springnote.Springnote.oauth_request("GET", "http://url.com")
        consumer_key = springnote.Springnote.consumer_token.key
        assert_that(oauth_req.parameters, has_key('oauth_signature_method'))
        assert_that(oauth_req.parameters, has_key('oauth_signature'))

    @unittest.test
    def should_have_basic_oauth_properties(self): 
        token = springnote.oauth.OAuthToken('key', 'secret')
        oauth_req = springnote.Springnote.oauth_request("GET", "http://url.com", sign_token=token)

        property_names = [ 'oauth_consumer_key', 'oauth_token', 
            'oauth_signature_method', 'oauth_signature', 
            'oauth_timestamp', 'oauth_nonce', 'oauth_version' ]
        for name in property_names:
            assert_that(oauth_req.parameters, has_key(name))

    @unittest.test
    def access_token_key_should_be_saved_to_sign_consumer_token(self):
        token = springnote.oauth.OAuthToken('key', 'secret')
        oauth_req = springnote.Springnote.oauth_request("GET", "http://url.com", sign_token=token)
        assert_that(oauth_req.parameters['oauth_token'], token.key)

        
    @unittest.test
    def oauth_parameters_should_be_packed_in_header(self): 
        """ parameters are joined by comma, and resides in request header under key 'Authorization'
        """
        class OAuthParamConstraint(object):
            def __repr__(self): return "%s.includes_valid_oauth_param()" % __name__
            def eval(self, arg):
                if 'Authorization' not in arg:
                    return False

                property_names = [ 'oauth_consumer_key', 
                           'oauth_signature_method', 'oauth_signature', 
                           'oauth_timestamp', 'oauth_nonce', 'oauth_version' ]
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
        springnote.Springnote.springnote_request("GET", "http://url.com/", secure=False)

        # restore 
        restore_httplib_module()


if __name__ == '__main__':
    unittest.main()

