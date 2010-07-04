#!/usr/bin/python
'''
    Test basic crud calls for Page Resource
'''
import test_env
from test_env import *

import unittest, re, __builtin__
from pmock import *
from pmock_xtnd import *

from hamcrest import *;
from hamcrest_xtnd import *

import springnote

# from http://dev.springnote.com/pages/413747, escaped to match python
sample_json = '{"page": {' \
    '"rights": null, ' \
    '"source": "\\u003Cp\\u003ENone\\u003C/p\\u003E\\n", ' \
    '"creator": "http://deepblue.myid.net/", ' \
    '"date_created": "2007/10/26 05:30:08 +0000", ' \
    '"contributor_modified": "http://deepblue.myid.net/", ' \
    '"date_modified": "2008/01/08 10:55:36 +0000", ' \
    '"relation_is_part_of": 1, ' \
    '"identifier": 4, ' \
    '"tags": "test", ' \
    '"title": "TestPage", ' \
    '"uri": "http://deepblue.springnote.com/pages/4" '  \
'}}'
sample_json_list = "[%s, %s]" % (sample_json, sample_json)
sample_data =  {u"page": {
    u"rights": None,
    u"source": u"\u003Cp\u003ENone\u003C/p\u003E\n",
    u"creator": u"http://deepblue.myid.net/",
    u"date_created": u"2007/10/26 05:30:08 +0000",
    u"contributor_modified": u"http://deepblue.myid.net/",
    u"date_modified": u"2008/01/08 10:55:36 +0000",
    u"relation_is_part_of": 1,
    u"identifier": 4,
    u"tags": u"test",
    u"title": u"TestPage",
    u"uri": u"http://deepblue.springnote.com/pages/4",
}}

class PageResponseMockedTestCase(unittest.TestCase):
    ''' mock Springnote instance and http response 

        has: 
            self.auth
            self.m_get_response '''
    def setUp(self):
        # mock http response
        self.m_get_response = Mock() # http response mock
        self.m_get_response.status = 200
        self.m_get_response.expects(at_least_once()).read() \
            .will(return_value(sample_json))

        # mock instance of springnote.Springnote
        self.auth = Mock()
        self.auth.access_token   = ('ACCESS', 'TOKEN')
        self.auth.consumer_token = ('CONSUMER', 'TOKEN')
        self.auth.expects(once()).method('springnote_request') \
            .will(return_value(self.m_get_response))

class PageResponseJsonMockedTestCase(PageResponseMockedTestCase):
    ''' mock Springnote instance, http response and json 

        has: 
            self.auth
            self.m_get_response '''
    def setUp(self):
        super(PageResponseJsonMockedTestCase, self).setUp()

        # mock json
        self.o_json = springnote.json
        springnote.json = Mock() 
        springnote.json.expects(at_least_once()).method('loads') \
            .will(return_value(sample_data))
    
    def tearDown(self):
        springnote.json = self.o_json


class PageRequestTestCase(PageResponseMockedTestCase):
    ''' set of tests about requests in Page resource '''
    def setUp(self):
        super(PageRequestTestCase, self).setUp()

        self.expects_springnote_request = \
            self.auth.expects(once()).method('springnote_request') \
            .will(return_value(self.m_get_response))

    @unittest.test
    def get_method_with_id_calls_get_page_request(self):
        """ page.get() with id calls get page request

        Page(self.auth, id=123).get() calls 
        springnote_request(method="GET", url=".*/pages/123[.].*", ...) """
        id = 123

        # mock
        url_pattern = "/pages/%d." % id
        self.expects_springnote_request.with_at_least(
            method = eq("GET"), 
            url    = string_contains(url_pattern)
        )
        # run
        springnote.Page(self.auth, id=id).get()

    @unittest.test
    def get_method_without_id_is_invalid(self):
        """ page.get() without id is invalid 
        Page(self.auth).get() raises InvalidOption error """
        should_raise(springnote.SpringnoteError.InvalidOption, \
            lambda: springnote.Page(self.auth).get())

    @unittest.test
    def get_method_calls_set_path_params(self):
        ''' page.get() calls _set_path_params() '''
        note, id = 'jangxyz', 123
        should_call_method(springnote.Page, '_set_path_params', 
            lambda: springnote.Page(self.auth, note=note, id=id).get()
        )

    @unittest.test
    def save_method_without_id_calls_create_page_request(self):
        """ page.save() without id calls create page request

        Page(auth, title='title', source='source').save()  calls 
        springnote_request(method="POST", body={title:.., source:..}, ..) """
        title  = 'some title'
        source = 'blah blah ahaha'

        # TODO: check access token
        # TODO: make regex more verbose
        # method: "POST"
        # source: '{"page": {"source": "blah blah ahaha", "title": "some title"}}'
        pattern1 = '"title"\s*:\s*"%s"\s*,\s*"source"\s*:\s*"%s"' % (title, source)
        pattern2 = '"source"\s*:\s*"%s",\s*"title"\s*:\s*"%s"\s*' % (source, title)
        body_pattern = re.compile("(%s|%s)" % (pattern1, pattern2))
        self.expects_springnote_request \
            .with_at_least(method=eq("POST"), body=string_contains(body_pattern))

        # run
        springnote.Page(self.auth, title=title, source=source).save()


    @unittest.test
    def save_method_with_id_calls_update_page_request(self):
        """ page.save() with id calls update page request
        Page(self.auth, id=123, source='edited').save() calls 
        springnote_request(method="PUT", url="../123.", body={source:..}, ..) """
        id     = 123
        source = 'edited'

        # method: "PUT"
        # url:    "/pages/123.json"
        # source: "source": "edited"
        url_pattern  = re.compile('''/pages/%d[.]''' % id) 
        body_pattern = re.compile('''["']source["']\s*:\s*["']%s["']''' % source)
        self.expects_springnote_request .with_at_least(
            method = eq("PUT"), 
            url    = string_contains(url_pattern),
            body   = string_contains(body_pattern)
        )

        # run
        springnote.Page(self.auth, id=id, source=source).save()


    @unittest.test
    def save_method_calls_set_path_params(self):
        ''' page.save() calls _set_path_params() '''
        note, id = 'jangxyz', 123
        should_call_method(springnote.Page, '_set_path_params', 
            lambda: springnote.Page(self.auth, note=note, id=id).save()
        )

    @unittest.test
    def save_method_only_puts_attributes_in_writable_attributes(self):
        ''' page.save() only packs attributes in writable_attribute '''
        page = springnote.Page(self.auth, id=3, title='title', source='source')
        # these shouldn't be in body
        page.rights               = "rights"
        page.date_created         = springnote.datetime.now()
        page.date_modified        = springnote.datetime.now()
        page.creator              = "creator"
        page.contributor_modified = "contributor_modified"
        
        should_call_method(self.auth, 'springnote_request',
            when=lambda: page.save(),
            arg=with_at_least(body=is_not(
                any_of(
                    contains_string("rights"),
                    contains_string("date_created"),
                    contains_string("date_modified"),
                    contains_string("creator"),
                    contains_string("contributor_modified"),
                )))
        )


    @unittest.test
    def delete_method_with_id_calls_delete_page_request(self):
        """ page.delete() with id calls delete page request
        Page(self.auth, id=123).delete() calls 
        springnote_request(method="DELETE", url="../123.json", ..) """
        id = 123

        # method: "DELETE"
        # url:    "/pages/123.json"
        url_pattern  = re.compile('''/pages/%d[.]''' % id) 
        self.expects_springnote_request .with_at_least(
            method = eq("DELETE"), 
            url    = string_contains(url_pattern),
        )

        # run
        springnote.Page(self.auth, id=id).delete()

    @unittest.test
    def delete_method_calls__set_path_params(self):
        ''' page.delete() calls _set_path_params() '''
        note, id = 'jangxyz', 123
        should_call_method(springnote.Page, '_set_path_params', 
            lambda: springnote.Page(self.auth, note=note, id=id).delete()
        )


    @unittest.test
    def delete_method_without_id_is_invalid(self):
        """ page.delete() without id is invalid

        Page(self.auth).delete() raises InvalidOption error """
        should_raise(springnote.SpringnoteError.InvalidOption, 
                        when=lambda: springnote.Page(self.auth).delete())


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
        t = self.auth

        # no note
        assert_that(Page._set_path_params(note=None, id=None),
                        is_(('/pages.json',      {})))
        assert_that(Page._set_path_params(note=None, id=1234),
                        is_(('/pages/1234.json', {})))

        # with note
        assert_that(Page._set_path_params(note='ab', id=None),
                        is_(('/pages.json?domain=ab',      {'domain':'ab'})))
        assert_that(Page._set_path_params(note='ab', id=1234),
                        is_(('/pages/1234.json?domain=ab', {'domain':'ab'})))

    @unittest.test
    def force_format_path_and_parameters(self):
        ''' _set_path_params() updates note or id if additionaly given 

        you can force override Page instance attributes '''

        Page = springnote.Page
        t = self.auth

        # cancel note
        note = 'jangxyz'
        path, params = Page._set_path_params(note=None, id=None)
        assert_that(params, is_not(has_key('domain')))
        assert_that(params, is_not(has_value(note)))

        # cancel id
        id = 123
        path, params = Page(t, id=id)._set_path_params(id=None)
        assert_that(path, is_not(string_contains(`id`)))

    @unittest.test
    def format_path_and_parameters_accepts_various_options(self):
        """ _set_path_params() accepts various options as parameters

        each of the following options are revealed in path and params:

            sort: identifier | title | relation_is_par_of | date_modified | date_created 
            order: desc | asc
            offset, count
            parent_id: 123
            q: query
            tags: filter by tags
            identifiers: 1,2
        """
        page = springnote.Page(self.auth)

        # sort & order
        path, params = page._set_path_params(sort='date_created', order='desc')
        assert_that(path, contains_string('sort=date_created'))
        assert_that(path, contains_string('order=desc'))
        assert_that(params, has_entry('sort',  'date_created'))
        assert_that(params, has_entry('order', 'desc'))

        # search for query
        path, params = page._set_path_params(q='unicode')
        assert_that(path, contains_string('q=unicode'))
        assert_that(params, has_entry('q', 'unicode'))

        # search for escaped query
        path, params = page._set_path_params(q='unicode encoding')
        assert_that(path, contains_string('q=unicode+encoding'))
        assert_that(params, has_entry('q', 'unicode encoding'))

        # parent_id
        path, params = page._set_path_params(parent_id=123)
        assert_that(path, contains_string('parent_id=123'))
        assert_that(params, has_entry('parent_id', 123))

        # filter by tags
        path, params = page._set_path_params(tags='python')
        assert_that(path, contains_string('tags=python'))
        assert_that(params, has_entry('tags', 'python'))

        # multiple identifiers
        path, params = page._set_path_params(identifiers="100,333")
        assert_that(path, contains_string('identifiers=100%2C333'))
        assert_that(params, has_entry('identifiers', '100,333'))


    @unittest.test
    def format_path_and_parameters_raises_exception_on_invalid_option(self):
        """ _set_path_params() raises InvalidOption if value is wrong 

        each of the following options are revealed in path and params:

            sort: one of [identifier, title, relation_is_par_of, date_modified, date_created] 
            order: either [desc, asc]
            offset, count, parent_id: int
            identifiers: is form of /1,2/"""
        page = springnote.Page(self.auth)

        # non-existing value raises InvalidOption
        should_raise(springnote.SpringnoteError.InvalidOption, \
            lambda: page._set_path_params(sort='iq', order='random'))

        # wrong typed value raises InvaidOption
        should_raise(springnote.SpringnoteError.InvalidOption, \
            lambda: page._set_path_params(offset='a string value', count='much as i want'))

        # wrong typed value raises InvaidOption
        should_raise(springnote.SpringnoteError.InvalidOption, \
            lambda: page._set_path_params(parent_id='something'))

        # wrong format of string raises InvalidOption
        should_raise(springnote.SpringnoteError.InvalidOption, \
            lambda: page._set_path_params(identifiers="every"))

    @unittest.test
    def list_method_calls_get_all_pages_request(self):
        """ Page.list() calls get all pages request 
        Page.list(self.auth) calls 
        springnote_request(method="GET", url="../pages.json..", ..) """
        # method: "GET"
        # url:    "../pages.json.."
        url_pattern = re.compile("/pages[.]json")
        should_call_method(self.auth, 'springnote_request', 
            when = lambda: springnote.Page.list(self.auth), 
            arg  = with_at_least(method=eq("GET"), url=string_contains(url_pattern)),
        )

    @unittest.test
    def list_method_calls_set_path_params(self):
        ''' Page.list() calls _set_path_params() '''
        should_call_method(springnote.Page, '_set_path_params', 
            lambda: springnote.Page.list(self.auth, note='jangxyz'), classmethod
        )

    @unittest.test
    def list_method_with_note_puts_proper_path(self):
        ''' Page.list() with note calls proper path '''
        # method: "GET"
        # url:    "../pages.json..?..domain=jangxyz"
        note = 'jangxyz'
        url_pattern = re.compile("/pages[.]json.*domain=%s" % note)
        should_call_method(self.auth, 'springnote_request', 
            when = lambda: springnote.Page.list(self.auth, note=note), 
            arg  = with_at_least(method=eq("GET"), url=string_contains(url_pattern)),
        )

class ConventionalMethodsTestCase(unittest.TestCase):
    def setUp(self):
        self.auth = springnote.Springnote()

    @unittest.test
    def search_method_calls_list_with_q(self):
        """ Page.search(keyword) is Page.list(query=keyword) """
        query = "keyword"
        run   = lambda: springnote.Page.search(self.auth, query = query)
        should_call_method(springnote.Page, 'list', 
            when=run, method_type=classmethod,
            arg = with_at_least(q=eq(query)),
        )


    @unittest.test
    def get_root_method_calls_list_and_filter_afterward(self):
        """ page.get_root() calls Page.list and filter with relation_is_part_of """
        run = lambda: springnote.Page(self.auth).get_root()
        should_call_method(springnote.Page, 'list', 
            when=run, method_type=classmethod,
        )
        # XXX: not really checking the AFTER part
        should_call_method(__builtin__, 'filter', when=run)
    
    @unittest.test
    def get_parent_method_calls_get_with_id(self): 
        ''' page.get_parent() calls Page(id=page.relation_is_part_of).get() '''
        parent_id = 123
        page = springnote.Page(self.auth, id=456)
        page.relation_is_part_of = parent_id

        run = lambda: page.get_parent()
        # calls springnote.Page(auth, id=parent_id)
        should_call_class(springnote, 'Page', when=run,
            arg = with_(eq(self.auth), id=eq(parent_id))
        )
        should_call_method(springnote.Page, 'get', when=run)

    @unittest.test
    def get_parent_method_returns_none_if_no_relation_is_part_of(self): 
        ''' page.get_parent() without relation_is_part_of returns None '''
        page = springnote.Page(self.auth, id=456)
        assert_that(page.get_parent(), is_(None))
        
    @unittest.test
    def get_children_method_calls_list_with_parent_id(self): 
        ''' page.get_children() calls Page.list(parent_id=page.id) '''
        page    = springnote.Page(self.auth, id = 123)
        verbose = True
        run = lambda: page.get_children(verbose=verbose)
        should_call_method(springnote.Page, 'list', when=run, method_type=classmethod,
            arg=with_at_least(parent_id=eq(page.id), verbose=eq(verbose)))


class JsonTestCase(PageResponseJsonMockedTestCase):
    def convert_string_to_unicode(self, data):
        if isinstance(data, types.StringType):
            return springnote.SpringnoteResource._to_unicode(data)
        elif isinstance(data, types.ListType):
            return map(unicode, data)
        elif isinstance(data, types.DictType):
            u_data = {}
            for key, value in data.iteritems():
                u_key   = self.convert_string_to_unicode(key)
                u_value = self.convert_string_to_unicode(value)
                u_data[u_key] = u_value
            return u_data
        else:
            return data

    @unittest.test
    def should_load_json_after_request(self):
        ''' calls json.loads() after request() '''
        # mock
        springnote.json.expects(once()).method('loads') \
            .will(return_value(sample_data))       \
            .after("springnote_request", self.auth)

        # run
        springnote.Page(self.auth).request("/some/path")

    @unittest.test
    def should_dump_data_to_json_on_request(self):
        ''' calls json.dumps() when request() if data is given '''
        data = sample_data['page']

        # mock
        springnote.json.expects(once()).method('dumps') \
            .will(return_value(sample_json))

        springnote.Page(self.auth).request("/some/path", data=data)


class BuildModelFromResponseTestCase(PageResponseJsonMockedTestCase):
    def mock_module_json(self):
        self.o_json = springnote.json
        springnote.json = Mock()
        return springnote.json

    def restore_module_json(self):
        springnote.json = self.o_json
        return springnote.json

    @unittest.test
    def should_load_json_after_request(self):
        ''' calls json.loads() after request() '''
        # mock
        springnote.json.expects(once()).method('loads') \
            .will(return_value(sample_data))       \
            .after("springnote_request", self.auth)

        # run
        springnote.Page(self.auth).request("/some/path")

    @unittest.test
    def resource_attribute_is_same_with_json_data(self):
        ''' json data is loaded in page.resource 

         * json data: {'page': {'title':'something'}} 
         * .resource:          {'title':'something'}  '''
        page = springnote.Page(self.auth)
        page = page.request("/some/path")

        assert_that(page.resource, is_(sample_data['page']))

    @unittest.test
    def json_data_attributes_are_saved_as_instance_attributes(self):
        ''' json data's key is stored as instance attributes '''
        page = springnote.Page(self.auth)
        page.request("/some/path")

        for attr_name in sample_data['page']:
            assert_that(page, responds_to(attr_name))


    @unittest.test
    def json_data_in_converted_to_unicode(self):
        ''' json data converts to unicode string 

        converts stuffs like "\\u003C" to u"<", 
        as well as preserving "p" as u"p"
        '''
        # "\u003Cp\u003ENone\u003C/p\u003E\n"
        source   = sample_data["page"]["source"] 
        resolved = u"<p>None</p>\n"

        to_unicode = springnote.Page._to_unicode
        assert_that(to_unicode(source), is_(resolved))

    @unittest.test
    def json_data_values_are_saved_as_instance_attributes(self):
        ''' json data's value is stored in instance attributes, 
        except for converted values ('tags', 'date_created', 'date_modified' '''
        page = springnote.Page(self.auth)
        page = page.request("/some/path")

        to_unicode = springnote.Page._to_unicode
        for attr_name, attr_value in sample_data['page'].iteritems():
            if attr_name in ['tags', 'date_created', 'date_modified']: 
                continue
            if isinstance(attr_value, types.StringTypes):
                instance_value = getattr(page, attr_name)
                assert_that(instance_value, is_(to_unicode(attr_value)))

    @unittest.test
    def changes_multiple_json_data(self):
        ''' json list is changed to multiple page instances '''
        list_sample_data = [sample_data, sample_data]

        # mock
        self.restore_module_json() # I'm gonna use json
        self.m_get_response.expects(at_least_once()).read() \
            .will(return_value(sample_json_list))

        # run
        pages = springnote.Page.list(self.auth)
        assert_that(pages, has_length(2))
        assert_that(pages[0], (instance_of(springnote.Page)))
        assert_that(pages[0].raw, is_not(has_length(0)))

    @unittest.test
    def other_page_methods_call_request_method(self):
        ''' get, save, delete calls method request '''
        self.tearDown()
        page = springnote.Page(self.auth, id=123)
        should_call_method(page, 'request', lambda: page.get())
        should_call_method(page, 'request', lambda: page.save())
        should_call_method(page, 'request', lambda: page.delete())

    @unittest.test
    def instance_returned_from_request_must_be_same(self):
        ''' instance returned after a request must be the same with previous '''
        page1 = springnote.Page(self.auth, id=123)
        page2 = page1.get()

        assert_that(id(page1), is_(id(page2)))

    @unittest.test
    def id_should_be_same_as_identifier(self):
        id = 123
        page = springnote.Page(self.auth)
        page.id = id
        assert_that(page.identifier, is_(id))

        page = springnote.Page(self.auth)
        page.identifier = id
        assert_that(page.id, is_(id))

class PageBlackMagicTestCase(unittest.TestCase):
    def setUp(self):
        self.sn   = springnote.Springnote()
        self.page = springnote.Page(self.sn, id=123)

    def tearDown(self):
        pass

    @unittest.test
    def page_get_attachment_calls_attachment_get(self):
        ''' page.get_attachment(id, verbose) calls Attachment(page, id).get(verbose) '''
        id      = 456
        verbose = False

        run = lambda: self.page.get_attachment(id=id, verbose=verbose)
        ## calls springnote.Attachment(page, id=123)
        #should_call_class(springnote, 'Attachment', when=run, 
        #                        arg=with_(eq(self.page), id=eq(id)))
        # calls springnote.Attachment.get(verbose=True)
        should_call_method(springnote.Attachment, 'get', when=run, 
                                arg=with_at_least(verbose=eq(verbose)))

    @unittest.test
    def page_upload_attachment_calls_attachment_upload(self):
        ''' page.upload_attachment(verbose) calls Attachment(page, id).upload(verbose) '''
        id        = 123
        filename  = 'somefile.txt'
        content   = "FILE CONTENT"
        file      = Mock()
        file.name = filename
        file.read = lambda: content
        verbose   = True

        run  = lambda: self.page.upload_attachment(id, filename=filename, file=file, verbose=verbose)
        ## test springnote.Attachment(page, id=123)
        #should_call_class(springnote, 'Attachment', when=run, 
        #                    arg = with_(eq(self.page), eq(id),
        #                                filename=eq(filename), file=eq(file)))
        # test springnote.Attachment().get(verbose=True)
        should_call_method(springnote.Attachment, 'upload', when=run, 
                            arg = with_at_least(verbose=eq(verbose)))

    @unittest.test
    def page_list_attachments_calls_attachment_list(self):
        ''' page.list_attachments() calls Attachment.list(page) '''
        run  = lambda: self.page.list_attachments()
        page = Mock()

        should_call_method(springnote.Attachment, 'list', when=run, 
            arg = with_at_least(eq(springnote.Attachment), eq(self.page)), 
            method_type=classmethod)

class TagConversionTestCase(PageResponseJsonMockedTestCase):
    @unittest.test
    def converts_string_tags_into_list(self):
        ''' "TAG1,TAG2" formatted tags are splitted by comma(,) and saved as list '''
        tag_string = "tag1,tag2,tag3"
        tag_list   = ["tag1", "tag2", "tag3"]

        # mock
        response_data = sample_data.copy()
        response_data[u"page"][u"tags"] = tag_string
        springnote.json.expects(at_least_once()).method('loads') \
            .will(return_value(response_data))

        # run & verify
        page = springnote.Page(self.auth, id=123).get()
        assert_that(page.tags, is_(tag_list))

    @unittest.test
    def tags_list_in_constructor(self):
        tags = ["abc", "def"]
        page = springnote.Page(self.auth, tags=tags)
        assert_that(page.tags, is_(tags))

    @unittest.test
    def tags_string_in_constructor_is_splitted_by_space_and_commas(self):
        ''' passing string tags is saved as list, splitted by both ' ' and ',' '''
        tag_string = "abc def,ghi"
        tag_list   = ["abc", "def", "ghi"]
        page = springnote.Page(self.auth, tags=tag_string)
        assert_that(page.tags, is_(tag_list))

    @unittest.test
    def unconverted_tags_data_is_in_resource(self):
        ''' "TAG1,TAG2" formatted tags are saved as original in resource '''
        tag_string = "tag1,tag2,tag3"
        tag_list   = ["tag1", "tag2", "tag3"]

        # mock
        response_data = sample_data.copy()
        response_data[u"page"][u"tags"] = tag_string
        springnote.json.expects(at_least_once()).method('loads') \
            .will(return_value(response_data))

        # run & verify
        page = springnote.Page(self.auth, id=123).get()
        assert_that(page.resource['tags'], is_(tag_string))

class DateTimeConvesionTestCase(PageResponseJsonMockedTestCase):
    @unittest.test
    def converts_date_created_and_date_modified_into_datetime_format(self):
        ''' date_modified and date_created ("2007/10/26 05:30:08 +0000") converts to datetime format '''
        # "2007/10/26 05:30:08 +0000", "2008/01/08 10:55:36 +0000"
        date_created  = sample_data[u"page"][u"date_created"]
        date_modified = sample_data[u"page"][u"date_modified"]

        # run & verify
        page = springnote.Page(self.auth, id=123).get()
        assert_that(page.date_created,  instance_of(springnote.datetime))
        assert_that(page.date_modified, instance_of(springnote.datetime))

    @unittest.test
    def converts_datetime_format_with_localtimezone(self):
        ''' date_modified and date_created ("2007/10/26 05:30:08 +0000") converts to datetime format '''
        # "2007/10/26 05:30:08 +0000", "2008/01/08 10:55:36 +0000"
        date_created  = sample_data["page"]["date_created"]
        date_modified = sample_data["page"]["date_modified"]

        # run 
        page = springnote.Page(self.auth, id=123).get()

        # verify localtimezone
        dt  = springnote.datetime.strptime(date_created, page.datetime_format)
        dt -= springnote.timedelta(seconds=springnote.time.timezone)
        assert_that(page.date_created.timetuple(), is_(dt.timetuple()))

        dt  = springnote.datetime.strptime(date_modified, page.datetime_format)
        dt -= springnote.timedelta(seconds=springnote.time.timezone)
        assert_that(page.date_modified.timetuple(), is_(dt.timetuple()))

    @unittest.test
    def unconverted_datetime_is_in_resource(self):
        ''' string format date_modified and date_created ("2007/10/26 05:30:08 +0000") is in resource '''
        # "2007/10/26 05:30:08 +0000", "2008/01/08 10:55:36 +0000"
        date_created  = sample_data[u"page"][u"date_created"]
        date_modified = sample_data[u"page"][u"date_modified"]

        # run & verify
        page = springnote.Page(self.auth, id=123).get()
        assert_that(page.resource['date_created'],  is_(date_created))
        assert_that(page.resource['date_modified'], is_(date_modified))


if __name__ == '__main__':
    unittest.main()

