*** Settings ***
Documentation    Leave-request API: contract (JSON Schema), permissions and error handling.

Resource         ../../resources/api/acme_api.resource

Test Tags        api


*** Test Cases ***
Created Leave Request Matches The Schema
    [Tags]    smoke
    ${leave}=    "employee" Requests Leave Via The API    type=annual    start=2030-05-04    end=2030-05-08
    Response Should Match Schema    ${leave}    leave_request
    Should Be Equal    ${leave}[status]    pending
    Should Be Equal As Integers    ${leave}[days]    5

Leave List Matches The Schema And Is Scoped To The Employee
    [Tags]    regression
    "employee" Requests Leave Via The API
    ${response}=    GET On Session    employee    /leave-requests    expected_status=200
    Response Should Match Schema    ${response.json()}    leave_request_list
    FOR    ${item}    IN    @{response.json()}[items]
        Should Be Equal    ${item}[employee]    ${USERS}[employee][username]
    END

Manager Approves Through The API
    [Tags]    smoke
    ${leave}=    "employee" Requests Leave Via The API
    An API Session For "manager"
    ${response}=    "manager" Decides Leave Request ${leave}[id] As "approved"
    Response Should Match Schema    ${response.json()}    leave_request
    Should Be Equal    ${response.json()}[decidedBy]    ${USERS}[manager][username]

Employee Cannot Approve Leave
    [Tags]    smoke    negative    permissions
    ${leave}=    "employee" Requests Leave Via The API
    ${response}=    "employee" Decides Leave Request ${leave}[id] As "approved"    expected_status=403
    Response Should Match Schema    ${response.json()}    error
    Should Be Equal    ${response.json()}[error]    forbidden

A Decided Request Cannot Be Decided Again
    [Tags]    regression    negative
    ${leave}=    "employee" Requests Leave Via The API
    An API Session For "manager"
    "manager" Decides Leave Request ${leave}[id] As "approved"
    ${response}=    "manager" Decides Leave Request ${leave}[id] As "rejected"    expected_status=409
    Should Be Equal    ${response.json()}[error]    conflict

Invalid Leave Request Is Rejected With 422
    [Tags]    regression    negative
    An API Session For "employee"
    VAR    &{body}    type=holiday    startDate=2030-01-01    endDate=2030-01-02    reason=x
    ${response}=    POST On Session    employee    /leave-requests    json=${body}    expected_status=422
    Response Should Match Schema    ${response.json()}    error
    Should Contain    ${response.json()}[message]    Leave type must be one of

Requests Without A Token Are Unauthorized
    [Tags]    smoke    negative
    ${response}=    GET    ${API_URL}/leave-requests    expected_status=401
    Response Should Match Schema    ${response.json()}    error

Wrong Password Returns 401
    [Tags]    regression    negative
    VAR    &{body}    username=${USERS}[employee][username]    password=wrong
    ${response}=    POST    ${API_URL}/auth/login    json=${body}    expected_status=401
    Should Be Equal    ${response.json()}[error]    invalid_credentials
