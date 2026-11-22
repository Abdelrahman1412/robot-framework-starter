*** Settings ***
Documentation    Leave-request flow: an employee asks, a manager decides, the employee sees the result.

Resource         ../../resources/pages/login_page.resource
Resource         ../../resources/pages/leave_page.resource
Resource         ../../resources/pages/approvals_page.resource
Resource         ../../resources/api/acme_api.resource

Suite Setup      Open Browser Session

Test Tags        ui    leave


*** Test Cases ***
Employee Submits A Leave Request
    [Tags]    smoke
    Given I Am Signed In As "employee"
    And I Open The Leave Page
    When I Request "annual" Leave From "2030-01-06" To "2030-01-08" Because "Family trip"
    ${id}=    Then The Request Should Be Submitted
    And My Request ${id} Should Have Status "pending"

Manager Approves A Request Created Through The API
    [Documentation]    Data setup goes through the API, so only the behaviour under test uses the UI.
    [Tags]    smoke
    ${leave}=    Given "employee" Requests Leave Via The API    reason=Dentist appointment
    And I Am Signed In As "manager"
    And I Open The Approvals Page
    And Request ${leave}[id] Should Be Waiting For Approval
    When I Approve Request ${leave}[id]
    Then Leave Request ${leave}[id] Should Have Status "approved" Via The API

Employee Sees The Manager's Decision
    [Tags]    regression
    ${leave}=    Given "employee" Requests Leave Via The API    type=sick    reason=Flu
    And "manager" Decides Leave Request ${leave}[id] As "rejected"
    When I Am Signed In As "employee"
    And I Open The Leave Page
    Then My Request ${leave}[id] Should Have Status "rejected"

End Date Before Start Date Is Rejected
    [Tags]    regression    negative
    Given I Am Signed In As "employee"
    And I Open The Leave Page
    When I Request "annual" Leave From "2030-02-10" To "2030-02-01" Because "Typo in dates"
    Then I Should See The Leave Error "End date cannot be before start date"
