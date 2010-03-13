#!/usr/bin/python
'''
Test basic crud calls for page 
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
    def get_method_calls_get_page_request(self):
        """ Page(access_token, id=123).get() 
        calls springnote_request(method="GET", url=".*/123[.].*", ...) """
        id = 123

        # mock
        url_pattern = "/%d." % id
        self.expects_springnote_request \
            .with_at_least(method=eq("GET"), url=string_contains(url_pattern))
        #springnote.SpringnoteResource.expects(once()).__build_model_from_response() \
        #    .will(return_value(None))

        # run
        access_token = ('FAKE_TOKEN', 'FAKE_KEY')
        springnote.Page(access_token, id=id).get()

    @unittest.test
    def get_method_with_note_calls_with_domain_param(self):
        """ Page(access_token, note='jangxyz', id=123).get() 
        calls springnote_request(method="GET", url=".*/123[.].*?domain=jangxyz", ...) """
        note = 'jangxyz'
        id   = 123

        # mock
        url_pattern = re.compile("/%d[.].*domain=%s" % (id,note))
        self.expects_springnote_request \
            .with_at_least(method=eq("GET"), url=string_contains(url_pattern))

        # run
        access_token = ('FAKE_TOKEN', 'FAKE_KEY')
        springnote.Page(access_token, id=id, note=note).get()

    @unittest.test
    def save_method_without_id_calls_create_page_request(self):
        """ Page(access_token, title='title', source='source').save()
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
        access_token = ('FAKE_TOKEN', 'FAKE_KEY')
        springnote.Page(access_token, title=title, source=source).save()


    @unittest.test
    def save_method_with_id_calls_update_page_request(self):
        """ Page(access_token, id=123, source='edited').save()
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
        access_token = ('FAKE_TOKEN', 'FAKE_KEY')
        springnote.Page(access_token, id=id, source=source).save()

    @unittest.test
    def save_method_with_id_and_note_sets_proper_path_and_params(self):
        """ Page(access_token, id=123, source='edited').save()
        calls springnote_request(method="PUT", url="../123.", ..) """

        id   = 123
        note = 'some_note'

        # method: "PUT"
        # params: {'domain': 'some_note'}
        # url:    "/pages/123.json?domain=some_note"
        url_pattern  = re.compile('''/pages/%d[.].*?.*domain=%s''' % (id,note))
        self.expects_springnote_request .with_at_least(
            method = eq("PUT"), 
            url    = string_contains(url_pattern),
            params = dict_including({'domain': note}),
        )

        # run
        access_token = ('FAKE_TOKEN', 'FAKE_KEY')
        springnote.Page(access_token, note=note, id=id).save()


if __name__ == '__main__':
    unittest.main()

