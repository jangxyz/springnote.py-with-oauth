from test_env import *
import urllib
import springnote

def patch(method, patched_object):
    original_object = patched_object
    try:
        method()
    finally:
        patched_object = original_object
        

def response():
    openid = urllib.quote_plus('http://jangxyz.myid.net/')
    response_param = {
        "oauth_token" :        "cd",
        "oauth_token_secret" : "ab",
        "open_id" :            openid,
    }
    response_mock = Mock({
        'read': urllib.urlencode(response_param)
    })

    response_mock.status = 200
    return response_mock
    

def request_token(response_mock=None):
    response_mock = response_mock or response()
    
    httpsconnection_mock = Mock({
        'request':     None,
        'getresponse': response_mock
    })

    springnote.httplib = Mock({ 
        'HTTPSConnection': httpsconnection_mock 
    })

    springnote.httplib.OK = 200

    #
    return springnote.httplib, httpsconnection_mock, response_mock
    

