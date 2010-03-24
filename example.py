#/usr/bin/python
# -*- coding: utf-8 -*-

"""

    Example program using Springnote API library

    you can try:
      * list, read, update, create, delete page
      * list, download, update, upload, delete attachment of a page
      * get/list revisions of page
      * get/list comments of page
      * get list of collaborations of page
      * read, write lock of page

    +----------------+------+-----+------+-----+--------+
    |                | LIST | GET | POST | PUT | DELETE |
    +----------------+------+-----+------+-----+--------+
    | Page           |  o   |  o  |  o   |  o  |   o    |
    | Attachments    |  o   |  o  |  o   |  o  |   o    |
    | Revisions      |  o   |  o  |  -   |  -  |   -    |
    | Comments       |  o   |  -  |  -   |  -  |   -    |
    | Collaborations |  o   |  -  |  -   |  -  |   -    |
    | Lock           |  -   |  o  |  o   |  -  |   -    |
    +----------------+------+-----+------+-----+--------+

"""

import sys, pprint
from springnote import Springnote, Page

def usage(verbose=False):
    print "%s is a simple program to see how the library works." % sys.argv[0]
    print
    print "  Usage:", sys.argv[0], '[options]', 'method', 'page [page_id [resource [resource_id]]]'
    print
    print ' ex1)', sys.argv[0], '--verbose', 'get', 'page',    '                  # see every pages of default note'
    print ' ex2)', sys.argv[0], 'get', 'page', 123, 'attachment', 456,  '         # download attachment 456 of page 123'
    print ' ex3)', sys.argv[0], 'post', 'page', 'test', '"the contents in it" ', '# a bit different format here'
    print
    print ' * options: --dry | --verbose | --access-token ACCESS_TOKEN:ACCESS_KEY'
    print ' * method: get | put | post | delete'
    print ' * resource: page | attachment | revision | comment | collaboration | lock'
    print 
    if verbose:
        print '''
    +----------------+------+-----+------+-----+--------+
    |                | LIST | GET | POST | PUT | DELETE |
    +----------------+------+-----+------+-----+--------+
    | Pages          |  o   |  o  |  o   |  o  |   o    |
    | Attachments    |  o   |  o  |  o   |  o  |   o    |
    | Revisions      |  o   |  o  |  -   |  -  |   -    |
    | Comments       |  o   |  -  |  -   |  -  |   -    |
    | Collaborations |  o   |  -  |  -   |  -  |   -    |
    | Lock           |  -   |  o  |  o   |  -  |   -    |
    +----------------+------+-----+------+-----+--------+
        '''

def _w(s):
    return s.split()

def parse(argv):
    verbose = False
    access_token = None
    for argument in argv[:]:
        if argument == '--dry':
            global default_dry_run
            default_dry_run = True
            argv.pop(0)
        elif argument == '--access-token': # format 'keykeykey:secretsecret'
            argv.pop(0)
            access_token = argv.pop(0).split(':')
        elif argument == '--verbose':
            verbose = True
            argv.pop(0)

    if len(argv) < 2: # tell me what to do!
        usage(verbose)
        sys.exit()

    # --verbose if you want to see more
    if not verbose: 
        sys.stderr.write("you can see more detailed information with --verbose option\n\n")

    method        = argv[0].upper()                 # GET
    page_rsrc     = argv[1].rstrip('s').lower()     # page(s)
    page_id, resource, resource_id = None, None, None
    if len(argv) >= 3: page_id = argv[2]            # 123

    if method not in _w("GET PUT POST DELETE"):
        sys.exit("ERROR: don't know method %s" % method)

    if len(argv) >= 4: resource    = argv[3]  # attachment
    if len(argv) >= 5: resource_id = argv[4]  # 456

    other_resources = _w("attachment revision comment collaboration lock")
    # must be pure PAGE, with other methods than GET
    if resource not in other_resources:
        # the only case where there is other resource than page_id
        if method is not "POST":
            page_id = int(page_id)
        return access_token, method, page_id, None, None, verbose, argv
    page_id = int(page_id)

    # arguments used for resource other than page
    if resource:    resource = resource.rstrip('s').lower()   # attachment
    if resource_id: resource_id = int(resource_id)            # 456

    # mend resource name a bit
    if resource and resource not in 'lock collaboration'.split():
        resource += 's'

    return access_token, method, page_id, resource, resource_id, verbose, argv


def auth(sn, verbose):
    print 'going through authorization...'
    # 1. receive a request token
    request_token = sn.fetch_request_token(verbose=verbose)
    print 'request token received:', (request_token.key, request_token.secret)

    # 2. user approves the request token
    print 'go to this url and approve:', sn.authorize_url(request_token)
    raw_input('Press enter when complete. ')

    # 3. receive access token -> saved inside sn
    access_token = sn.fetch_access_token(request_token, verbose=verbose)
    return sn


def main():
    # parse options
    args = parse(sys.argv[1:])
    access_token, method, page_id, resource, resource_id, verbose, argv = args

    print method, 'page', page_id or '', resource or '', resource_id or ''
    sn = Springnote()
    ## Authorize
    if access_token:
        sn.set_access_token(*access_token)
    else:
        # go through authorization process
        sn = auth(sn, verbose)
        access_token = sn.access_token
        access_token_option = '--access-token %s:%s' % (access_token.key, access_token.secret)
        print 'your access token is ', (access_token.key, access_token.secret)
        print 'you can save it somewhere else and reuse it later like this:'
        print ' ', sys.argv[0], access_token_option, method, 'page', page_id or '', resource or '', resource_id or ''
        print

    ## Request resource
    if resource is None: # Page
        if method == 'GET':
            if page_id: ## GET page 123
                page = Page(sn, id=page_id).get(verbose=verbose)
                pprint.pprint(page.resource)
                print "got page '%s'(#%d), last updated at %s" % (page.title, page.identifier, page.date_modified)
            else:       ## GET pages
                pages = Page.list(sn, verbose=verbose)
                first_p = filter(lambda x: x.relation_is_part_of is None, pages)[0]
                last_p  = max(pages, key=lambda x: x.date_modified)
                print "got", len(pages), 'pages,',
                print "from '%s'(#%d) to '%s'(#%d)" % (first_p.title, first_p.identifier, last_p.title, last_p.identifier)
                print "not gonna show ALL the pages for ya"
        elif method == "DELETE":
            print "c'mon now, this is just a tutorial program. :p"
        else:
            title, source = None, None
            if method == "POST": ## POST page
                if len(argv) >= 3:  title  = argv[2]
                if len(argv) >= 4:  source = argv[3]
                if title:
                    page = Page(sn, title=title, source=source)
                    page.save()
                    print "created page '%s'(#%d) at %s" % (page.title, page.id, page.date_created)
                    print "content:", page.source
            elif method == "PUT":  ## PUT page 123
                if len(argv) >= 4:  title  = argv[3]
                if len(argv) >= 5:  source = argv[4]
                if not page_id:
                    sys.exit("I need to know which page you want to edit.")
                if title:
                    page = Page(sn, id=page_id, title=title, source=source)
                    page.save()
                    print "updated page '%s'(#%d) at %s" % (page.title, page.id, page.date_created)
                    print "content:", page.source
        return

    # other resources
    if resource_id:  path = '/%s/%d.json' % (resource, resource_id)
    else:            path = '/%s.json'    % resource
    # downloading attachment omits extension .json 
    if resource == 'attachments' and resource_id:
        path = path[:-5]
    url = 'http://api.springnote.com/pages/%d%s' % (page_id, path)
    print method, url

    # status
    http_response = sn.springnote_request(method, url, verbose=verbose)
    # save downloaded file
    is_downloading = resource == 'attachment' and method == "GET" and resource_id
    if not is_downloading:
        http_response.read()
    else:
        f = open('download', 'wb')
        f.write(http_response.read())
        f.close()
        print "saved file to 'download'"
    print  http_response.status
    return http_response.status

if __name__ == '__main__':
    main()
    print

