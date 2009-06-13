from hamcrest.core.base_matcher import BaseMatcher
from hamcrest.core.internal.hasmethod import hasmethod

class IsEmpty(BaseMatcher):

    def _matches(self, item):
        if not hasmethod(item, '__len__'):
            return False
        return len(item) == 0

    def describe_to(self, description):
        description.append_text('an empty sequence')

empty = IsEmpty

