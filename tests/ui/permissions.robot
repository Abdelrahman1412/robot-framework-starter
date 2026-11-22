*** Settings ***
Documentation    Role-based access: what each role can see and open.

Resource         ../../resources/pages/login_page.resource
Resource         ../../resources/pages/dashboard_page.resource

Suite Setup      Open Browser Session

Test Tags        ui    permissions


*** Test Cases ***
Employee Does Not See Approvals In The Navigation
    [Tags]    smoke
    Given I Am Signed In As "employee"
    Then The Navigation Should Not Show "approvals"
    And The Navigation Should Not Show "admin"

Employee Cannot Open The Approvals Page Directly
    [Tags]    smoke    negative
    Given I Am Signed In As "employee"
    When I Open The Page "/approvals"
    Then I Should See Access Denied

Manager Cannot Open User Administration
    [Tags]    regression    negative
    Given I Am Signed In As "manager"
    Then The Navigation Should Show "approvals"
    And The Navigation Should Not Show "admin"
    When I Open The Page "/admin/users"
    Then I Should See Access Denied

Admin Can Open User Administration
    [Tags]    regression
    Given I Am Signed In As "admin"
    When I Open The Page "/admin/users"
    Then Get Element Count    css=[data-testid=users-table] tr    ==    3
