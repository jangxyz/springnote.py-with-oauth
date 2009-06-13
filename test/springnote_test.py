#!/usr/bin/python
# -*- coding: utf-8 -*-

import unittest
from   hamcrest import *
import mocking

from   test_env import *
import springnote


def poke(d, *keys):
    entry = d.copy()
    for key in keys:
        entry = entry.get(key, {})
    return entry or None

class SpringnoteClassBasicTestCase(unittest.TestCase):
    def setUp(self):
        self.client = springnote.Springnote()

    def test_initializing_springnote_with_no_arguments(self):
        token = self.client.consumer_token
        assert_that(token.key, is_(springnote.CONSUMER_TOKEN_KEY), 'token key')
        assert_that(token.secret, is_(springnote.CONSUMER_TOKEN_SECRET), 'token secret')
        
    def test_initializing_springnote_with_consumer_token_tuple(self):
        client = springnote.Springnote(('abc', 'def'))
        token = client.consumer_token
        assert_that( token.key, is_('abc') )
        assert_that( token.secret, is_('def') )

    def test_new_instance_should_not_be_authorized(self):
        """ client should be authorized before use """
        assert_that(self.client.is_authorized(), is_(False))


class FetchingRequestTokenTestCase(unittest.TestCase):
    """ as a consumer, it should fetch request token from springnote """
    def setUp(self):
        self.client = springnote.Springnote()
        self.original_httplib = springnote.httplib
        mocks =  mocking.request_token()
        self.httplib, self.https_connection, self.response = mocks

    def tearDown(self):
        springnote.httplib = self.original_httplib


    def test_posts_to_request_url(self):
        # execute
        request_token = self.client.fetch_request_token()

        # test
        request_calls = self.https_connection.mockGetNamedCalls("request")
        request_calls_params = [method.params for method in request_calls]
        assert_that(request_calls_params, has_item(("POST", springnote.Springnote.REQUEST_TOKEN_URL)
))


    def test_returns_token_with_key_and_secret_on_status_ok(self):
        request_token = self.client.fetch_request_token()
        assert_that(request_token.key, is_(instance_of(str)))
        assert_that(request_token.secret, is_(instance_of(str)))



class AuthorizingUrlTestCase(unittest.TestCase):
    def setUp(self):
        self.client = springnote.Springnote()
        self.client.request_token = springnote.oauth.OAuthToken('some', 'token')

        self.original = springnote.httplib
        mocking.request_token()

    def tearDown(self):
        springnote.httplib = self.original

    def test_should_have_authorize_url(self):
        url = self.client.authorize_url()
        assert_that(url, contains_string(springnote.Springnote.AUTHORIZATION_URL))

    def test_should_have_token_key_in_url(self):
        url = self.client.authorize_url()
        token = self.client.request_token
        assert_that(url, contains_string(token.key))

    def test_should_have_callback_url_if_given(self):
        callback_url = "http://some.callback.url/"
        url = self.client.authorize_url(callback=callback_url)

        escaped = springnote.urllib.quote_plus(callback_url)
        assert_that(url, contains_string(escaped))



class FetchingAccessTokenTestCase(unittest.TestCase):
    """ consumer의 자격으로 springnote.com으로부터 access token을 받아옵니다.  """
    def setUp(self):
        self.client = springnote.Springnote()
        self.client.request_token = springnote.oauth.OAuthToken('some', 'token')

        self.original_httplib = springnote.httplib
        mocks =  mocking.request_token()
        self.httplib, self.https_connection, self.response = mocks

    def tearDown(self):
        springnote.httplib = self.original_httplib
    

    def test_posts_to_access_url_with_request_token_in_it(self):
        """ send POST request to ACCESS_URL, with key of request token in header """
        request_token = self.client.fetch_request_token()
        self.client.fetch_access_token()

        def check_param(method):
            parameters = ("POST", springnote.Springnote.ACCESS_TOKEN_URL)
            header_authorization = method.kwparams.get('headers',{}).get('Authorization','')
            return method.params == parameters and \
                   'oauth_token="%s"' % request_token.key in header_authorization


        such_calls = filter(check_param, self.https_connection.mockGetNamedCalls("request"))
        assert_that(such_calls, is_not(empty))


    def test_returns_token_with_key_and_secret_when_status_ok(self):
        request_token = self.client.fetch_request_token()

        assert_that(request_token.key, is_(instance_of(str)))
        assert_that(request_token.secret, is_(instance_of(str)))



if __name__ == '__main__':
    try:
        import testoob
        testoob.main()
    except ImportError:
        unittest.main()


