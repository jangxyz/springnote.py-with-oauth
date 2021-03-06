#!/usr/bin/python

"""
    pmock extension
"""

##############################################################################
# Argument constraints
############################################################################## 

class DictionarySubsetConstraint(object):
    def __init__(self, expected):
        self._expected = expected
    def __repr__(self):
        return "%s.dict_including(%s)" % (__name__, repr(self._expected))
    def eval(self, arg):
        for key, value in self._expected.iteritems():
            if key not in arg or arg[key] != value:
                return False
        return True

def dict_including(expected):
    return DictionarySubsetConstraint(expected)


##
##

class DictionaryNotContainsValueConstraint(object):
    def __init__(self, expected):
        self._expected = expected
    def __repr__(self):
        return "%s.contains_value(%s)" % (__name__, repr(self._expected))
    def eval(self, arg):
        return self._expected not in arg.values()

def not_contains_value(expected):
    return DictionaryNotContainsValueConstraint(expected)

##
##

import types, re
class StringContainsConstraint(object):
    ''' patch of StringcontainsConstraint to accept regex '''
    def __init__(self, expected):
        self._expected = expected
    def __repr__(self):
        return "%s.string_contains(%s)" % (__name__, repr(self._expected))
    def eval(self, arg):
        if arg is None:
            return False
        # string
        elif isinstance(self._expected, types.StringType):
            return arg.find(self._expected) != -1
        # regex
        elif isinstance(self._expected, re._pattern_type):
            return self._expected.search(arg) is not None
        else:
            return False

def string_contains(expected):
    return StringContainsConstraint(expected)

##
##

class StringNotContainsConstraint(StringContainsConstraint):
    def __repr__(self):
        return "%s.string_not_contains(%s)" % (__name__, repr(self._expected))
    def eval(self, arg):
        return not StringContainsConstraint.eval(self, arg)

def string_not_contains(expected):
    return StringNotContainsConstraint(expected)

##
##

from pmock import LeastArgumentsMatcher, AllArgumentsMatcher
def with_at_least(*arg_constraints, **kwarg_constraints):
    """Specify the method's minimum required arguments."""
    return LeastArgumentsMatcher(arg_constraints, kwarg_constraints)

def with_(*arg_constraints, **kwarg_constraints):
    """Fully specify the method's arguments."""
    return AllArgumentsMatcher(arg_constraints, kwarg_constraints)
