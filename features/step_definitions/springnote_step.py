import sys, os; sys.path.append(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir))
import springnote

def when_i_initialize_springnote_with_nothing():
    self.springnote = springnote.Springnote()
    
def then_the_consumer_token_of_springnote_is_set_to_default():
    self.springnote.consumer_token

