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
    global original_sn, original_sn_rsrc, original_page
    original_sn = springnote.Springnote
    host = springnote.Springnote.HOST
    original_page = springnote.Page
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
    springnote.Page = original_page
    #springnote = original_module

def should_call_method(object, method_name, callable, method_type=None):
    class IsCalled(Exception): pass
    def is_called(*args, **kwarg): raise IsCalled()
    if method_type is not None: is_called = method_type(is_called)
    # save
    orig = getattr(object, method_name)
    if method_type is not None: orig = method_type(orig)
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
        raise AssertionError, "did not raise exception %s" % exception
    except exception:
        pass # proper exception raised
    except Exception, e:
        error_msg = 'expected %s to be raised but instead got %s:"%s"' % (exception, type(e), e)
        raise AssertionError, error_msg

class PageRequestTestCase(unittest.TestCase):
    ''' set of tests about requests in Page resource '''
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

        Page(self.token, id=123).get() calls 
        springnote_request(method="GET", url=".*/pages/123[.].*", ...) """
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
        Page(self.token, title='title', source='source').save() calls 
        springnote_request(method="POST", body={title:..,source:..}, ..) """
        title  = 'some title'
        source = 'blah blah ahaha'

        # TODO: check access token
        # TODO: replace with pmock.or
        # TODO: make regex more verbose
        # method: "POST"
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
        Page(self.token, id=123, source='edited').save() calls 
        springnote_request(method="PUT", url="../123.", body={source:..}, ..) """
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
        Page(self.token, id=123).delete() calls 
        springnote_request(method="DELETE", url="../123.", ..) """
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

    @unittest.test
    def force_format_path_and_parameters(self):
        ''' _set_path_params() updates note or id if additionaly given 

        you can force override Page instance attributes '''

        Page = springnote.Page
        Page.format = Page._set_path_params
        t = self.token

        # cancel note
        note = 'jangxyz'
        path, params = Page(t, note=note, id=None).format(note=None)
        assert_that(params, is_not(has_key('domain')))
        assert_that(params, is_not(has_value(note)))

        # cancel id
        id = 123
        path, params = Page(t, id=id).format(id=None)
        assert_that(path, is_not(string_contains(`id`)))

    @unittest.test
    def format_path_and_parameters_accepts_various_options(self):
        """ _set_path_params() accepts various options as parameters

        each of the following options are revealed in path and params:

            sort: identifier | title | relation_is_par_of | date_modified | date_created 
            order: desc | asc
            offset, count
            q: query
            tags: filter by tags
            identifiers: 1,2
        """
        page = springnote.Page(self.token)

        # sort & order
        path, params = page._set_path_params(sort='date_created', order='desc')
        assert_that(path, string_contains('sort=date_created'))
        assert_that(path, string_contains('order=desc'))
        assert_that(params, has_entry('sort',  'date_created'))
        assert_that(params, has_entry('order', 'desc'))

        # search for query
        path, params = page._set_path_params(q='unicode')
        assert_that(path, string_contains('q=unicode'))
        assert_that(params, has_entry('q', 'unicode'))

        # search for escaped query
        path, params = page._set_path_params(q='unicode encoding')
        assert_that(path, string_contains('q=unicode%20encoding'))
        assert_that(params, has_entry('q', 'unicode encoding'))

        # filter by tags
        path, params = page._set_path_params(tags='python')
        assert_that(path, string_contains('tags=python'))
        assert_that(params, has_entry('tags', 'python'))

        # multiple identifiers
        path, params = page._set_path_params(identifiers="100,333")
        assert_that(path, string_contains('identifiers=100,333'))
        assert_that(params, has_entry('identifiers', '100,333'))


    @unittest.test
    def format_path_and_parameters_raises_exception_on_invalid_option(self):
        """ _set_path_params() raises InvalidOption if value is wrong 

        each of the following options are revealed in path and params:

            sort: not one of [identifier, title, relation_is_par_of, date_modified, date_created] 
            order: not either [desc, asc]
            offset, count: not int
            identifiers: is not form of /1,2/"""
        page = springnote.Page(self.token)

        # non-existing value raises InvalidOption
        should_raise(springnote.SpringnoteError.InvalidOption, \
            lambda: page._set_path_params(sort='iq', order='random'))

        # wrong typed value raises InvaidOption
        should_raise(springnote.SpringnoteError.InvalidOption, \
            lambda: page._set_path_params(offset='a string value', count='much as i want'))

        # wrong format of string raises InvalidOption
        should_raise(springnote.SpringnoteError.InvalidOption, \
            lambda: page._set_path_params(identifiers="every"))


    @unittest.test
    def list_method_calls_get_all_pages_request(self):
        """ Page.list() calls get all pages request 
        Page.list(self.token) calls 
        springnote_request(method="GET", url="../pages.json..", ..) """
        # method: "GET"
        # url:    "../pages.json.."
        url_pattern = re.compile("/pages[.]json")
        self.expects_springnote_request.with_at_least(
            method = eq("GET"), 
            url    = string_contains(url_pattern)
        )
        springnote.Page.list(self.token)
        
    @unittest.test
    def list_method_calls_set_path_params_static(self):
        ''' Page.list() calls _set_path_params_static() '''
        should_call_method(springnote.Page, '_set_path_params_static', 
            lambda: springnote.Page.list(self.token, note='jangxyz'), staticmethod
        )

    @unittest.test
    def list_method_with_note_puts_proper_path(self):
        ''' Page.list() with note calls proper path '''
        # method: "GET"
        # url:    "../pages.json.."
        note = 'jangxyz'
        url_pattern = re.compile("/pages[.]json.*domain=%s" % note)
        self.expects_springnote_request.with_at_least(
            method = eq("GET"), 
            url    = string_contains(url_pattern)
        )
        springnote.Page.list(self.token, note=note)

    @unittest.test
    def search_method_calls_get_all_pages_request(self):
        """ Page.search() accepts query explicitly, rest is same with list()

        Page.search(token, query='name') calls 
        springnote_request(method="GET", url="../pages.json..", ..) """
        query = "keyword"

        # url: "../pages.json..q=keyword"
        # params: 
        url_pattern = re.compile("/pages[.].*q=%s" % query)
        self.expects_springnote_request.with_at_least(
            method = eq("GET"), 
            url    = string_contains(url_pattern),
            params = dict_including({'q': query})
        )
        springnote.Page.search(self.token, query=query)


class BuildModelFromResponseTestCase(unittest.TestCase):
    # from http://dev.springnote.com/pages/413747
    sample_json = '''{"page": {
        "rights": null,
        "source": "\u003Cp\u003ENone\u003C/p\u003E\n",
        "creator": "http://deepblue.myid.net/",
        "date_created": "2007/10/26 05:30:08 +0000",
        "contributor_modified": "http://deepblue.myid.net/",
        "date_modified": "2008/01/08 10:55:36 +0000",
        "relation_is_part_of": 1,
        "identifier": 4,
        "tags": "test",
        "title": "TestPage"
    }}'''
    sample_data =  {"page": {
        "rights": None,
        "source": "\u003Cp\u003ENone\u003C/p\u003E\n",
        "creator": "http://deepblue.myid.net/",
        "date_created": "2007/10/26 05:30:08 +0000",
        "contributor_modified": "http://deepblue.myid.net/",
        "date_modified": "2008/01/08 10:55:36 +0000",
        "relation_is_part_of": 1,
        "identifier": 4,
        "tags": "test",
        "title": "TestPage"
    }}
    def setUp(self):
        self.o_Springnote = springnote.Springnote
        self.o_json       = springnote.json

        # mock objects
        springnote.Springnote = CMock()
        springnote.json       = Mock()
        self.m_get_response   = Mock()

        # default Springnote.springnote_request behavior
        springnote.Springnote.expects(at_least_once()).method('springnote_request') \
            .will(return_value(self.m_get_response))

        # default json.loads behavior
        springnote.json.expects(at_least_once()).method('loads') \
            .will(return_value(self.sample_data))

        # default response behavior
        self.m_get_response.status = 200
        self.m_get_response.expects(at_least_once()).read() \
            .will(return_value(self.sample_json))

        self.token = ('BOGUS', 'TOKEN')

        # short conventions
        #self.expects_springnote_request = \
        #    springnote.Springnote.expects(once()).method('springnote_request') \
        #    .will(return_value(self.m_get_response))
        #self.response_expects = self.m_get_response.expects(once())

                            
    def tearDown(self):     
        # restore original
        springnote.Springnote = self.o_Springnote
        springnote.json       = self.o_json
                            
                            
    @unittest.test          
    def should_load_json_after_request(self):
        ''' calls json.load() after request() '''
        # mock
        springnote.json.expects(once()).method('loads') \
            .will(return_value(self.sample_data))       \
            .after("springnote_request", springnote.Springnote)

        # run
        springnote.Page(self.token).request("/some/path")


    @unittest.test
    def resource_attribute_should_be_same_with_json_data(self):
        ''' json data is loaded in page.resource 
        
         * json data: {'page': {'title':'something'}} 
         * .resource:          {'title':'something'}  '''
        page = springnote.Page(self.token)
        page.request("/some/path")

        assert_that(page.resource, is_(self.sample_data['page']))

    @unittest.test
    def json_data_attributes_are_saved_as_instance_attributes(self):
        ''' json data's key is stored as instance attributes '''
        page = springnote.Page(self.token)
        page.request("/some/path")

        for attr_name in self.sample_data['page']:
            assert_that(page, responds_to(attr_name))


    @unittest.test
    def json_data_in_converted_to_unicode(self):
        ''' json data converts to unicode string 

        converts stuffs like "\\u003C" to u"<", 
        as well as preserving "p" as u"p"
        '''
        # "\u003Cp\u003ENone\u003C/p\u003E\n"
        source   = self.sample_data["page"]["source"] 
        resolved = u"<p>None</p>\n"

        to_unicode = springnote.Page._to_unicode
        assert_that(to_unicode(source), is_(resolved))

    @unittest.test
    def json_data_values_are_saved_as_instance_attributes(self):
        ''' json data's value is stored in instance attributes,
        except for 'tags' '''
        page = springnote.Page(self.token)
        page.request("/some/path")

        to_unicode = springnote.Page._to_unicode
        for attr_name, attr_value in self.sample_data['page'].iteritems():
            if attr_name == 'tags': continue
            if isinstance(attr_value, types.StringTypes):
                instance_value = getattr(page, attr_name)
                assert_that(instance_value, is_(to_unicode(attr_value)))

    @unittest.test
    def changes_multiple_json_data(self):
        ''' json list is changed to multiple page instances '''
        list_sample_json = '[%s, %s]' % (self.sample_json, self.sample_json)
        list_sample_data = [self.sample_data, self.sample_data]
        # mock
        springnote.json.expects(at_least_once()).method('loads') \
            .will(return_value(list_sample_data))
        self.m_get_response.expects(at_least_once()).read() \
            .will(return_value(list_sample_json))

        # run
        pages = springnote.Page.list(self.token)
        assert_that(pages, has_length(2))
        assert_that(pages[0], (instance_of(springnote.Page)))

    @unittest.test
    def other_page_methods_calls_request(self):
        ''' get, save, delete calls method request '''
        page = springnote.Page(self.token, id=123)

        should_call_method(page, 'request', lambda: page.get())
        should_call_method(page, 'request', lambda: page.save())
        should_call_method(page, 'request', lambda: page.delete())


if __name__ == '__main__':
    unittest.main()

