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

    +---------------+------+-----+------+-----+--------+
    |               | LIST | GET | POST | PUT | DELETE |
    +---------------+------+-----+------+-----+--------+
    | Page          |  o   |  o  |  o   |  o  |   o    |
    | Attachments   |  o   |  o  |  o   |  o  |   o    |
    | Revisions     |  o   |  o  |  -   |  -  |   -    |
    | Comments      |  o   |  -  |  -   |  -  |   -    |
    | Collaboration |  o   |  -  |  -   |  -  |   -    |
    | Lock          |  -   |  o  |  o   |  -  |   -    |
    +---------------+------+-----+------+-----+--------+

"""

import sys, pprint, os
from springnote import Springnote, Page, Attachment

def usage(verbose=False):
    print "%s is a simple program to see how the library works." % sys.argv[0]
    print
    print "  Usage:", sys.argv[0], '[options]', 'method', 'page [page_id [resource [resource_id]]]'
    print
    print ' * options: --dry | --verbose | --access-token ACCESS_TOKEN:ACCESS_KEY'
    print ' * method: get | put | post | delete'
    print ' * resource: page | attachment | revision | comment | collaboration | lock'
    print
    print ' ex1)', sys.argv[0], '--verbose', 'get', 'page',    '                  # see every pages of default note'
    print ' ex2)', sys.argv[0], 'get', 'page', 123, 'attachment', 456,  '         # download attachment 456 of page 123'
    print ' ex3)', sys.argv[0], 'post', 'page', 'test', '"the contents in it" ', '# a bit different format here'
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
    ''' parse user input and figure out method, resource, and additional parameters '''
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

    if not verbose: 
        sys.stderr.write("you can see more detailed information with --verbose option\n\n")
    if len(argv) < 2: # tell me what to do!
        usage(verbose)
        sys.exit()

    method    = argv[0].upper()                         # GET
    page_rsrc = argv[1].rstrip('s').lower()             # page(s)
    page_id, resource, resource_id = None, None, None
    if len(argv) >= 3: page_id = argv[2]                # 123

    if method not in _w("GET PUT POST DELETE"):
        sys.exit("ERROR: don't know method %s" % method)

    if len(argv) >= 4: resource    = argv[3]            # attachment
    if len(argv) >= 5: resource_id = argv[4]            # 456

    # must be pure PAGE, with other methods than GET
    other_resources = _w("attachment revision comment collaboration lock")
    if resource not in other_resources:
        # the only case where there is other resource than page_id
        if page_id and method is not "POST":
            page_id = int(page_id)
        return access_token, method, page_id, None, None, verbose, argv
    page_id = int(page_id)

    # arguments used for resource other than page
    if resource:    
        resource = resource.rstrip('s').lower()
        if resource not in _w('lock collaboration'):
            resource += 's'

    # POST attachment gives filename in resource_id slot
    if method == "POST" and resource == "attachments": pass
    elif resource_id:   
        resource_id = int(resource_id)

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


def handle_page_resource(sn, method, page_id, verbose, argv):
    ''' some ways to play with page resource 
    
    note the possible styles handling each request.
     - LIST:   Page.list(sn)
     - GET:    Page(sn, id=page_id)).get()
     - POST:   Page(sn, title=title, source=source, tags="example_py").save()
     - PUT:    sn.save_page(id=page_id, title=title, source=source)
    '''
    ## GET page 123
    if method == 'GET' and page_id:
        page = Page(sn, id=page_id).get(verbose=verbose)
        pprint.pprint(page.resource)
        print "page '%(title)s'(#%(identifier)d), last updated at %(date_modified)s" % page.resource
    ## GET pages
    elif method == 'GET' and not page_id:
        pages   = Page.list(sn, verbose=verbose)
        first_p = filter(lambda x: x.relation_is_part_of is None, pages)[0]
        last_p  = max(pages, key=lambda x: x.date_modified)
        print "has", len(pages), 'pages,',
        print "from '%s'(#%d) to '%s'(#%d)" % (first_p.title, first_p.identifier, last_p.title, last_p.identifier)
        print "i'm not gonna show ALL the pages for ya"
    ## POST page
    elif method == "POST":
        title, source = None, None
        if len(argv) >= 3:  title  = argv[2]
        if len(argv) >= 4:  source = argv[3]
        if title:
            page = Page(sn, title=title, source=source, tags="example_py")
            page.save(verbose=verbose)
            pprint.pprint(page.resource)
            print "created page '%(title)s'(#%(identifier)d) at %(date_created)s" % page.resource
            print "content:", page.source
    ## PUT page 123
    elif method == "PUT":  
        title, source = None, None
        if len(argv) >= 4:  title  = argv[3]
        if len(argv) >= 5:  source = argv[4]
        if not page_id:
            sys.exit("I need to know which page you want to edit.")
        if title:
            page = sn.save_page(id=page_id, title=title, source=source, verbose=verbose)
            pprint.pprint(page.resource)
            print "updated page '%(title)s'(#%(identifier)d) at %(date_created)s" % page.resource
            print "content:", page.source
    ## DELETE page
    elif method == "DELETE":
        print "c'mon now, this is just a tutorial program. :p"

def handle_attachment_resource(sn, method, page_id, verbose, resource_id, argv):
    ''' shows a few ways handling attahcment resources, with page_id and resource_id.

    note the possible styles handling each request.
     - LIST:   Page(sn, id=page_id).list_attachments()
     - GET:    Attachment(Page(sn, id=page_id), id=resource_id).get().download()
     - POST:   Attachment(Page(sn, id=page_id), filename=filename, file=file_obj).upload()
     - PUT:    Attachment(Page(sn, id=page_id), id=resource_id, file=file_obj).upload()
     - DELETE: Page(sn, id=page_id).delete_attachment(resource_id)
    '''
    ## DOWNLOAD attchment
    if method == 'GET' and resource_id:
        page   = Page(sn, id=page_id)   # just initializing, no need to fetch
        attach = Attachment(page, id=resource_id)
        attach.get(verbose=verbose)         # this retrieves metadata, such as filename
        attach.download(verbose=verbose)    # this downloads actual file content
        pprint.pprint(attach.resource)
        print 'saving to', attach.title, '..'

        if os.path.exists(filename):
            print 'filename already exists! abort saving file'
        else:
            file = open(attach.title, 'rw')
            file.write(attach.raw)
            file.close()

    ## LIST attchments
    if method == 'GET' and not resource_id:
        page = Page(sn, id=page_id).get() # fetch page, just curious
        attachments = page.list_attachments(verbose=verbose)
        print 'found', len(attachments), "files under '%(title)s'(#%(identifier)d)" % page.resource
        for attach in attachments:
            print ' - %(title), %(description) bytes' % attach.resource
            
    ## POST atatchment
    elif method == "POST":
        filename = resource_id # resource_id slot has filename to upload
        file_obj = open(filename, 'rb')

        # DON'T HAVE TO give a page object, relation_is_part_of will do.
        page   = Page(sn, id=page_id)   # no fetch, just holding page_id
        attach = Attachment(page, filename=filename, file=file_obj)
        attach.upload(verbose=verbose)
        pprint.pprint(attach.resource)
        print "created '%(title)s' (#%(identifier)d), %(description)d bytes under %(relation_is_part_of)d" % attach.resource
        file_obj.close()

    ## PUT attachment
    elif method == "PUT":
        filename = argv[5]  # you need the resource_id
        file_obj = open(filename, 'rb')

        page   = Page(sn, id=page_id)   # no fetch, just holding page_id
        attach = Attachment(page, id=resource_id, file=file_obj) # knows filename
        attach.upload(verbose=verbose)
        print "updated '%(title)s' (#%(identifier)d), %(description)d bytes under %(relation_is_part_of)d" % attach.resource
        file_obj.close()

    ## DELETE attachment
    elif method == "DELETE":
        page = Page(sn, id=page_id)
        attach = page.delete_attachment(resource_id, verbose=verbose)
        print "deleted file '%(title)s'" % attach.resource

def main():
    # parse options
    args = parse(sys.argv[1:])
    access_token, method, page_id, resource, resource_id, verbose, argv = args

    print method, 'page', page_id or '', resource or '', resource_id or ''
    sn = Springnote()
    ## Authorize
    if access_token: # use given access token
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

    if resource is None:
        handle_page_resource(sn, method, page_id, verbose, argv)
    elif resource == 'attachments':
        handle_attachment_resource(sn, method, page_id, verbose, resource_id, argv)
    # the rest.. in simple springnote_request style
    else:
        if resource_id:  path = '/pages/%d/%s/%d.json' % (page_id, resource, resource_id)
        else:            path = '/pages/%d/%s.json'    % (page_id, resource)
        url = 'http://api.springnote.com/' + path.lstrip('/')
        print method, url

        # response
        http_response = sn.springnote_request(method, url, verbose=verbose)
        pprint.pprint(http_response.read())
        print http_response.status
    print

if __name__ == '__main__':
    main()

