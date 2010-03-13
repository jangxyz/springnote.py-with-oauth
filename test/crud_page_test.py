#!/usr/bin/python
'''
    Test basic crud calls for Page Resource
'''
import test_env

import unittest, re
from pmock import *
from pmock_xtnd import *

from hamcrest import *;
from hamcrest_xtnd import *

import springnote

def set_url(id, note=None, params={}):
    return "http://api.springnote.com/pages/%d.json" % id

# callabla Mock
class CMock(Mock):
    def __init__(self, *arg, **kwarg): 
        Mock.__init__(self, `(arg, kwarg)`)
    def __call__(self, *arg, **kwarg): return self

def mock_springnote_class():
    global original_sn, original_sn_rsrc
    original_sn = springnote.Springnote
    host = springnote.Springnote.HOST
    springnote.Springnote = CMock()         # mock class Springnote
    springnote.Springnote.HOST = host

    # don't use SpringnoteResource._build_model_from_response
    original_sn_rsrc = springnote.SpringnoteResource
    def stub__build_model_from_response(self, *args, **kwargs):
        #print 'stub __build_model_from_response:', self, args, kwargs
        pass
    springnote.SpringnoteResource._build_model_from_response = stub__build_model_from_response

    return springnote.Springnote, springnote.SpringnoteResource

def restore_springnote_class():
    springnote.Springnote = original_sn
    springnote.SpringnoteResource = original_sn_rsrc
    #springnote = original_module

def should_call_method(object, method_name, callable):
    class IsCalled(Exception): pass
    def is_called(*args, **kwarg): raise IsCalled()
    # save
    orig = getattr(object, method_name)
    # patch
    setattr(object, method_name, is_called)

    # run
    try:
        callable()
        raise AssertionError, "method %s is not called" % method_name
    except IsCalled:
        # verify
        pass 
    finally:
        # restore
        setattr(object, method_name, orig)

def should_raise(exception, callable):
    try:
        callable()
        self.fail("did not raise exception %s" % exception)
    except exception:
        pass # proper exception raised
    except Exception, e:
        error_msg = 'expected %s to be raised but instead got %s:"%s"' % (exception, type(e), e)
        raise AssertionError, error_msg

class CrudPageTestCase(unittest.TestCase):
    def setUp(self):
        self.springnote = springnote.Springnote()
        mock_springnote_class()
        self.sn = springnote.Springnote

        self.m_get_response = Mock()

        self.expects_springnote_request = \
            springnote.Springnote.expects(once()).method('springnote_request') \
            .will(return_value(self.m_get_response))

        #self.m_get_response.expects(once()).read().will(return_value('{"page": {}}'))
        self.m_get_response.expects(once()).read()
        self.m_get_response.status = 200

        self.token = ('FAKE_KEY', 'FAKE_SECRET')

    def tearDown(self):
        restore_springnote_class()

    def get_page_calls_springnote_request(self):
        """ GET """
        id = 123
        self.sn.expects(once())           \
            .method("springnote_request") \
                .with_at_least(url=eq(set_url(id)), method=eq("GET"))

        self.springnote.get_page(id)

    @unittest.test
    def get_method_with_id_calls_get_page_request(self):
        """ page.get() with id calls get page request

        Page(self.token, id=123).get()
        calls springnote_request(method="GET", url=".*/pages/123[.].*", ...) """
        id = 123

        # mock
        url_pattern = "/pages/%d." % id
        self.expects_springnote_request .with_at_least(
            method = eq("GET"), 
            url    = string_contains(url_pattern)
        )
        springnote.Page(self.token, id=id).get()

    @unittest.test
    def get_method_without_id_is_invalid(self):
        """ page.get() without id is invalid 
        Page(self.token).get() raises InvalidOption error """
        should_raise(springnote.SpringnoteError.InvalidOption, \
            lambda: springnote.Page(self.token).get())

    @unittest.test
    def get_method_calls_set_path_params(self):
        ''' page.get() calls _set_path_params() '''
        note, id = 'jangxyz', 123
        should_call_method(springnote.Page, '_set_path_params', 
            lambda: springnote.Page(self.token, note=note, id=id).get()
        )

    @unittest.test
    def save_method_without_id_calls_create_page_request(self):
        """ page.save() without id calls create page request
        Page(self.token, title='title', source='source').save()
        calls springnote_request(method="POST", body={title:..,source:..}, ..) """

        title  = 'some title'
        source = 'blah blah ahaha'

        # TODO: check access token
        # TODO: replace with pmock.or
        # TODO: make regex more verbose
        # methdo: "POST"
        # source: '{"page": {"source": "blah blah ahaha", "title": "some title"}}'
        pattern1 = '"title"\s*:\s*"%s"\s*,\s*"source"\s*:\s*"%s"' % (title, source)
        pattern2 = '"source"\s*:\s*"%s",\s*"title"\s*:\s*"%s"\s*' % (source, title)
        body_pattern = re.compile("(%s|%s)" % (pattern1, pattern2))
        self.expects_springnote_request \
            .with_at_least(method=eq("POST"), body=string_contains(body_pattern))

        # run
        springnote.Page(self.token, title=title, source=source).save()


    @unittest.test
    def save_method_with_id_calls_update_page_request(self):
        """ page.save() with id calls update page request
        Page(self.token, id=123, source='edited').save()
        calls springnote_request(method="PUT", url="../123.", body={source:..}, ..) """
        id     = 123
        source = 'edited'

        # method: "PUT"
        # url:    "/pages/123."
        # source: "source": "edited"
        url_pattern  = re.compile('''/pages/%d[.]''' % id) 
        body_pattern = re.compile('''["']source["']\s*:\s*["']%s["']''' % source)
        self.expects_springnote_request .with_at_least(
            method = eq("PUT"), 
            url    = string_contains(url_pattern),
            body   = string_contains(body_pattern)
        )

        # run
        springnote.Page(self.token, id=id, source=source).save()


    @unittest.test
    def save_method_calls_set_path_params(self):
        ''' page.save() calls _set_path_params() '''
        note, id = 'jangxyz', 123
        should_call_method(springnote.Page, '_set_path_params', 
            lambda: springnote.Page(self.token, note=note, id=id).save()
        )


    @unittest.test
    def delete_method_with_id_calls_delete_page_request(self):
        """ page.delete() with id calls delete page request
        Page(self.token, id=123).delete() 
        calls springnote_request(method="DELETE", url="../123.", ..) """
        id = 123

        # method: "DELETE"
        # url:    "/pages/123."
        url_pattern  = re.compile('''/pages/%d[.]''' % id) 
        self.expects_springnote_request .with_at_least(
            method = eq("DELETE"), 
            url    = string_contains(url_pattern),
        )

        # run
        springnote.Page(self.token, id=id).delete()

    @unittest.test
    def delete_method_calls__set_path_params(self):
        ''' page.delete() calls _set_path_params() '''
        note, id = 'jangxyz', 123
        should_call_method(springnote.Page, '_set_path_params', 
            lambda: springnote.Page(self.token, note=note, id=id).delete()
        )


    @unittest.test
    def delete_method_without_id_is_invalid(self):
        """ page.delete() without id is invalid
        
        Page(self.token).delete() raises InvalidOption error """
        try:
            springnote.Page(self.token).delete()
            self.fail("did not raise exception")
        except springnote.SpringnoteError.InvalidOption:
            pass # proper exception raised


    @unittest.test
    def format_path_and_parameters(self):
        ''' _set_path_params() formats path and params according to note and page id 

        id   sets "/$id$"  in path, while 
        note sets 'domain' key in params and 'domain=$domain' in query
            id=None: path '/pages.json'
            id=1234: path '/pages/1234.json'
            note='ab', id=None: ('/pages.json?domain=ab',      {'domain':'ab'})
            note='ab', id=1234: ('/pages/1234.json?domain=ab', {'domain':'ab'}) 
        '''

        Page = springnote.Page
        t = self.token

        # no note
        assert_that(Page(t, note=None, id=None)._set_path_params(),
                        is_(('/pages.json',      {})))
        assert_that(Page(t, note=None, id=1234)._set_path_params(),
                        is_(('/pages/1234.json', {})))

        # with note
        assert_that(Page(t, note='ab', id=None)._set_path_params(),
                        is_(('/pages.json?domain=ab',      {'domain':'ab'})))
        assert_that(Page(t, note='ab', id=1234)._set_path_params(),
                        is_(('/pages/1234.json?domain=ab', {'domain':'ab'})))



if __name__ == '__main__':
    unittest.main()

