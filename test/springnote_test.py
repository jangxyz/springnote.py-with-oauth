#!/usr/bin/python

import unittest
from pythonmock import Mock

import test_env
import springnote

class RequestMock:
    @staticmethod
    def mock_request_token(response_mock=None):
        if response_mock is None:
            openid = 'http%3A%2F%2Fjangxyz.myid.net%2F'
            response_mock = Mock({
                'read':  "oauth_token=cd&oauth_token_secret=ab&open_id=" + openid,
            })
            response_mock.status = 200

        springnote.httplib = Mock({
            'HTTPSConnection': Mock({
                'request':     None,
                'getresponse': response_mock
            })
        })         
        springnote.httplib.OK = 200
    

class SpringnoteClassBasicTestCase(unittest.TestCase):
    def setUp(self):
        self.client = springnote.Springnote()

    def test_initializing_springnote_with_no_arguments(self):
        assert self.client.consumer_token.key    == springnote.CONSUMER_TOKEN_KEY
        assert self.client.consumer_token.secret == springnote.CONSUMER_TOKEN_SECRET
        
    def test_initializing_springnote_with_consumer_token_tuple(self):
        client = springnote.Springnote(('abc', 'def'))
        assert client.consumer_token.key    == 'abc'
        assert client.consumer_token.secret == 'def'

    def test_new_instance_should_not_be_authorized(self):
        assert self.client.is_authorized() == False

    def test_fetch_request_token(self):
        """ as a consumer, it should fetch request token from springnote.com """
        RequestMock.mock_request_token()

        self.client.fetch_request_token()

    def test_new_instance_should_have_authorize_url(self):
        token = springnote.oauth.OAuthToken('some', 'token')
        assert springnote.Springnote.AUTHORIZATION_URL in self.client.authorize_url(token)


if __name__ == '__main__':
    try:
        import testoob
        testoob.main()
    except ImportError:
        unittest.main()


