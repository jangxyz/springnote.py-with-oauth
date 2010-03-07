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


