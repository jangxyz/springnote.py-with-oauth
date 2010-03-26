#!/usr/bin/python
'''
    Test CRUD calls for Comment, Lock, Collaboration, Revision Resources
'''
import test_env
from   test_env import *

import unittest

from pmock      import *
from pmock_xtnd import *
from hamcrest      import *
from hamcrest_xtnd import *

import springnote

class SpringnoteResourceTestCase(unittest.TestCase):
    def setUp(self):
        # mock
        springnote.Springnote = mock_class_Springnote()
        # http_response mock
        http_response = Mock()
        http_response.status = 200
        http_response.expects(once()).read() \
            .will(return_value(self.sample_json))
        # springnote request mock
        self.expects_springnote_request = \
            springnote.Springnote.expects(once()).method('springnote_request') \
                .will(return_value(http_response))
        #
        self.sn   = springnote.Springnote()
        self.page = springnote.Page(self.sn, id=123)

    def tearDown(self): 
        # restore
        springnote.Springnote = restore_class_Springnote()

    def verify_classmethod_list(self, resourceClass, method, url_pattern):
        ''' Resource.list() calls specified URL with speicified HTTP method '''
        self.expects_springnote_request.with_at_least(
            method = eq(method),
            url    = string_contains(url_pattern)
        )
        # run
        resourceClass.list(auth=self.sn, page=self.page)

from springnote import Comment
class CommentTestCase(SpringnoteResourceTestCase):
    sample_json = '{"comment": {' \
        '"source": "This is springnote",' \
        '"creator": "deepblue",' \
        '"date_created": "2008/10/28 12:46:47 +0000",' \
        '"relation_is_part_of": 4,' \
        '"identifier": 20' \
    '}}'

    @unittest.test
    def has_springnote_attributes(self):
        ''' Comment has attributes for springnote '''
        instance = Comment(auth=self.sn, parent=self.page)
        assert_that(getattr(instance, 'identifier',          False), is_not(False))
        assert_that(getattr(instance, 'date_created',        False), is_not(False))
        assert_that(getattr(instance, 'relation_is_part_of', False), is_not(False))
        assert_that(getattr(instance, 'creator',             False), is_not(False))
        assert_that(getattr(instance, 'source',              False), is_not(False))

    @unittest.test
    def classmethod_list_calls_proper_path_and_params(self):
        ''' Comment list() calls GET /pages/123/comments.json '''
        url_pattern = re.compile("/pages/%d/comments[.]" % self.page.id)
        self.verify_classmethod_list(Comment, "GET", url_pattern)


from springnote import Collaboration
class CollaborationTestCase(SpringnoteResourceTestCase):
    sample_json = '{"collaboration": {' \
        '"date_created": "2008/10/28 12:58:13 +0000",' \
        '"access_rights": "reader",' \
        '"rights_holder": "everybody",' \
        '"relation_is_part_of": 4' \
    '}}'
    @unittest.test
    def has_springnote_attributes(self):
        ''' Collaboration has attributes for springnote '''
        # you actually have no reason to make an instance this way
        instance = Collaboration(auth=self.sn, parent=self.page)
        assert_that(getattr(instance, 'rights_holder', False), is_not(False))
        assert_that(getattr(instance, 'access_rights', False), is_not(False))
        assert_that(getattr(instance, 'date_created',  False), is_not(False))

    @unittest.test
    def classmethod_list_calls_proper_path_and_params(self):
        ''' Collaboration.list() calls GET /pages/123/collaboration.json '''
        url_pattern = re.compile("/pages/%d/collaboration[.]" % self.page.id)
        self.verify_classmethod_list(Collaboration, "GET", url_pattern)

from springnote import Lock
class LockTestCase(SpringnoteResourceTestCase):
    sample_json = '{' \
        '"creator": "http://aaron.myid.net/",' \
        '"relation_is_part_of": 4,' \
        '"date_expired": "2008-10-28T13:08:30Z"' \
    '}'
    @unittest.test
    def has_springnote_attributes(self):
        ''' Lock has attributes for springnote '''
        # you actually have no reason to make an instance this way
        instance = Lock(auth=self.sn, parent=self.page)
        assert_that(getattr(instance, 'creator',             False), is_not(False))
        assert_that(getattr(instance, 'date_expired',        False), is_not(False))
        assert_that(getattr(instance, 'relation_is_part_of', False), is_not(False))

    @unittest.test
    def get_calls_proper_path_and_params(self):
        ''' Lock().get() calls GET /pages/123/lock.json '''
        url_pattern = re.compile("/pages/%d/lock[.]" % self.page.id)
        self.expects_springnote_request.with_at_least(
            method = eq("GET"),
            url    = string_contains(url_pattern)
        )
        # run
        Lock(auth=self.sn, parent=self.page).get()

    @unittest.test
    def acquire_calls_proper_path_and_params(self):
        ''' Lock().acquire() calls POST /pages/123/lock.json '''
        url_pattern = re.compile("/pages/%d/lock[.]" % self.page.id)
        self.expects_springnote_request.with_at_least(
            method = eq("POST"),
            url    = string_contains(url_pattern)
        )
        # run
        Lock(auth=self.sn, parent=self.page).acquire()


from springnote import Revision
class RevisionTestCase(SpringnoteResourceTestCase):
    sample_json = '{"revision": {' \
        '"creator": "http://deepblue.myid.net/", ' \
        '"identifier": 29685883, ' \
        '"source": "\\u003Cp\\u003ENone\\u003C/p\\u003E\\n", ' \
        '"relation_is_part_of": 1, ' \
        '"date_modified": "2008/01/08 10:55:36 +0000" ' \
    '}}'
    @unittest.test
    def has_springnote_attributes(self):
        ''' Revision has attributes for springnote '''
        instance = Revision(auth=self.sn, parent=self.page)
        assert_that(getattr(instance, 'identifier',          False), is_not(False))
        assert_that(getattr(instance, 'description',         False), is_not(False))
        assert_that(getattr(instance, 'creator',             False), is_not(False))
        assert_that(getattr(instance, 'date_created',        False), is_not(False))
        assert_that(getattr(instance, 'relation_is_part_of', False), is_not(False))
        assert_that(getattr(instance, 'source',              False), is_not(False))

    @unittest.test
    def classmethod_list_calls_proper_path_and_params(self):
        ''' Revision.list() calls GET /pages/123/revisions.json '''
        url_pattern = re.compile("/pages/%d/revisions[.]" % self.page.id)
        self.verify_classmethod_list(Revision, "GET", url_pattern)

    @unittest.test
    def get_calls_proper_path_and_params(self):
        ''' Revision().get() calls GET /pages/123/revisions/4567.json '''
        id = 4567
        url_pattern = re.compile("/pages/%d/revisions/%d[.]" % (self.page.id, id))
        self.expects_springnote_request.with_at_least(
            method = eq("GET"),
            url    = string_contains(url_pattern)
        )
        # run
        Revision(auth=self.sn, parent=self.page, id=id).get()


if __name__ == '__main__':
    unittest.main()

