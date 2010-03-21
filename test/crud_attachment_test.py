#!/usr/bin/python
'''
    Test CRUD calls for Attachment Resource
'''
import test_env
from test_env import *

import unittest, types

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

class AttachmentResourceTestCase(unittest.TestCase):
    def setUp(self):    
        springnote.Springnote = mock_class_Springnote()

        # mock
        # http_response mock
        http_response = Mock()
        http_response.status = 200
        http_response.expects(once()).read() \
            .will(return_value(sample_json))
        # springnote request mock
        self.expects_springnote_request = \
            springnote.Springnote.expects(once()).method('springnote_request') \
                .will(return_value(http_response))

        # file object mock
        file_content = 'FILE CONTENT'
        self.filename = 'testfile.txt'
        self.file_obj = Mock()
        self.file_obj.name = self.filename
        self.file_obj.expects(at_least_once()).method('seek')
        self.file_obj.expects(at_least_once()).read() \
            .will(return_value(file_content))

        #
        self.auth = Mock()
        self.auth.access_token, self.auth.consumer_token = ('AT', 'CT')
        self.page   = springnote.Page(self.auth, id=1)
        self.attach = springnote.Attachment(self.auth, self.page, id=123)

    def tearDown(self): 
        springnote.Springnote = restore_class_Springnote()

    @unittest.test
    def has_basic_attributes(self):
        ''' has [date_created, relation_is_part_of, description, title] as attributes 
        except identifier. we use id instead.
        '''
        attch = springnote.Attachment(self.auth, self.page)
        attrs = "date_created relation_is_part_of description title".split(' ')
        attrs += ['id']
        for attr in attrs:
            assert_that(attch, responds_to(attr))

    @unittest.test
    def class_method_list_calls_proper_path(self):
        ''' list() calls GET ".../pages/123/attachments". '''
        # mock
        url_pattern = re.compile("/pages/%d/attachments[.]" % self.page.id)
        self.expects_springnote_request.with_at_least(
            method = eq("GET"), 
            url    = string_contains(url_pattern)
        )
        # run
        springnote.Attachment.list(self.auth, self.page.id)

    @unittest.test
    def class_method_list_with_note_calls_proper_path_and_params(self):
        ''' list(123, 'jangxyz') calls GET ".../pages/123/attachments..domain=jangxyz" '''
        note = 'jangxyz'
        page_id = self.page.id
        # mock
        url_pattern = "/pages/%d/attachments[.].*domain=%s" % (page_id, note)
        url_pattern = re.compile(url_pattern)
        self.expects_springnote_request.with_at_least(
            method = eq("GET"), 
            url    = string_contains(url_pattern)
        )
        # run
        springnote.Attachment.list(self.auth, page_id, note=note)

    @unittest.test
    def get_calls_proper_path_and_params(self):
        ''' get() calls GET ".../pages/1/attachments/123 with .json '''
        self.page.note = 'jangxyz'
        # mock
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
        pageid_less_attach = springnote.Attachment(self.auth, idless_page, id=123)
        should_raise(springnote.SpringnoteError.InvalidOption, 
                    when=lambda: pageid_less_attach.delete())

        # test attachment without id
        id_less_attach = springnote.Attachment(self.auth, self.page, id=None)
        should_raise(springnote.SpringnoteError.InvalidOption, 
                    when=lambda: id_less_attach.delete())

    @unittest.test
    def upload_old_file_calls_proper_path_params_and_dumped_data(self):
        ''' upload() existing file calls proper path, param and file object '''
        self.attach.file = self.file_obj
        # mock
        url_pattern = "/pages/%d/attachments/%d[.]" % (self.page.id, self.attach.id)
        url_pattern = re.compile(url_pattern)
        self.expects_springnote_request.with_at_least(
            method=eq("PUT"), url=string_contains(url_pattern),
            body=eq(self.file_obj)
        )
        # run
        self.attach.upload()

    @unittest.test
    def upload_new_file_calls_proper_path_and_params_and_dumped_data(self):
        ''' upload() new file calls proper path, param and file object '''
        self.attach.id   = None
        self.attach.file = self.file_obj
        # mock
        url_pattern = re.compile("/pages/%d/attachments[.]" % self.page.id)
        self.expects_springnote_request.with_at_least(
            method=eq("POST"), url=string_contains(url_pattern),
            body=eq(self.file_obj))
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
        # page without an id
        page   = springnote.Page(self.auth, None)
        attach = springnote.Attachment(self.auth, page, file=self.file_obj)
        should_raise(springnote.SpringnoteError.InvalidOption, 
                    when = lambda: attach.upload())

        # no file
        attach = springnote.Attachment(self.auth, self.page, file=None)
        should_raise(springnote.SpringnoteError.InvalidOption, 
                    when = lambda: attach.upload())

#class AttachmentDownloadTestCase(unittest.TestCase):
#    def setUp(self):    
#        springnote.Springnote = mock_class_Springnote()
#
#        # mock
#        # file object mock
#        file_content = 'FILE CONTENT'
#        http_response = Mock()
#        http_response.status = 200
#        http_response.expects(once()).read() \
#            .will(return_value(file_content))
#        # springnote request mock
#        self.expects_springnote_request = \
#            springnote.Springnote.expects(once()).method('springnote_request') \
#                .will(return_value(http_response))
#
#        #
#        self.auth = Mock()
#        self.auth.access_token, self.auth.consumer_token = ('AT', 'CT')
#        self.page   = springnote.Page(self.auth, id=1)
#        self.attach = springnote.Attachment(self.auth, self.page, id=123)
#
#    def tearDown(self): 
#        springnote.Springnote = restore_class_Springnote()
#
#    @unittest.test
#    def download_calls_proper_path_and_params(self):
#        ''' download() calls GET ".../pages/1/attachments/123 without .json '''
#        # mock
#        url_pattern = re.compile(
#            "/pages/%d/attachments/%d$" % (self.page.id, self.attach.id))
#        self.expects_springnote_request.with_at_least(
#            method=eq("GET"), url=string_contains(url_pattern))
#        # run
#        self.attach.download()
#
#    @unittest.test
#    def download_saves_file_content_but_no_title(self):
#        ''' download() saves response to content, but not metadata '''
#        attach = springnote.Attachment(self.auth, self.page, id=123)
#        attach.download()
#        assert_that(attach.title,   is_(None))
#        assert_that(attach.content, is_not(None))
#
#    @unittest.test
#    def download_saves_file_to_local(self):
#        ''' download(filename) saves to local filename '''
#        filename = 'localfile.txt'
#        run = lambda: self.attach.download(filename)
#        should_call_method(springnote.__builtin__, 'open',
#            when = run,
#            arg  = with_(eq(filename), string_contains('w')))
#
#    @unittest.test
#    def download_with_filename_true_saves_locally_with_same_filename(self):
#        ''' download(filename=True) saves with same filename '''
#        self.attach.title = "some_filename.txt"
#        filename = True
#        run = lambda: self.attach.download(filename)
#        should_call_method(springnote.__builtin__, 'open',
#            when = run,
#            arg  = with_(eq(self.attach.title), string_contains('w')))
#
#    @unittest.test
#    def download_with_path_and_filename_saves_in_that_position(self):
#        ''' download() with path and filename saves to that path '''
#        filename = "test_file.txt"
#        path     = "/tmp"
#        run = lambda: self.attach.download(filename, path)
#        should_call_method(springnote.__builtin__, 'open',
#            when = run,
#            arg  = with_(eq(path +"/"+ filename), string_contains('w')))
#            
#    @unittest.test
#    def download_should_not_save_file_if_file_does_not_exist(self):
#        ''' download(filename) should not save locally if file already exist '''
#        filename = 'localfile.txt'
#        run      = lambda: self.attach.download(filename)
#        # save & patch
#        O_os_path_exists = springnote.os.path.exists
#        springnote.os.path.exists = lambda x: True
#        
#        should_not_call_method(springnote.__builtin__, 'open',
#            when = run,
#            arg  = with_(eq(filename), string_contains('w')))
#
#        # recover
#        springnote.os.path.exists = O_os_path_exists
#
#    @unittest.test
#    def download_with_overwrite_should_save_file_even_if_file_does_not_exist(self):
#        ''' download(filename, overwrite) should save locally even if file exists '''
#        filename  = 'localfile.txt'
#        run       = lambda: self.attach.download(filename, overwrite=True)
#        # save & patch
#        O_os_path_exists = springnote.os.path.exists
#        springnote.os.path.exists = lambda x: True
#        
#        should_call_method(springnote.__builtin__, 'open',
#            when = run,
#            arg  = with_(eq(filename), string_contains('w')))
#
#        # recover
#        springnote.os.path.exists = O_os_path_exists
#
#    @unittest.test
#    def download_and_delete_methods_should_have_both_page_id_and_id(self):
#        ''' download() raises InvalidOption if any of page id and id is not given '''
#        # test page without id
#        idless_page = springnote.Page(self.auth, None) 
#        pageid_less_attach = springnote.Attachment(self.auth, idless_page, id=123)
#        should_raise(springnote.SpringnoteError.InvalidOption, 
#                    when=lambda: pageid_less_attach.download())
#
#        # test attachment without id
#        id_less_attach = springnote.Attachment(self.auth, self.page, id=None)
#        should_raise(springnote.SpringnoteError.InvalidOption, 
#                    when=lambda: id_less_attach.download())


if __name__ == '__main__':
    unittest.main()

