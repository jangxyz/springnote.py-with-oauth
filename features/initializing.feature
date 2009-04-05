Feature: Initializing Springnote

So that I can use springnote library as I want,
As a user of the library
I want to initialize it in various ways

Scenario: Initializing Springnote with default options

  When I initialize springnote with nothing
  Then the comsumer token of Springnote is set to default


