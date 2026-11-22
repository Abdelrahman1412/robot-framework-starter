*** Settings ***
Documentation    Login page keywords and multi-role sign-in with saved storage state.

Resource         ../common.resource


*** Keywords ***
I Open The Login Page
    New Context    baseURL=${BASE_URL}
    New Page    ${BASE_URL}/login
    Get Title    ==    Sign in | Acme HR

I Sign In As "${role}"
    Submit Login Form    ${USERS}[${role}][username]    ${USERS}[${role}][password]

I Sign In With Username "${username}" And Password "${password}"
    Submit Login Form    ${username}    ${password}

I Should See The Login Error "${message}"
    Get Text    data-testid=login-error    ==    ${message}
    Get Url    *=    /login

I Am Signed In As "${role}"
    [Documentation]    Opens a context that is already signed in as ``role``, reusing saved storage state.
    ...    The real UI login happens once per role per run, even across pabot processes.
    Run Only Once    Save Storage State For Role    ${role}
    New Context    baseURL=${BASE_URL}    storageState=${EXECDIR}/${AUTH_DIR}/${role}.json
    New Page    ${BASE_URL}/dashboard

Save Storage State For Role
    [Arguments]    ${role}
    New Context    baseURL=${BASE_URL}
    New Page    ${BASE_URL}/login
    Submit Login Form    ${USERS}[${role}][username]    ${USERS}[${role}][password]
    Get Url    *=    /dashboard
    Save Storage State    ${EXECDIR}/${AUTH_DIR}/${role}.json
    Close Context

Submit Login Form
    [Documentation]    The password goes through Fill Secret so it never appears in the log.
    [Arguments]    ${username}    ${password}
    Fill Text    data-testid=username    ${username}
    Fill Secret    data-testid=password    $password
    Click    data-testid=login-submit
