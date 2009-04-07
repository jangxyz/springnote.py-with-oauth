Feature: Initializing Springnote

So that I can use springnote library as I want,
As a user of the library
I want to initialize it in various ways

Scenario: Initializing Springnote with default options

  Given a springnote instance initialized with no arguments
  And   the instance should not be authorized
  And   the consumer token of the instance should set to default
  And   the instance should show the url to authorize


Scenario: Initializing Springnote other consumer token

  Given another consumer token for another application
  When I initialize springnote with ('abc', 'def')
  Then the consumer token of Springnote is ('abc', 'def')


