#!/usr/bin/python

import unittest
from pythonmock import Mock

import os, sys; sys.path.append( os.path.join(os.path.dirname(__file__), os.path.pardir) )
import springnote

class RequestMock:
    @staticmethod
    def mock_response_for_request_token(response_mock=None):
        if response_mock is None:
            response_mock = Mock({'read': "oauth_token=cd&oauth_token_secret=ab&open_id=http%3A%2F%2Fchanju.myid.net%2F"})

        springnote.httplib = Mock({
            'HTTPSConnection': Mock({
                'request':     None,
                'getresponse': response_mock
            })
        })         
    

class SpringnoteClassBasicTestCase(unittest.TestCase):
    def setUp(self):
        self.client = springnote.Springnote()

    def test_initializing_springnote_with_no_arguments(self):
        assert self.client.consumer_token == (springnote.CONSUMER_TOKEN_KEY, springnote.CONSUMER_TOKEN_SECRET)
        
    def test_initializing_springnote_with_consumer_token_tuple(self):
        client = springnote.Springnote(('abc', 'def'))
        assert client.consumer_token == ('abc', 'def')

    def test_new_instance_should_not_be_authorized(self):
        assert self.client.is_authorized() == False

    def test_fetch_request_token(self):
        """ as a consumer, it should fetch request token from springnote.com """
        self.client.fetch_request_token()
        self.fail("Implement me!")

    def test_new_instance_should_have_authorize_url(self):
        assert springnote.Springnote.AUTHORIZATION_URL in self.client.authorize_url()


if __name__ == '__main__':
    try:
        import testoob
        testoob.main()
    except ImportError:
        unittest.main()


