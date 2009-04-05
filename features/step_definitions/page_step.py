# ----

def given_i_am_some_user():
    self.user = self.default_user

def given_has_a_default_note():
    self.note = self.default_note

def given_has_some_public_page():
    self.page_id = self.public_page_id

# ----

def when_i_read_some_public_page_of_my_default_note():
    self.page = Springnote.page(page_id)

def when_i_try_to_access_some_resource_in_springnote():
    self.empty_client.get_page(517652)

def when_i_did_not_authorize_myself():
    pass

# ----

def then_springnote_denies_my_request_trying_to_access_some_resource():
    client = Springnote()
    try:
        client.get_page(315672)
    except SpringnoteError.Unauthorized:
        pass
    else:
        raise Error
        

