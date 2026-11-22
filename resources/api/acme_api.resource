*** Settings ***
Documentation    API keywords for the Acme HR JSON API (RequestsLibrary), also used for test data setup.

Library          RequestsLibrary
Library          ../../libraries/SchemaLibrary.py
Resource         ../common.resource


*** Keywords ***
An API Session For "${role}"
    [Documentation]    Logs in through the API and opens a RequestsLibrary session named after the role.
    ...    Credentials are kept out of the log.
    ${previous}=    Set Log Level    NONE
    TRY
        VAR    &{body}    username=${USERS}[${role}][username]    password=${USERS}[${role}][password]
        ${response}=    POST    ${API_URL}/auth/login    json=${body}    expected_status=200
    FINALLY
        Set Log Level    ${previous}
    END
    Response Should Match Schema    ${response.json()}    login_response
    VAR    &{headers}    Authorization=Bearer ${response.json()}[token]
    Create Session    ${role}    ${API_URL}    headers=${headers}    disable_warnings=1

"${role}" Requests Leave Via The API
    [Documentation]    Data setup shortcut: creates a pending leave request and returns its JSON.
    [Arguments]    ${type}=annual    ${start}=2030-03-02    ${end}=2030-03-04    ${reason}=Created by API setup
    An API Session For "${role}"
    VAR    &{body}    type=${type}    startDate=${start}    endDate=${end}    reason=${reason}
    ${response}=    POST On Session    ${role}    /leave-requests    json=${body}    expected_status=201
    RETURN    ${response.json()}

"${role}" Decides Leave Request ${id} As "${decision}"
    [Arguments]    ${expected_status}=200
    VAR    &{body}    decision=${decision}
    ${response}=    POST On Session    ${role}    /leave-requests/${id}/decision    json=${body}
    ...    expected_status=${expected_status}
    RETURN    ${response}

Leave Request ${id} Should Have Status "${status}" Via The API
    An API Session For "manager"
    ${response}=    GET On Session    manager    /leave-requests/${id}    expected_status=200
    Should Be Equal    ${response.json()}[status]    ${status}
