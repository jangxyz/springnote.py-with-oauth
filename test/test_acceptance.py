#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
    Try each feature as much as possible, communicating with springnote.com

        needs user interaction to get access-key

'''
import test_env, unittest
from hamcrest import *
import datetime, sys
from springnote import Springnote, Page, Attachment, Comment, Collaboration, Revision, Lock, SpringnoteError

global_verbose      = None
global_access_token = None

# test basic springnote request
test_basic_function_calls = True
# test object calls (eg, Attachment.upload)
test_object_calls         = True
test_page_object          = True
test_attachment_object    = True
test_comment_object       = True
test_collaboration_object = True
test_lock_object          = True
test_revision_object      = True
# test sugar calls (eg, page.upload_attachment)
test_sugar_methods               = True
test_page_sugar_methods          = True
test_attachment_sugar_methods    = True
test_comment_sugar_methods       = True
test_collaboration_sugar_methods = True
test_lock_sugar_methods          = True
test_revision_sugar_methods      = True


def _starting(msg):
    print msg,
    sys.stdout.flush()
_printout=_starting

def _check_http_status(response, msg):
    import sys
    if response.status != 200:
        print msg
        print 'halting with code', response.status
        sys.exit(response.status)
    else:
        _okay()

def _okay():
    print "\tok"

def parse_data(json_body, keyword):
    partial = json_body.split(keyword, 2)
    if len(partial) < 2:
        return None
    return int(partial[1].split(",")[0].strip('\'": ')) 

def should_raise(exception, when):
    callable = when
    try:
        callable()
        raise AssertionError, "did not raise exception %s" % exception
    except exception:
        pass # proper exception raised
    except Exception, e:
        error_msg = 'expected %s to be raised but instead got %s:"%s"' % (exception, type(e), e)
        raise AssertionError, error_msg

class File:     # simple file object
    def __init__(self, name, content):
        self.name = name
        self.read = lambda: content

class IntegrationTestCase(unittest.TestCase):
    def setUp(self):    pass
    def tearDown(self): pass

    def test_whole(self):
        '''
            1.  get access key (user interaction needed)     [GET access token]
            2.  get list of pages of default note            [LIST   page]
            3.  this checks access token                     [AUTH access token]
            4.  get a page                                   [GET    page]
            5.  create a page                                [POST   page]
            6.  edit the page                                [PUT    page]
            7.  get revisions of the page                    [LIST   revision]
            8.  get the some_rev revision of the page           [GET    revision]
            9.  get collaborations of the page               [LIST   collaboration]
            10. get attachments of the page                  [LIST   attachments]
            11. post attachment to the page                  [POST   attachment]
            12. get the attachment                           [GET    attachments]
            13. download attachment of the page              [GET    attachment]
            14. delete attachment to the page                [DELETE attachment]
            15. delete page                                  [DELETE page]
        '''
        global test_id, global_tag

        test_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        global_tag = 'springnote_oauthpy_integartion_test'
        print 'start test at', test_id

        sn = Springnote()
        self._test_access_token(sn)
        if test_basic_function_calls: self._test_basic_function_calls(sn)
        if test_object_calls:         self._test_object_calls(sn)
        if test_sugar_methods:        self._test_sugar_methods(sn)

        self.cleanup(sn)
        print "done."

    def _test_access_token(self, sn):
        ''' GET access token
        get access key (user interaction needed) '''
        global global_access_token

        if not global_access_token:
            request_token = sn.fetch_request_token(verbose=global_verbose)
            print "\ngo to this url and approve:", sn.authorize_url(request_token)
            raw_input("Press enter when complete. ")
            sn.fetch_access_token(request_token, verbose=global_verbose)
            _starting("test GET access token..")
            _printout("%s:%s" % (sn.access_token.key, sn.access_token.secret))
            _okay()
        else:
            print "skipping GET access token (using %s)" % ':'.join(global_access_token)
            from springnote import oauth
            sn.access_token = oauth.OAuthToken(*global_access_token)

    def _test_basic_function_calls(self, sn):
        ''' calls each functions following the scenario, checking for response status 200 '''
        # LIST page - get list of pages of default note            
        _starting("test GET pages..")
        url  = "http://api.springnote.com/pages.json"
        resp = sn.springnote_request("GET", url, verbose=global_verbose)
        _check_http_status(resp, "error on LIST page with access token " + `(sn.access_token.key, sn.access_token.secret)`)

        page_id = int(resp.read().split("identifier", 2)[1].split(",")[0].strip('\'": ')) 

        # AUTH access token - this checks access token                     
        _starting("test using access token..")
        _okay()

        # GET page - get most recently modified page              
        _starting("test GET page..")
        url  = 'http://api.springnote.com/pages/%d.json' % page_id
        resp = sn.springnote_request("GET", url, verbose=global_verbose)
        _check_http_status(resp, "error on GET page %d" % page_id)

        # POST page - create a page                                
        _starting("test POST page..")
        url  = 'http://api.springnote.com/pages.json'
        body = '{"page": {"source": "integration test. if you happen to see this, erase it for me", "tags": "%s", "title": "test - %s"}}' % (global_tag, test_id)
        resp = sn.springnote_request("POST", url, body=body, verbose=global_verbose)
        _check_http_status(resp, "error on POST page with body: %s" % body)
        page_id = int(resp.read().split("identifier", 2)[1].split(",")[0].strip('\'": ')) 

        # PUT page - edit the page                                
        _starting("test PUT page..")
        url  = 'http://api.springnote.com/pages/%d.json' % page_id
        body = '{"page": {"source": "edited"}}'
        resp = sn.springnote_request("PUT", url, body=body, verbose=global_verbose)
        _check_http_status(resp, "error on PUT page %d with body: %s" % (page_id, body))

        # LIST revision - get revisions of the page                    
        _starting("test LIST revisions..")
        url  = 'http://api.springnote.com/pages/%d/revisions.json' % page_id
        resp = sn.springnote_request("GET", url, verbose=global_verbose)
        _check_http_status(resp, "error on LIST revisions")
        revision_id = parse_data(resp.read(), "identifier")

        # GET revision - get the some_rev revision of the page           
        _starting("test GET revisions..")
        url  = 'http://api.springnote.com/pages/%d/revisions/%d.json' % (page_id, revision_id)
        resp = sn.springnote_request("GET", url, verbose=global_verbose)
        _check_http_status(resp, "error on GET revision")

        # LIST collaboration - get collaborations of the page               
        _starting("test LIST collaboration")
        url  = 'http://api.springnote.com/pages/%d/collaboration.json' % page_id
        resp = sn.springnote_request("GET", url, verbose=global_verbose)
        _check_http_status(resp, "error on LIST collaboration")

        # LIST attachments - get attachments of the page                  
        _starting("test LIST attachments")
        url  = 'http://api.springnote.com/pages/%d/attachments.json' % page_id
        resp = sn.springnote_request("GET", url, verbose=global_verbose)
        _check_http_status(resp, "error on LIST attachments")

        # POST attachment - post attachment to the page                  
        _starting("test POST attachment")
        url     = 'http://api.springnote.com/pages/%d/attachments.json' % page_id
        data    = open(__file__, 'rb') # i shall sacrifice myself for testing!
        resp = sn.springnote_request("POST", url, body=data, verbose=global_verbose)
        data.close()
        _check_http_status(resp, "error on POST attachment")
        attachment_id = parse_data(resp.read(), "identifier")

        # PUT attachment - put attachment to the page
        _starting("test PUT attachment")
        url  = 'http://api.springnote.com/pages/%d/attachments/%d.json' % (page_id, attachment_id)
        data = open(__file__, 'rb') 
        resp = sn.springnote_request("PUT", url, body=data, verbose=global_verbose)
        _check_http_status(resp, "error on PUT attachment")

        # GET attachment - get information about attachment
        _starting("test GET attachment")
        url  = 'http://api.springnote.com/pages/%d/attachments/%d.json' % (page_id, attachment_id)
        resp = sn.springnote_request("GET", url, verbose=global_verbose)
        _check_http_status(resp, "error on GET attachment")

        # DOWNLOAD attachment - download attachment of the page              
        _starting("test DOWNLOAD attachment")
        url  = 'http://api.springnote.com/pages/%d/attachments/%d' % (page_id, attachment_id)
        resp = sn.springnote_request("GET", url, headers={}, verbose=global_verbose)
        _check_http_status(resp, "error on DOWNLOAD attachment")

        # DELETE attachment - delete attachment to the page                
        _starting("test DELETE attachment")
        url  = 'http://api.springnote.com/pages/%d/attachments/%d.json' % (page_id, attachment_id)
        resp = sn.springnote_request("DELETE", url, verbose=global_verbose)
        _check_http_status(resp, "error on DELETE attachment")

        # DELETE page - delete page                                  
        _starting("test DELETE page")
        url  = "http://api.springnote.com/pages/%d.json" % page_id
        resp = sn.springnote_request("DELETE", url, verbose=global_verbose)
        _check_http_status(resp, "error on DELETE page")

    def _test_object_calls(self, auth):
        if test_page_object:
            # LIST page: get list of pages of default note            
            _starting("test Page.list()..")
            pages = Page.list(auth, verbose=global_verbose)
            _printout("%d pages" % len(pages))
            
            # LIST page with options
            last_modified = sorted(pages, \
                cmp=lambda x,y: cmp(x.date_modified, y.date_modified))[-1]
            most_recent = Page.list(auth, 
                            sort="date_modified", order="desc", count=1,
                            verbose=global_verbose)[0]
            for attr in ["identifier", "title", "source", "date_modified"]:
                last_modified_attr = getattr(last_modified, attr)
                most_recent_attr   = getattr(most_recent, attr)
                assert_that(last_modified_attr, is_(equal_to(most_recent_attr)))
            _okay()

            # GET page: get most recently modified page
            _starting("test page.get() READ ..")
            page = Page(auth, id=last_modified.id).get(verbose=global_verbose)
            assert_that(page.title, is_(equal_to(last_modified.title)))
            _okay()

        # you need this to test other resources
        if True:
            # POST page: create a page
            _starting("test page.save() CREATE ..")
            page = Page(auth, 
                title  = "POST test for %s" % test_id, 
                source = "hola!",
                tags   = global_tag 
            ).save(verbose=global_verbose)
            new_pages = Page.list(auth, verbose=global_verbose)
            if test_page_object:
                assert_that(len(pages) +1, is_(equal_to(len(new_pages))))
            _okay()

        if test_page_object:
            # PUT page: edit the page
            _starting("test page.save() UPDATE ..")
            page.source = "modified"
            page.save(verbose=global_verbose)
            refetch = Page(auth, id=page.id).get(verbose=global_verbose)
            assert_that(refetch.source, contains_string("modified"))
            _okay()

        # test other resources
        if test_attachment_object:     self._test_attachment_object(page)
        if test_comment_object:        self._test_comment_object(page)
        if test_collaboration_object:  self._test_collaboration_object(page)
        if test_lock_object:           self._test_lock_object(page)
        if test_revision_object:       self._test_revision_object(page)

        # you need this to test other resources
        if True:
            # DELETE page:   delete page                                  
            _starting("test page.delete() DELETE ..")
            page.delete(verbose=global_verbose)
            should_raise(SpringnoteError.Response, 
                lambda: Page(auth, id=page.id).get(verbose=global_verbose)
            )
            _okay()
        
    def _test_attachment_object(self, page):
        # LIST attachment - count 0
        attaches = Attachment.list(page, verbose=global_verbose)
        assert_that(len(attaches), is_(0))

        # POST attachment
        _starting("test Attachment.upload() CREATE ..")
        data = open(__file__, 'rb') # i shall sacrifice myself for testing!
        attach = Attachment(page, file=data)
        assert_that(attach.date_created, is_(None))
        attach.upload(verbose=global_verbose)
        data.close()
        assert_that(attach.date_created, is_not(None))
        prev_attach_rsrc = attach.resource
        # LIST attachment - count 1
        attaches = Attachment.list(page, verbose=global_verbose)
        assert_that(len(attaches), is_(1))
        assert_that(attaches[0].id, is_(attach.id))
        _okay()

        # PUT attachment
        _starting("test Attachment.upload() UPDATE ..")
        attach.file = File('tmp2', 'CONTENT!')
        attach.upload(verbose=global_verbose)
        assert_that(attach.id          , is_(prev_attach_rsrc["identifier"]))
        assert_that(attach.title       , is_not(prev_attach_rsrc["title"]))
        assert_that(attach.description , is_not(prev_attach_rsrc["description"]))
        assert_that(attach.resource["date_created"], is_(prev_attach_rsrc["date_created"]))
        _okay()
        
        # DELETE attachment
        _starting("test Attachment.delete() ..")
        attach.delete(verbose=global_verbose)
        # LIST attachment - count 0
        attaches = Attachment.list(page, verbose=global_verbose)
        assert_that(len(attaches), is_(0))
        _okay()
        _starting("test Attachment.list() ..")
        _okay()

    def _test_comment_object(self, page):
        # LIST comment - count 0
        _starting("test Comment.list() ..")
        comments = Comment.list(page, verbose=global_verbose)
        assert_that(comments, has_length(0))
        _okay()

    def _test_collaboration_object(self, page):
        # LIST collaboration - count 0
        _starting("test Collaboration.list() ..")
        collabs = Collaboration.list(page, verbose=global_verbose)
        assert_that(collabs, has_length(0))
        _okay()

    def _test_lock_object(self, page):
        # GET lock 
        _starting("test lock.get() ..")
        lock = Lock(page).get(verbose=global_verbose)
        assert_that(lock.relation_is_part_of, is_(page.id))
        _okay()

        # POST lock - acquire lock. lock expire time udpated
        _starting("test lock.acquire() ..")
        new_lock = Lock(page).acquire(verbose=global_verbose)
        assert_that(new_lock.date_expired, is_not(None))
        assert_that(new_lock.date_expired, is_not(lock.date_expired))
        _okay()

    def _test_revision_object(self, page):
        # LIST reivisions - count 4 (page create, update, attachment create, update)
        _starting("test revision.list() ..")
        revs = Revision.list(page, verbose=global_verbose)
        assert_that(revs, has_length(4))
        first = min(revs, key=lambda x: x.date_created)
        #assert_that(first.description, 
        #                contains_string('이 페이지를 개설하였습니다'))
        assert_that(first.relation_is_part_of, is_(page.id))
        some_rev = filter(lambda r: r.description == '', revs)[0]
        assert_that(some_rev.source, is_(None))
        _okay()

        # GET revision 
        _starting("test revision.get() ..")
        rev = Revision(page, id=some_rev.id).get(verbose=global_verbose)
        assert_that(rev.source, is_not(None))
        _okay()

    def _test_sugar_methods(self, sn):
        self._test_page_sugar_methods(sn)

    def _test_page_sugar_methods(self, sn):
        if test_page_sugar_methods:
            _starting("test sn.list_pages() ..")
            pages = sn.list_pages(verbose=global_verbose)
            _printout("%d pages" % len(pages))
            
            # LIST page with options
            last_modified = sorted(pages, \
                cmp=lambda x,y: cmp(x.date_modified, y.date_modified))[-1]
            most_recent = sn.list_pages(sort="date_modified", order="desc", count=1,
                            verbose=global_verbose)[0]
            for attr in ["identifier", "title", "source", "date_modified"]:
                last_modified_attr = getattr(last_modified, attr)
                most_recent_attr   = getattr(most_recent, attr)
                assert_that(last_modified_attr, is_(equal_to(most_recent_attr)))
            _okay()

            # GET page: get most recently modified page
            _starting("test sn.get_page() READ ..")
            page = sn.get_page(id=last_modified.id, verbose=global_verbose)
            assert_that(page.title, is_(equal_to(last_modified.title)))
            _okay()

        # you need this to test other resources
        if True:
            # POST page: create a page
            _starting("test sn.save_page() CREATE ..")
            page = sn.save_page(title   = "POST test for %s" % test_id, 
                                source  = "hola!",
                                tags    = global_tag,
                                verbose =global_verbose)
            new_pages = sn.list_pages(verbose=global_verbose)
            if test_page_sugar_methods:
                assert_that(len(pages) +1, is_(equal_to(len(new_pages))))
            _okay()

        if test_page_sugar_methods:
            # PUT page: edit the page
            _starting("test sn.save_page() UPDATE ..")
            page.source = "modified"
            sn.save_page(id=page.id, source=page.source, verbose=global_verbose)
            refetch = sn.get_page(id=page.id, verbose=global_verbose)
            assert_that(refetch.source, contains_string("modified"))
            _okay()

        # test other resources
        if test_attachment_sugar_methods:     self._test_attachment_sugar_methods(page)
        if test_comment_sugar_methods:        self._test_comment_sugar_methods(page)
        if test_collaboration_sugar_methods:  self._test_collaboration_sugar_methods(page)
        if test_lock_sugar_methods:           self._test_lock_sugar_methods(page)
        if test_revision_sugar_methods:       self._test_revision_sugar_methods(page)

        # you need this to test other resources
        if True:
            # DELETE page:   delete page                                  
            _starting("test sn.delete_page() DELETE ..")
            sn.delete_page(id=page.id, verbose=global_verbose)
            should_raise(SpringnoteError.Response, 
                lambda: sn.get_page(id=page.id, verbose=global_verbose)
            )
            _okay()

    def _test_attachment_sugar_methods(self, page):
        # LIST attachment - count 0
        attaches = page.list_attachments(verbose=global_verbose)
        assert_that(len(attaches), is_(0))

        # POST attachment
        _starting("test page.upload_attachment() CREATE ..")
        data = open(__file__, 'rb') # i shall sacrifice myself for testing!
        attach = page.upload_attachment(file=data, verbose=global_verbose)
        data.close()
        assert_that(attach.date_created, is_not(None))
        prev_attach_rsrc = attach.resource
        # LIST attachment - count 1
        attaches = page.list_attachments(verbose=global_verbose)
        assert_that(len(attaches), is_(1))
        assert_that(attaches[0].id, is_(attach.id))
        _okay()

        # PUT attachment
        _starting("test upload_attachment() UPDATE ..")
        attach.file = File('tmp2', 'CONTENT!')
        page.upload_attachment(id=attach.id, file=attach.file, verbose=global_verbose)
        assert_that(attach.id         , is_(prev_attach_rsrc["identifier"]))
        assert_that(attach.title      , is_not(prev_attach_rsrc["title"]))
        assert_that(attach.description, is_not(prev_attach_rsrc["description"]))
        assert_that(attach.resource["date_created"], 
										is_(prev_attach_rsrc["date_created"]))
        _okay()
        
        # DELETE attachment
        _starting("test page.delete_attachment() ..")
        page.delete_attachment(id=attach.id, verbose=global_verbose)
        # LIST attachment - count 0
        attaches = page.list_attachments(verbose=global_verbose)
        assert_that(len(attaches), is_(0))
        _okay()
        _starting("test page.list_attachments() ..")
        _okay()

    def _test_comment_sugar_methods(self, page):
        # LIST comment - count 0
        _starting("test page.list_comment() ..")
        comments = page.list_comments(verbose=global_verbose)
        assert_that(comments, has_length(0))
        _okay()

    def _test_collaboration_sugar_methods(self, page):
        # LIST collaboration - count 0
        _starting("test page.list_collaboration() ..")
        collabs = page.list_collaborations(verbose=global_verbose)
        assert_that(collabs, has_length(0))
        _okay()

    def _test_lock_sugar_methods(self, page):
        # GET lock 
        _starting("test page.get_lock() ..")
        lock = page.get_lock(verbose=global_verbose)
        assert_that(lock.relation_is_part_of, is_(page.id))
        _okay()

        # POST lock - acquire lock. lock expire time udpated
        _starting("test page.acquire_lock() ..")
        new_lock = page.acquire_lock(verbose=global_verbose)
        assert_that(new_lock.date_expired, is_not(None))
        assert_that(new_lock.date_expired, is_not(lock.date_expired))
        _okay()

    def _test_revision_sugar_methods(self, page):
        # LIST reivisions - count 4 (page create, update, attachment create, update)
        _starting("test page.list_revision() ..")
        revs = page.list_revisions(verbose=global_verbose)
        number_of_revisions = 2
        if test_attachment_sugar_methods: 
            number_of_revisions = 4
        assert_that(revs, has_length(number_of_revisions))
        first = min(revs, key=lambda x: x.date_created)
        assert_that(first.relation_is_part_of, is_(page.id))
        some_rev = filter(lambda r: r.description == '', revs)[0]
        assert_that(some_rev.source, is_(None))
        _okay()

        # GET revision 
        _starting("test page.get_revision() ..")
        rev = page.get_revision(id=some_rev.id, verbose=global_verbose)
        assert_that(rev.source, is_not(None))
        _okay()


    def cleanup(self, sn):
        # delete garbage pages
        _starting('cleaning..')
        params = {'tags': global_tag}
        url  = 'http://api.springnote.com/pages.json?tags=%s' % global_tag
        resp = sn.springnote_request("GET", url, params, verbose=global_verbose)

        body = resp.read()
        partial = body.split('identifier', 1)
        page_ids = []
        while len(partial) >= 2:
            partial = partial[1].split(",", 1)
            page_id = int(partial[0].strip('\'": ')) 
            page_ids.append(page_id)
            #
            body = partial[1]
            partial = body.split('identifier', 1)

        _starting(page_ids)
        for page_id in page_ids:
            # delete
            url = "http://api.springnote.com/pages/%d.json" % page_id
            sn.springnote_request("DELETE", url, verbose=global_verbose)
        _okay()
        print 


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '-v':
        sys.argv.pop(1)
        global_verbose = True
    if len(sys.argv) > 1:
        global_access_token = sys.argv.pop(1).split(':')
    unittest.main()

