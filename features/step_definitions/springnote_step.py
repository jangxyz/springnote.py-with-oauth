import sys, os; sys.path.append(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir))
import springnote
import types

def given_another_consumer_token_for_another_application():
    pass # nothing to implement

def given_a_springnote_instance_initialized_with_no_arguments():
    self.springnote = springnote.Springnote()

def given_the_instance_should_not_be_authorized():
    assert self.springnote.is_authorized() == False

def given_the_consumer_token_of_the_instance_should_set_to_default():
    token = self.springnote.consumer_token 
    assert token.key == springnote.CONSUMER_TOKEN_KEY
    assert token.secret == springnote.CONSUMER_TOKEN_SECRET

def given_the_instance_should_fetch_request_token():
    self.request_token = self.springnote.fetch_request_token()
    assert isinstance(self.request_token.key, types.StringType)
    assert isinstance(self.request_token.secret, types.StringType)

def given_the_instance_should_show_the_url_to_authorize():
    url = self.springnote.authorize_url(self.request_token)
    assert springnote.AUTHORIZATION_URL in url
    

# ------------------------------------------------------------
def when_i_initialize_springnote_with_abc_def_():
    self.springnote = springnote.Springnote(("abc", "def"))
    
# ------------------------------------------------------------

def then_the_consumer_token_of_springnote_is_abc_def_():
    assert self.springnote.consumer_token == ("abc", "def")

