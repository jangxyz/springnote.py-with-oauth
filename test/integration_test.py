#!/usr/bin/python
'''
    Try each feature

        It needs user interaction first (to get access-key)

'''

import test_env, unittest
from hamcrest import *
import datetime, sys
from springnote import Springnote, Page, SpringnoteError

global_verbose = None

def _starting(msg):
    print msg,
    sys.stdout.flush()
_printout=_starting

def check_http_status(response, msg):
    import sys
    if response.status != 200:
        print msg
        print 'halting with code', response.status
        sys.exit(response.status)
    else:
        print "\tOK"

def _okay():
    print "\tOK"

def parse_data(json_body, keyword):
    partial = json_body.split(keyword, 2)
    if len(partial) < 2:
        return None
    return int(partial[1].split(",")[0].strip('\'": ')) 

def should_raise(exception, callable):
    try:
        callable()
        raise AssertionError, "did not raise exception %s" % exception
    except exception:
        pass # proper exception raised
    except Exception, e:
        error_msg = 'expected %s to be raised but instead got %s:"%s"' % (exception, type(e), e)
        raise AssertionError, error_msg


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
            8.  get the first revision of the page           [GET    revision]
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
        self._test_basic_function_calls(sn)
        self._test_page_object_calls(sn)

        self.cleanup(sn)

        print "done."

    def _test_access_token(self, sn):
        ''' GET access token
        get access key (user interaction needed) '''
        request_token = sn.fetch_request_token(verbose=global_verbose)
        print "\ngo to this url and approve:", sn.authorize_url(request_token)
        raw_input("Press enter when complete. ")
        access_token = sn.fetch_access_token(request_token, verbose=global_verbose)
        print "test GET access token..", 
        _okay()

    def _test_basic_function_calls(self, sn):
        ''' calls each functions following the scenario, checking for response status 200 '''
        # LIST page
        #   get list of pages of default note            
        print "test GET pages..",
        url  = "http://api.springnote.com/pages.json"
        resp = sn.springnote_request("GET", url, verbose=global_verbose)
        check_http_status(resp, "error on LIST page with access token " + `(sn.access_token.key, sn.access_token.secret)`)
        page_id = int(resp.read().split("identifier", 2)[1].split(",")[0].strip('\'": ')) 

        # AUTH access token
        #   this checks access token                     
        print "test using access token..", "\tOK"

        # GET page
        #   get most recently modified page              
        print "test GET page..",
        url  = 'http://api.springnote.com/pages/%d.json' % page_id
        resp = sn.springnote_request("GET", url, verbose=global_verbose)
        check_http_status(resp, "error on GET page %d" % page_id)

        # POST page
        #   create a page                                
        print "test POST page..",
        url  = 'http://api.springnote.com/pages.json'
        body = '{"page": {"source": "integration test. if you happen to see this, erase it for me", "tags": "%s", "title": "test - %s"}}' % (global_tag, test_id)
        resp = sn.springnote_request("POST", url, body=body, verbose=global_verbose)
        check_http_status(resp, "error on POST page with body: %s" % body)
        page_id = int(resp.read().split("identifier", 2)[1].split(",")[0].strip('\'": ')) 

        # PUT page
        #   edit the page                                
        print "test PUT page..",
        url  = 'http://api.springnote.com/pages/%d.json' % page_id
        body = '{"page": {"source": "edited"}}'
        resp = sn.springnote_request("PUT", url, body=body, verbose=global_verbose)
        check_http_status(resp, "error on PUT page %d with body: %s" % (page_id, body))

        # LIST revision
        #   get revisions of the page                    
        print "test LIST revisions..",
        url  = 'http://api.springnote.com/pages/%d/revisions.json' % page_id
        resp = sn.springnote_request("GET", url, verbose=global_verbose)
        check_http_status(resp, "error on LIST revisions")
        revision_id = parse_data(resp.read(), "identifier")

        # GET revision
        #   get the first revision of the page           
        print "test GET revisiosn..",
        url  = 'http://api.springnote.com/pages/%d/revisions/%d.json' % (page_id, revision_id)
        resp = sn.springnote_request("GET", url, verbose=global_verbose)
        check_http_status(resp, "error on GET revision")

        # LIST collaboration
        #   get collaborations of the page               
        print "test LIST collaboration",
        url  = 'http://api.springnote.com/pages/%d/collaboration.json' % page_id
        resp = sn.springnote_request("GET", url, verbose=global_verbose)
        check_http_status(resp, "error on LIST collaboration")

        # LIST attachments
        #   get attachments of the page                  
        print "test LIST attachments",
        url  = 'http://api.springnote.com/pages/%d/attachments.json' % page_id
        resp = sn.springnote_request("GET", url, verbose=global_verbose)
        check_http_status(resp, "error on LIST attachments")

        # POST attachment
        #   post attachment to the page                  
        print "test POST attachment",
        url  = 'http://api.springnote.com/pages/%d/attachments.json' % page_id
        data = open(__file__, 'rb') # i shall sacrifice myself for testing!
        resp = sn.springnote_request("POST", url, body=data, verbose=global_verbose)
        data.close()
        check_http_status(resp, "error on POST attachment")
        attachment_id = parse_data(resp.read(), "identifier")

        # PUT attachment
        #  put attachment to the page
        print "test PUT attachment",
        url  = 'http://api.springnote.com/pages/%d/attachments/%d.json' % (page_id, attachment_id)
        data = open(__file__, 'rb') 
        resp = sn.springnote_request("PUT", url, body=data, verbose=global_verbose)
        check_http_status(resp, "error on PUT attachment")

        # GET attachment
        #   get information about attachment
        print "test GET attachment",
        url  = 'http://api.springnote.com/pages/%d/attachments/%d.json' % (page_id, attachment_id)
        resp = sn.springnote_request("GET", url, verbose=global_verbose)
        check_http_status(resp, "error on GET attachment")

        # DOWNLOAD attachment
        #   download attachment of the page              
        print "test DOWNLOAD attachment",
        url  = 'http://api.springnote.com/pages/%d/attachments/%d' % (page_id, attachment_id)
        resp = sn.springnote_request("GET", url, headers={}, verbose=global_verbose)
        check_http_status(resp, "error on DOWNLOAD attachment")

        # DELETE attachment
        #   delete attachment to the page                
        print "test DELETE attachment",
        url  = 'http://api.springnote.com/pages/%d/attachments/%d.json' % (page_id, attachment_id)
        resp = sn.springnote_request("DELETE", url, verbose=global_verbose)
        check_http_status(resp, "error on DELETE attachment")

        # DELETE page
        #   delete page                                  
        _starting("test DELETE page")
        url  = "http://api.springnote.com/pages/%d.json" % page_id
        resp = sn.springnote_request("DELETE", url, verbose=global_verbose)
        check_http_status(resp, "error on DELETE page")

    def _test_page_object_calls(self, sn):
        auth = sn
        # LIST page: get list of pages of default note            
        _starting("test Page.list()..")
        pages = Page.list(auth)
        _printout("%d pages" % len(pages))
        
        # LIST page with options
        last_modified = sorted(pages, \
            cmp=lambda x,y: cmp(x.date_modified, y.date_modified))[-1]
        most_recent = Page.list(auth, sort="date_modified", order="desc", count=1)[0]
        for attr in ["identifier", "title", "source", "date_modified"]:
            last_modified_attr = getattr(last_modified, attr)
            most_recent_attr   = getattr(most_recent, attr)
            assert_that(last_modified_attr, is_(equal_to(most_recent_attr)))
        _okay()

        # GET page: get most recently modified page
        _starting("test page.get() READ ..")
        page = Page(auth, id=last_modified.id).get()
        assert_that(page.title, is_(equal_to(last_modified.title)))
        _okay()

        # POST page: create a page
        _starting("test page.save() CREATE ..")
        page = Page(auth, 
            title  = "POST test for %s" % test_id, 
            source = "hola!",
            tags   = global_tag
        ).save()
        new_pages = Page.list(auth)
        assert_that(len(pages) +1, is_(equal_to(len(new_pages))))
        _okay()

        # PUT page: edit the page
        _starting("test page.save() UPDATE ..")
        page.source = "modified"
        page.save()
        refetch = Page(auth, id=page.id).get()
        assert_that(refetch.source, contains_string("modified"))
        _okay()

        # DELETE page
        #   delete page                                  
        _starting("test page.delete() DELETE ..")
        page.delete()
        should_raise(SpringnoteError.Response, 
            lambda: Page(auth, id=page.id).get()
        )
        _okay()
        

    def cleanup(self, sn):
        # delete garbage pages
        print 'cleaning..',
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

        print page_ids,
        for page_id in page_ids:
            # delete
            url = "http://api.springnote.com/pages/%d.json" % page_id
            sn.springnote_request("DELETE", url, verbose=global_verbose)
        print "\tOK"
        print 


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '-v':
        global_verbose = True
    unittest.main()

