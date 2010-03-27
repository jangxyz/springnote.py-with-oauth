from hamcrest.core.base_matcher import BaseMatcher
from hamcrest.core.internal.hasmethod import hasmethod

##

class IsEmpty(BaseMatcher):
    def _matches(self, item):
        if not hasmethod(item, '__len__'):
            return False
        return len(item) == 0
    def describe_to(self, description):
        description.append_text('an empty sequence')
empty = IsEmpty

##

class RespondsTo(BaseMatcher):
    ''' an object responds to some attribute/method name '''
    def __init__(self, responder):
        self.responder = responder
    def _matches(self, item):
        #return self.responder in vars(item)
        return self.responder in dir(item)
    def describe_to(self, description):
        description.append_text("to respond to .%s" % self.responder)
responds_to = RespondsTo

##
import types
class IsInstanceOf(BaseMatcher):
    """ hack to hamcrest/core/core/isinstanceof.py """
    def __init__(self, the_class):
        if not (isinstance(the_class, type) or \
                isinstance(the_class, types.ClassType)):
            raise TypeError('IsInstanceOf requires type')
        self.the_class = the_class
    def _matches(self, item):
        return isinstance(item, self.the_class)
    def describe_to(self, description):
        description.append_text('an instance of ')          \
                    .append_text(self.the_class.__name__)
instance_of = IsInstanceOf  # Can use directly without a function.

