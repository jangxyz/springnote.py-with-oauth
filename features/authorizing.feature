Feature: Telling springnote who I am

So that I can use resources in Springnote
As a springnote user
I want to authorize myself

Scenario: Springnote denies access without any authorization

  Given I am some user
  When I did not authorize myself
  Then Springnote denies my request trying to access some resource


Scenario: springnote asks me for authorization first

