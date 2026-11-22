*** Settings ***
Documentation    Sign-in for every role, and the wrong-password path.

Resource         ../../resources/pages/login_page.resource
Resource         ../../resources/pages/dashboard_page.resource

Suite Setup      Open Browser Session

Test Tags        ui    login


*** Test Cases ***
Employee Can Sign In
    [Tags]    smoke
    Given I Open The Login Page
    When I Sign In As "employee"
    Then I Should Land On The Dashboard As "employee"

Manager Can Sign In
    [Tags]    smoke
    Given I Open The Login Page
    When I Sign In As "manager"
    Then I Should Land On The Dashboard As "manager"

Admin Can Sign In
    [Tags]    regression
    Given I Open The Login Page
    When I Sign In As "admin"
    Then I Should Land On The Dashboard As "admin"

Wrong Password Is Rejected
    [Tags]    smoke    negative
    Given I Open The Login Page
    When I Sign In With Username "emma" And Password "not-the-password"
    Then I Should See The Login Error "Invalid username or password"

Saved Storage State Skips The Login Form
    [Documentation]    The second context reuses cookies saved by the first sign-in.
    [Tags]    regression
    Given I Am Signed In As "manager"
    Then I Should Land On The Dashboard As "manager"
