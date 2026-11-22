*** Settings ***
Documentation    Dashboard and navigation keywords.

Resource         ../common.resource


*** Keywords ***
I Should Land On The Dashboard As "${role}"
    Get Url    *=    /dashboard
    Get Text    data-testid=role    ==    ${role}
    Get Text    data-testid=welcome    *=    Welcome

The Navigation Should Show "${link}"
    Get Element States    data-testid=nav-${link}    contains    visible

The Navigation Should Not Show "${link}"
    Get Element Count    data-testid=nav-${link}    ==    0

I Open The Page "${path}"
    Go To    ${BASE_URL}${path}

I Should See Access Denied
    Get Text    data-testid=access-denied    ==    Access denied
