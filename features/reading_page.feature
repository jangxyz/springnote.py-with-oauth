So that I can read content of springnote
As a springnote user
I want to read the content of specific page


Scenario: Reading public page of my default note

  Given I am some user
  And has a default note
  And has some public page
  
  When I read some public page of my default note

  Then I can read its content


Scenario: Reading private page of my default note

Scenario: Reading public page of my non-default note

Scenario: Reading private page of my non-default note

Scenario: Reading someone else's public page

Scenario: Reading someone else's private page


