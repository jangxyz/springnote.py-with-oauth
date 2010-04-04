import os, sys
# ../
PATH    = os.path.dirname(__file__)
HOMEDIR = os.path.abspath(os.path.join(PATH, os.path.pardir))
LIBDIR  = os.path.abspath(os.path.join(PATH, 'lib'))
sys.path.append(HOMEDIR)
sys.path.append(LIBDIR)

# use unittest_decorator as unittest
import unittest_decorator # add @unittest.test decorators and such
sys.modules['unittest'] = sys.modules['unittest_decorator'] # override default unittest module

from pmock import Mock
import pmock
import springnote

class IsCalled(Exception): 
    pass
def should_call_class(object, class_name, when, arg=None):
    ''' mock out class_name under object to Calling class '''
    run = when
    called = []
    class Calling:
        def __init__(self, *args, **kwarg):
            if isinstance(arg, pmock.AbstractArgumentsMatcher):
                invocation = pmock.Invocation(class_name, args, kwarg)
                called.append(invocation)
                if arg.matches(invocation):
                    raise IsCalled()
                else:
                    msg = "got: " + str(invocation) + \
                        "\nexpected: method %s(%s)" % (class_name, arg)
                    raise AssertionError, msg
            else:
                raise IsCalled()

    # save
    orig = getattr(object, class_name)

    # patch
    setattr(object, class_name, Calling)
    for attr in dir(orig):
        if attr.startswith('__'): continue
        the_value = getattr(orig, attr)
        setattr(getattr(object, class_name), attr, the_value)

    # test
    try:
        # run
        run()
        # shouldn't reach here
        if isinstance(arg, pmock.AbstractArgumentsMatcher):
            msg = "\n".join(map(str, called)) + "\nhave been called, but " \
                "method %s(%s) is not called" % (class_name, arg)
            raise AssertionError, msg
        else:
            raise AssertionError, "method %s is not called" % class_name
    # verify
    except IsCalled:
        pass
    # restore
    finally:
        setattr(object, class_name, orig)

def should_call_method(object, method_name, when, method_type=None, arg=None, returns=None):
    callable = when
    called = []
    def is_called(*args, **kwarg): 
        if isinstance(arg, pmock.AbstractArgumentsMatcher):
            invocation = pmock.Invocation(method_name, args, kwarg)
            called.append(invocation)
            if arg.matches(invocation):
                raise IsCalled()
            else:
                msg = "got: " + str(invocation) + \
                    "\nexpected: method %s(%s)" % (method_name, arg)
                raise AssertionError, msg
        else:
            raise IsCalled()

    # set staticmethod or classmethod, if given
    if method_type is not None: 
        is_called = method_type(is_called)

    # save
    orig = getattr(object, method_name)
    #if method_type is not None: 
    #    orig = method_type(orig)

    # patch
    setattr(object, method_name, is_called)

    # test
    try: 
        callable()
        # should not reach here
        if isinstance(arg, pmock.AbstractArgumentsMatcher):
            msg = "got: " + "\n".join(map(str, called)) + \
                "\nexpected: method %s(%s)" % (method_name, arg)
            raise AssertionError, msg
        else:
            raise AssertionError, "method %s is not called" % method_name
    except IsCalled:    # verify
        pass
    finally:            # restore
        setattr(object, method_name, orig)

def should_not_call_method(object, method_name, when, method_type=None, arg=None):
    # save
    orig = getattr(object, method_name)
    if method_type is not None: 
        orig = method_type(orig)

    try:
        should_call_method(object, method_name, when, method_type, arg)
        raise AssertionError, "method %s is called" % method_name
    except AssertionError: pass
    except:
        pass
    finally:    # restore
        setattr(object, method_name, orig)

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

# callabla Mock
class CMock(Mock):
    def __init__(self, *arg, **kwarg): 
        Mock.__init__(self, `(arg, kwarg)`)
    def __call__(self, *arg, **kwarg): return self

def mock_class_Springnote():
    global original_class_Springnote
    # patch
    original_class_Springnote = springnote.Springnote
    host = springnote.HOST

    # mock
    springnote.Springnote = CMock()
    springnote.HOST = host

    return springnote.Springnote

def restore_class_Springnote():
    springnote.Springnote = original_class_Springnote
    return springnote.Springnote

def mock_class_SpringnoteResource():
    global original_sn_rsrc
    # don't use SpringnoteResource._build_model_from_response
    original_sn_rsrc = springnote.SpringnoteResource
    def stub__build_model_from_response(self, *args, **kwargs):
        pass
    springnote.SpringnoteResource._build_model_from_response = stub__build_model_from_response
    return springnote.SpringnoteResource

def restore_class_SpringnoteResource():
    springnote.SpringnoteResource = original_sn_rsrc
    return springnote.SpringnoteResource

def mock_class_Page():
    global original_page
    original_page = springnote.Page
    springnote.Page = CMock()
    return springnote.Page
def restore_class_Page():
    springnote.Page = original_page
    return springnote.Page


