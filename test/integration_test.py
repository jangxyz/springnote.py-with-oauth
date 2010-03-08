#!/usr/bin/python
'''
    Try each feature

        It needs user interaction first (to get access-key)

'''

import test_env, unittest
import datetime, sys
from springnote import Springnote

global_verbose = None

def check(response, msg):
    import sys
    if response.status != 200:
        print msg
        print 'halting with code', response.status
        sys.exit(response.status)
    else:
        print "\tOK"

def parse_data(json_body, keyword):
    partial = json_body.split(keyword, 2)
    if len(partial) < 2:
        return None
    return int(partial[1].split(",")[0].strip('\'": ')) 


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
        test_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        print 'start test at', test_id
        sn = Springnote()

        # GET access token
        #   get access key (user interaction needed)     
        request_token = sn.auth.fetch_request_token(verbose=global_verbose)
        print "\ngo to this url and approve:", sn.auth.authorize_url()
        raw_input("Press enter when complete. ")
        access_token = sn.auth.fetch_access_token(request_token, verbose=global_verbose)
        print "test GET access token..", "\tOK"

        # LIST page
        #   get list of pages of default note            
        print "test GET pages..",
        url  = "http://api.springnote.com/pages.json"
        resp = sn.springnote_request("GET", url, sign_token=access_token, verbose=global_verbose)
        check(resp, "error on LIST page with access token " + `(access_token.key, access_token.secret)`)
        page_id = int(resp.read().split("identifier", 2)[1].split(",")[0].strip('\'": ')) 

        # AUTH access token
        #   this checks access token                     
        print "test using access token..", "\tOK"

        # GET page
        #   get most recently modified page              
        print "test GET page..",
        url  = 'http://api.springnote.com/pages/%d.json' % page_id
        resp = sn.springnote_request("GET", url, sign_token=access_token, verbose=global_verbose)
        check(resp, "error on GET page %d" % page_id)

        # POST page
        #   create a page                                
        print "test POST page..",
        url  = 'http://api.springnote.com/pages.json'
        body = '{"page": {"source": "integration test. if you happen to see this, erase it for me", "tags": "springnote_oauth.py_integartion_test", "title": "test - %s"}}' % test_id
        resp = sn.springnote_request("POST", url, body=body, sign_token=access_token, verbose=global_verbose)
        check(resp, "error on POST page with body: %s" % body)
        page_id = int(resp.read().split("identifier", 2)[1].split(",")[0].strip('\'": ')) 

        # PUT page
        #   edit the page                                
        print "test PUT page..",
        url  = 'http://api.springnote.com/pages/%d.json' % page_id
        body = '{"page": {"source": "edited"}}'
        resp = sn.springnote_request("PUT", url, body=body, sign_token=access_token, verbose=global_verbose)
        check(resp, "error on PUT page %d with body: %s" % (page_id, body))

        # LIST revision
        #   get revisions of the page                    
        print "test LIST revisions..",
        url  = 'http://api.springnote.com/pages/%d/revisions.json' % page_id
        resp = sn.springnote_request("GET", url, sign_token=access_token, verbose=global_verbose)
        check(resp, "error on LIST revisions")
        revision_id = parse_data(resp.read(), "identifier")

        # GET revision
        #   get the first revision of the page           
        print "test GET revisiosn..",
        url  = 'http://api.springnote.com/pages/%d/revisions/%d.json' % (page_id, revision_id)
        resp = sn.springnote_request("GET", url, sign_token=access_token, verbose=global_verbose)
        check(resp, "error on GET revision")

        # LIST collaboration
        #   get collaborations of the page               
        print "test LIST collaboration",
        url  = 'http://api.springnote.com/pages/%d/collaboration.json' % page_id
        resp = sn.springnote_request("GET", url, sign_token=access_token, verbose=global_verbose)
        check(resp, "error on LIST collaboration")

        # LIST attachments
        #   get attachments of the page                  
        print "test LIST attachments",
        url  = 'http://api.springnote.com/pages/%d/attachments.json' % page_id
        resp = sn.springnote_request("GET", url, sign_token=access_token, verbose=global_verbose)
        check(resp, "error on LIST attachments")

        # POST attachment
        #   post attachment to the page                  
        print "test POST attachment",
        url  = 'http://api.springnote.com/pages/%d/attachments.json' % page_id
        data = open(__file__, 'rb') # i shall sacrifice myself for testing!
        resp = sn.springnote_request("POST", url, body=data, sign_token=access_token, verbose=global_verbose)
        data.close()
        check(resp, "error on POST attachment")
        attachment_id = parse_data(resp.read(), "identifier")

        # PUT attachment
        #  put attachment to the page
        print "test PUT attachment",
        url  = 'http://api.springnote.com/pages/%d/attachments/%d.json' % (page_id, attachment_id)
        data = open(__file__, 'rb') 
        resp = sn.springnote_request("PUT", url, body=data, sign_token=access_token, verbose=global_verbose)
        check(resp, "error on PUT attachment")

        # GET attachment
        #   get information about attachment
        print "test GET attachment",
        url  = 'http://api.springnote.com/pages/%d/attachments/%d.json' % (page_id, attachment_id)
        resp = sn.springnote_request("GET", url, sign_token=access_token, verbose=global_verbose)
        check(resp, "error on GET attachment")

        # DOWNLOAD attachment
        #   download attachment of the page              
        print "test DOWNLOAD attachment",
        url  = 'http://api.springnote.com/pages/%d/attachments/%d' % (page_id, attachment_id)
        resp = sn.springnote_request("GET", url, headers={}, sign_token=access_token, verbose=global_verbose)
        check(resp, "error on DOWNLOAD attachment")

        # DELETE attachment
        #   delete attachment to the page                
        print "test DELETE attachment",
        url  = 'http://api.springnote.com/pages/%d/attachments/%d.json' % (page_id, attachment_id)
        resp = sn.springnote_request("DELETE", url, sign_token=access_token, verbose=global_verbose)
        check(resp, "error on DELETE attachment")

        # DELETE page
        #   delete page                                  
        print "test DELETE page",
        url  = "http://api.springnote.com/pages/%d.json" % page_id
        resp = sn.springnote_request("DELETE", url, sign_token=access_token, verbose=global_verbose)
        check(resp, "error on DELETE page")

        # delete garbage pages
        print 'cleaning..',
        tag = 'springnote_oauthpy_integartion_test'
        params = {'tags': tag}
        url  = 'http://api.springnote.com/pages.json?tags=%s' % tag
        resp = sn.springnote_request("GET", url, params, sign_token=access_token, verbose=global_verbose)
        #del_page_id = parse_data(resp.read(), "identifier")

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
            sn.springnote_request("DELETE", url, sign_token=access_token, verbose=global_verbose)
        print "\tOK"

        print 
        print "done."


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '-v':
        global_verbose = True
    unittest.main()

