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
from datetime import datetime, timedelta
import time

class SpringnoteResourceTestCase(unittest.TestCase):
    def setUp(self):
        # mock
        springnote.Springnote = mock_class_Springnote()
        # http_response mock
        self.http_response = Mock()
        self.http_response.status = 200
        self.http_response.expects(once()).read() \
            .will(return_value(self.sample_json))
        # springnote request mock
        self.expects_springnote_request = \
            springnote.Springnote.expects(once()).method('springnote_request') \
                .will(return_value(self.http_response))
        #
        self.sn   = springnote.Springnote()
        self.page = springnote.Page(self.sn, id=123)

    def tearDown(self): 
        # restore
        springnote.Springnote = restore_class_Springnote()

    def verify_classmethod_list(self, resource_class, method, url_pattern):
        ''' Resource.list() calls specified URL with speicified HTTP method '''
        self.expects_springnote_request.with_at_least(
            method = eq(method),
            url    = string_contains(url_pattern)
        )
        # run
        resource_class.list(self.page)

    def verify_id_is_same_with_identifier(self, new_cls):
        id = 123
        obj = new_cls()
        obj.id = id
        assert_that(obj.identifier, is_(id))

        obj = new_cls()
        obj.identifier = id
        assert_that(obj.id, is_(id))

    def verify_datetime_format(self, resource_cls, json, attr_name):
        ''' json is converted to attribute in resource_cls, in datetime format '''
        obj = resource_cls.from_json(json, auth=self.sn, parent=self.page)
        assert_that(getattr(obj, attr_name), instance_of(datetime))

    def verify_localtime_conversion(self, resource_cls, json, attr_name):
        ''' converts datetime format in localtime '''
        date_data = springnote.json.loads(json)
        if len(date_data.keys()) is 1:
            date_data = date_data.values()[0]
        date_data = date_data[attr_name]
        # run 
        format = getattr(resource_cls, 'datetime_format')
        dt = datetime.strptime(date_data, format)
        # localize
        if format == "%Y/%m/%d %H:%M:%S +0900":
            dt -= timedelta(seconds=9*60*60)
        dt -= timedelta(seconds=time.timezone)

        obj = resource_cls.from_json(json, auth=self.sn, parent=self.page)
        # verify 
        assert_that(getattr(obj, attr_name).timetuple(), is_(dt.timetuple()))

    def verify_unconverted_datetime(self, resource_cls, json, attr_name):
        ''' unconverted datetime format is stored in resource attribute '''
        date_data = springnote.json.loads(json)
        if len(date_data.keys()) is 1:
            date_data = date_data.values()[0]
        date_data = date_data[attr_name]
        # run & verify
        obj = resource_cls.from_json(json, auth=self.sn, parent=self.page)
        assert_that(obj.resource[attr_name], is_(date_data))

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
        instance = Comment(parent=self.page)
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

    @unittest.test
    def id_should_be_same_as_identifier(self):
        self.verify_id_is_same_with_identifier(lambda: Comment(self.page))

    @unittest.test
    def converts_date_created_into_datetime_format(self):
        ''' date_created converts to datetime format '''
        self.verify_datetime_format(Comment, self.sample_json, 'date_created')

    @unittest.test
    def converts_datetime_format_with_localtimezone(self):
        ''' date_created converts to datetime in localtime '''
        self.verify_localtime_conversion(Comment, self.sample_json, 'date_created')

    @unittest.test
    def unconverted_datetime_is_in_resource(self):
        ''' string format date_created is in resource["date_created"] '''
        self.verify_unconverted_datetime(Comment, self.sample_json, 'date_created')


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
        instance = Collaboration(parent=self.page)
        assert_that(getattr(instance, 'rights_holder', False), is_not(False))
        assert_that(getattr(instance, 'access_rights', False), is_not(False))
        assert_that(getattr(instance, 'date_created',  False), is_not(False))

    @unittest.test
    def classmethod_list_calls_proper_path_and_params(self):
        ''' Collaboration.list() calls GET /pages/123/collaboration.json '''
        url_pattern = re.compile("/pages/%d/collaboration[.]" % self.page.id)
        self.verify_classmethod_list(Collaboration, "GET", url_pattern)

    @unittest.test
    def there_is_no_id_nor_identifier(self):
        collab = Collaboration(self.page)
        assert_that(hasattr(collab, 'id'        ), is_(False))
        assert_that(hasattr(collab, 'identifier'), is_(False))

    @unittest.test
    def converts_date_created_into_datetime_format(self):
        ''' date_created converts to datetime format '''
        self.verify_datetime_format(Collaboration, self.sample_json, 'date_created')

    @unittest.test
    def converts_datetime_format_with_localtimezone(self):
        ''' date_created converts to datetime in localtime '''
        self.verify_localtime_conversion(Collaboration, self.sample_json, 'date_created')

    @unittest.test
    def unconverted_datetime_is_in_resource(self):
        ''' string format date_created is in resource '''
        self.verify_unconverted_datetime(Collaboration, self.sample_json, 'date_created')

from springnote import Lock
class LockTestCase(SpringnoteResourceTestCase):
    sample_json = '{' \
        '"creator": "http://aaron.myid.net/",' \
        '"relation_is_part_of": 4,' \
        '"date_expired": "2008/10/28 13:08:30 +0000"' \
    '}'
    #'"date_expired": "2008-10-28T13:08:30Z"' \
    @unittest.test
    def has_springnote_attributes(self):
        ''' Lock has attributes for springnote '''
        # you actually have no reason to make an instance this way
        instance = Lock(parent=self.page)
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
        Lock(parent=self.page).get()

    @unittest.test
    def acquire_calls_proper_path_and_params(self):
        ''' Lock().acquire() calls POST /pages/123/lock.json '''
        url_pattern = re.compile("/pages/%d/lock[.]" % self.page.id)
        self.expects_springnote_request.with_at_least(
            method = eq("POST"),
            url    = string_contains(url_pattern)
        )
        # run
        Lock(parent=self.page).acquire()

    @unittest.test
    def converts_date_expired_into_datetime_format(self):
        ''' date_expired converts to datetime format '''
        self.verify_datetime_format(Lock, self.sample_json, 'date_expired')

    @unittest.test
    def converts_datetime_format_with_localtimezone(self):
        ''' date_expired converts to datetime in localtime '''
        self.verify_localtime_conversion(Lock, self.sample_json, 'date_expired')

    @unittest.test
    def unconverted_datetime_is_in_resource(self):
        ''' string format date_expired is in resource '''
        self.verify_unconverted_datetime(Lock, self.sample_json, 'date_expired')


from springnote import Revision
class RevisionTestCase(SpringnoteResourceTestCase):
    sample_json = '{"revision": {' \
        '"creator": "http://deepblue.myid.net/", ' \
        '"identifier": 29685883, ' \
        '"source": "\\u003Cp\\u003ENone\\u003C/p\\u003E\\n", ' \
        '"relation_is_part_of": 1, ' \
        '"date_created": "2008/01/08 10:55:36 +0900" ' \
    '}}'
    #'"date_created": "2008/01/08 10:55:36 +0000" ' \
    @unittest.test
    def has_springnote_attributes(self):
        ''' Revision has attributes for springnote '''
        instance = Revision(parent=self.page)
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
        ''' Revision(id=4567).get() calls GET /pages/123/revisions/4567.json '''
        id = 4567
        url_pattern = re.compile("/pages/%d/revisions/%d[.]" % (self.page.id, id))
        self.expects_springnote_request.with_at_least(
            method = eq("GET"),
            url    = string_contains(url_pattern)
        )
        # run
        Revision(parent=self.page, id=id).get()

    @unittest.test
    def should_have_parent_id_and_one_of_index_or_id_and_parent_id(self):
        ''' Revision.get() without parent.id or (id|index) raises exception '''
        # (parent.id, id) is okay
        rev = Revision(self.page, id=3)
        should_call_method(springnote.Revision, 'request', when=lambda: rev.get())

        # (parent.id, index) is okay
        rev = Revision(self.page, index=-3)
        should_call_method(springnote.Revision, 'list', when=lambda: rev.get())

        # (parent.id=None, id or index) is NOT okay
        idless_page = springnote.Page(self.page.auth, None) 
        pageid_less_rev = springnote.Revision(idless_page, id=123)
        should_raise(springnote.SpringnoteError.InvalidOption, 
                    when=lambda: pageid_less_rev.get())

        # (parent.id, id=None, index=None) is NOT okay
        id_less_rev = springnote.Revision(self.page, id=None, index=None)
        should_raise(springnote.SpringnoteError.InvalidOption, 
                    when=lambda: id_less_rev.get())

    @unittest.test
    def converts_date_created_into_datetime_format(self):
        ''' date_created converts to datetime format '''
        self.verify_datetime_format(Revision, self.sample_json, 'date_created')

    @unittest.test
    def converts_datetime_format_with_localtimezone(self):
        ''' date_created converts to datetime in localtime '''
        self.verify_localtime_conversion(Revision, self.sample_json, 'date_created')

    @unittest.test
    def unconverted_datetime_is_in_resource(self):
        ''' string format date_created is in resource '''
        self.verify_unconverted_datetime(Revision, self.sample_json, 'date_created')

    @unittest.test
    def datetime_conversion_preservers_timezone(self):
        ''' convert and unconverting datetime returns to same string '''
        date_created = springnote.json.loads(self.sample_json)
        date_created = date_created['revision']['date_created']
        rev = Revision(auth=self.sn, parent=self.page, id=4567).get()
        assert_that(rev.resource['date_created'], is_(date_created))

class RevisionWithIndexTestCase(unittest.TestCase):
    def setUp(self):
        self.sn   = springnote.Springnote()
        self.page = springnote.Page(self.sn, id=123)

    @unittest.test
    def get_with_index_calls_list(self):
        ''' Revision(index=-2).get() calls list() and request() with index id '''
        index   = -2
        verbose = True
        rev     = Revision(parent=self.page, index=index)
        run = lambda: rev.get(verbose=verbose)

        # calls Revision.list
        should_call_method(springnote.Revision, 'list', when=run,
            arg=with_(eq(springnote.Revision), eq(self.page), verbose=eq(verbose)),
            method_type=classmethod,
        )

    @unittest.test
    def get_with_index_calls_get_with_id_from_list(self):
        ''' Revision(index=-2).get() calls request with -2th id of revisions '''
        # save
        o_revision_list = springnote.Revision.list

        page    = self.page
        index   = -2
        id      = 4567
        verbose = True
        
        rev1 = Revision(parent=page, id=id)
        rev2 = Revision(parent=page, id=id+1)
        rev1.date_created = 1
        rev2.date_created = 2
        springnote.Revision.list = lambda *args, **kwarg: [rev2, rev1]

        # calls revision.get()
        rev = Revision(parent=page, index=index)
        run = lambda: rev.get(verbose=verbose)
        url = "/pages/%d/revisions/%d." % (page.id, id)
        should_call_method(springnote.Revision, 'request', when=run,
            arg=with_at_least(eq(rev), contains_string(url), verbose=eq(verbose)))

        # restore
        springnote.Revision.list = o_revision_list

    @unittest.test
    def get_with_too_large_index_raises_exception(self):
        ''' Revision(index=-10000).get() with no such revision raises error '''
        # save
        o_revision_list = springnote.Revision.list

        page    = self.page
        index   = -10000        # too big!
        id      = 4567
        verbose = True
        
        rev1, rev2 = Revision(parent=page, id=id), Revision(parent=page, id=id+1)
        rev1.date_created, rev2.date_created = 1, 2
        springnote.Revision.list = lambda *args, **kwarg: [rev2, rev1]

        # calls revision.get()
        run = lambda: Revision(parent=page, index=index).get(verbose=verbose)
        should_raise(springnote.SpringnoteError.InvalidOption, when=run)

        # restore
        springnote.Revision.list = o_revision_list


if __name__ == '__main__':
    unittest.main()

