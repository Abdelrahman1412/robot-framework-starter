*** Settings ***
Documentation     Optional: proves API writes reach the database. Skipped by ``--exclude db``.

Resource          ../../resources/api/acme_api.resource
Resource          ../../resources/db/acme_db.resource

Suite Setup       I Connect To The Acme HR Database
Suite Teardown    Disconnect From All Databases

Test Tags         db


*** Test Cases ***
Approved Leave Is Persisted
    [Tags]    regression
    ${leave}=    Given "employee" Requests Leave Via The API
    And Leave Request ${leave}[id] Should Be Stored With Status "pending"
    And An API Session For "manager"
    When "manager" Decides Leave Request ${leave}[id] As "approved"
    Then Leave Request ${leave}[id] Should Be Stored With Status "approved"
