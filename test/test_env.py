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

def should_call_method(object, method_name, when, method_type=None, arg=None):
    callable = when
    class IsCalled(Exception): 
        pass
    def is_called(*args, **kwarg): 
        if isinstance(arg, pmock.AbstractArgumentsMatcher):
            invocation = pmock.Invocation(method_name, args, kwarg)
            if arg.matches(invocation):
                raise IsCalled()
        else:
            raise IsCalled()

    # set staticmethod or classmethod, if given
    if method_type is not None: 
        is_called = method_type(is_called)

    # save
    orig = getattr(object, method_name)
    if method_type is not None: 
        orig = method_type(orig)

    # patch
    setattr(object, method_name, is_called)

    # test
    try:                # run
        callable()
        if isinstance(arg, pmock.AbstractArgumentsMatcher):
            raise AssertionError, "method %s(%s) is not called" % (method_name, arg)
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
    global original_sn
    # patch
    original_sn = springnote.Springnote
    host = springnote.HOST

    # mock
    springnote.Springnote = CMock()
    springnote.HOST = host

    return springnote.Springnote

def restore_class_Springnote():
    springnote.Springnote = original_sn
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

def restore_class_Page():
    springnote.Page = original_page

