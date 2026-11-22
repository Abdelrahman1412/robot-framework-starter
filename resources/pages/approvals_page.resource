*** Settings ***
Documentation    Approvals page keywords (manager and admin view).

Resource         ../common.resource


*** Keywords ***
I Open The Approvals Page
    Go To    ${BASE_URL}/approvals
    Get Title    ==    Approvals | Acme HR

Request ${id} Should Be Waiting For Approval
    Get Text    data-testid=leave-status-${id}    ==    pending

I Approve Request ${id}
    Click    data-testid=approve-${id}
    Get Element Count    data-testid=leave-row-${id}    ==    0

I Reject Request ${id}
    Click    data-testid=reject-${id}
    Get Element Count    data-testid=leave-row-${id}    ==    0
