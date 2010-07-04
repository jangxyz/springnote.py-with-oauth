#!/usr/bin/python
'''
    Test CRUD calls for Attachment Resource
'''
import test_env
from test_env import *

import unittest, __builtin__

from pmock import *
from pmock_xtnd import *
from hamcrest import *;
from hamcrest_xtnd import *

import springnote

sample_json = '{"attachment": {' \
    '"date_created": "2007/10/26 05:30:07 +0000",' \
    '"relation_is_part_of": 4,' \
    '"identifier": 1,' \
    '"description": 456,' \
    '"title": "Attachment.jpg"' \
'}}'

class AttachmentResponseMockedTestCase(unittest.TestCase):
    ''' mock Springnote instance and http response 
        has: self.auth '''
    def setUp(self):
        # mock http response
        http_response = Mock()
        http_response.status = 200
        http_response.expects(at_least_once()).read() \
            .will(return_value(sample_json))

        # mock Springnote instance
        self.auth = Mock()
        self.auth.access_token   = ('ACCESS', 'TOKEN')
        self.auth.consumer_token = ('CONSUMER', 'TOKEN')
        self.auth.expects(at_least_once()).method('springnote_request') \
            .will(return_value(http_response))

class AttachmentDownloadResponseMockedTestCase(unittest.TestCase):
    def setUp(self):
        # mock http response
        file_content = 'FILE CONTENT'
        http_response = Mock()
        http_response.status = 200
        http_response.expects(once()).read().will(return_value(file_content))

        # mock Springnote instance
        self.auth = Mock()
        self.auth.access_token, self.auth.consumer_token = ('AT', 'CT')
        self.expects_springnote_request = \
            self.auth.expects(once()).method('springnote_request') \
                .will(return_value(http_response))


class AttachmentResourceTestCase(unittest.TestCase):
    def setUp(self):    
        springnote.Springnote = mock_class_Springnote()

        # mock http response
        http_response = Mock()
        http_response.status = 200
        http_response.expects(once()).read().will(return_value(sample_json))

        # mock Springnote instance
        self.auth = Mock()
        self.auth.access_token, self.auth.consumer_token = ('AT', 'CT')
        self.expects_springnote_request = \
            self.auth.expects(once()).method('springnote_request') \
                .will(return_value(http_response))

        # file object mock
        file_content = 'FILE CONTENT'
        self.filename = 'testfile.txt'
        self.wrapped_body = '--AaB03x\r\n' \
            'Content-Disposition: form-data; name="Filedata"; filename="README"\r\n' \
            'Content-Transfer-Encoding: binary\r\n' \
            'Content-Type: application/octet-stream\r\n' \
            '\r\n' \
            '%s' \
            '--AaB03x--' % file_content
        self.file_obj = Mock()
        self.file_obj.name = self.filename
        self.file_obj.expects(at_least_once()).method('seek')
        self.file_obj.expects(at_least_once()).read() \
            .will(return_value(file_content))

        self.page   = springnote.Page(self.auth, id=1)
        self.attach = springnote.Attachment(self.page, id=123)

    def tearDown(self): 
        springnote.Springnote = restore_class_Springnote()

    @unittest.test
    def has_basic_attributes(self):
        ''' has [date_created, relation_is_part_of, description, title, identifier] as attributes '''
        attch = springnote.Attachment(self.page)
        attrs  = "date_created relation_is_part_of description title identifier".split(' ')
        attrs += ['id']
        for attr in attrs:
            assert_that(attch, responds_to(attr))

    @unittest.test
    def class_method_list_calls_proper_path(self):
        ''' list() calls GET ".../pages/123/attachments.json" '''
        # mock
        url_pattern = re.compile("/pages/%d/attachments[.]" % self.page.id)
        self.expects_springnote_request.with_at_least(
            method = eq("GET"), 
            url    = string_contains(url_pattern)
        )
        # run
        springnote.Attachment.list(self.page)

    @unittest.test
    def class_method_list_with_note_calls_proper_path_and_params(self):
        ''' list(123, 'jangxyz') calls GET ".../pages/123/attachments..domain=jangxyz" '''
        self.page.note = 'jangxyz'
        # mock
        url_pattern = "/pages/%d/attachments[.].*domain=%s" % (self.page.id, self.page.note)
        url_pattern = re.compile(url_pattern)
        self.expects_springnote_request.with_at_least(
            method = eq("GET"), 
            url    = string_contains(url_pattern)
        )
        # run
        springnote.Attachment.list(self.page)

    @unittest.test
    def get_calls_proper_path_and_params(self):
        ''' get() calls GET ".../pages/1/attachments/123 with .json '''
        self.page.note = 'jangxyz'
        # mock
        # url: "/pages/1/attachments/123.json?domain=jangxyz"
        url_pattern = "/pages/%d/attachments/%d[.].*\?domain=%s" % (self.page.id, self.attach.id, self.page.note)
        url_pattern = re.compile(url_pattern)
        self.expects_springnote_request.with_at_least(
            method=eq("GET"), url=string_contains(url_pattern))
        # run
        self.attach.get()

    @unittest.test
    def get_reloads_metadata_but_not_the_content(self):
        ''' get() reloads metadata but not the content '''
        self.attach.get()
        assert_that(self.attach.file, is_(None))
        assert_that(self.attach.title, is_not(None))

    @unittest.test
    def delete_calls_proper_path_and_params(self):
        ''' delete() calls GET ".../pages/1/attachments/123.json '''
        # mock
        url_pattern = re.compile(
            "/pages/%d/attachments/%d[.]" % (self.page.id, self.attach.id))
        self.expects_springnote_request.with_at_least(
            method=eq("DELETE"), url=string_contains(url_pattern))
        # run
        self.attach.delete()

    @unittest.test
    def download_and_delete_methods_should_have_both_page_id_and_id(self):
        ''' delete() raises InvalidOption if any of page id and id is not given '''
        # test page without id
        idless_page = springnote.Page(self.auth, None) 
        pageid_less_attach = springnote.Attachment(idless_page, id=123)
        should_raise(springnote.SpringnoteError.InvalidOption, 
                    when=lambda: pageid_less_attach.delete())

        # test attachment without id
        id_less_attach = springnote.Attachment(self.page, id=None)
        should_raise(springnote.SpringnoteError.InvalidOption, 
                    when=lambda: id_less_attach.delete())

    @unittest.test
    def upload_old_file_calls_proper_path_params_and_dumped_data(self):
        ''' upload() existing file calls proper path, param and file object '''
        self.attach.file = self.file_obj
        # mock
        url_pattern = "/pages/%d/attachments/%d[.]" % (self.page.id, self.attach.id)
        url_pattern = re.compile(url_pattern)
        springnote.Springnote.expects(once()).method('wrap_file_to_body') \
            .will(return_value(self.wrapped_body))
        self.expects_springnote_request.with_at_least(
            method=eq("PUT"), url=string_contains(url_pattern),
            body=string_contains(self.file_obj.read())
        ) .after('wrap_file_to_body', springnote.Springnote)
        # run
        self.attach.upload()

    @unittest.test
    def upload_new_file_calls_proper_path_and_params_and_dumped_data(self):
        ''' upload() new file calls proper path, param and file object '''
        self.attach.id   = None
        self.attach.file = self.file_obj
        # mock
        url_pattern = re.compile("/pages/%d/attachments[.]" % self.page.id)
        springnote.Springnote.expects(once()).method('wrap_file_to_body') \
            .will(return_value(self.wrapped_body))
        self.expects_springnote_request.with_at_least(
            method=eq("POST"), url=string_contains(url_pattern),
            body=string_contains(self.file_obj.read()))
        # run
        self.attach.upload()

    def upload_dumps_data_and_proper_header(self):
        ''' upload() dumps data and has content-type: multipart in header '''
        self.attach.id   = None
        self.attach.file = self.file_obj
        # mock
        url_pattern = re.compile("/pages/%d/attachments[.]" % self.page.id)
        self.expects_springnote_request.with_at_least(
            method=eq("POST"), url=string_contains(url_pattern),
            body=eq(self.file_obj))
        # run
        self.attach.upload()

    @unittest.test
    def upload_should_have_both_page_id_and_file(self):
        ''' upload() raises InvalidOption if either page id or file object is not given '''
        run = lambda: attach.upload()
        # page without an id
        page   = springnote.Page(self.auth, None)
        attach = springnote.Attachment(page, file=self.file_obj)
        should_raise(springnote.SpringnoteError.InvalidOption, when=run)

        # no file
        attach = springnote.Attachment(self.page, file=None)
        should_raise(springnote.SpringnoteError.InvalidOption, when=run)

    @unittest.test
    def id_should_be_same_as_identifier(self):
        id = 123
        attach = springnote.Attachment(self.page)
        attach.id = id
        assert_that(attach.identifier, is_(id))

        attach = springnote.Attachment(self.page)
        attach.identifier = id
        assert_that(attach.id, is_(id))


class AttachmentDownloadTestCase(AttachmentDownloadResponseMockedTestCase):
    def setUp(self):    
        super(AttachmentDownloadTestCase, self).setUp()
        self.page   = springnote.Page(self.auth, id=1)
        self.attach = springnote.Attachment(self.page, id=123)

    @unittest.test
    def download_calls_proper_path_and_params(self):
        ''' download() calls GET ".../pages/1/attachments/123 without .json '''
        # mock
        url_pattern = re.compile(
            "/pages/%d/attachments/%d$" % (self.page.id, self.attach.id))
        self.expects_springnote_request.with_at_least(
            method=eq("GET"), url=string_contains(url_pattern))
        # run
        self.attach.download()

    @unittest.test
    def download_saves_file_content_but_no_title(self):
        ''' download() saves response to content, but not metadata '''
        attach = springnote.Attachment(self.page, id=123)
        attach.download()
        assert_that(attach.title,   is_(None))
        assert_that(attach.content, is_not(None))

    @unittest.test
    def download_and_delete_methods_should_have_both_page_id_and_id(self):
        ''' download() raises InvalidOption if any of page id and id is not given '''
        run = lambda: pageid_less_attach.download()
        # test page without id
        idless_page = springnote.Page(self.auth, None) 
        pageid_less_attach = springnote.Attachment(idless_page, id=123)
        should_raise(springnote.SpringnoteError.InvalidOption, when=run)

        # test attachment without id
        id_less_attach = springnote.Attachment(self.page, id=None)
        should_raise(springnote.SpringnoteError.InvalidOption, when=run)

class AttributeConvertTestCase(AttachmentResponseMockedTestCase):
    def setUp(self):
        super(AttributeConvertTestCase, self).setUp()

        self.page = springnote.Page(self.auth, id=123)
        self.date_created = "2007/10/26 05:30:07 +0000"

    @unittest.test
    def converts_date_created_into_datetime_format(self):
        ''' date_created converts to datetime format '''
        # run 
        attach = springnote.Attachment.from_json(sample_json, self.auth, self.page)
        assert_that(attach.date_created, instance_of(springnote.datetime))

    @unittest.test
    def converts_datetime_format_with_localtimezone(self):
        ''' date_created converts to datetime in localtime '''
        # run 
        date_created = "2007/10/26 05:30:07 +0000"
        dt  = springnote.datetime(2007,10,26,5,30,7)
        dt -= springnote.timedelta(seconds=springnote.time.timezone) # localize
        attach = springnote.Attachment.from_json(sample_json, self.auth, self.page)
        # verify 
        assert_that(attach.date_created.timetuple(), is_(dt.timetuple()))

    @unittest.test
    def unconverted_datetime_is_in_resource(self):
        ''' string format date_created is in resource '''
        date_created = "2007/10/26 05:30:07 +0000"
        # run & verify
        attach = springnote.Attachment.from_json(sample_json, self.auth, self.page)
        assert_that(attach.resource['date_created'], is_(date_created))


if __name__ == '__main__':
    unittest.main()

