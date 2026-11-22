*** Settings ***
Documentation    Shared setup: configuration, the demo app lifecycle and browser sessions per role.

Variables        ../variables/config.py
Library          OperatingSystem
Library          Process
Library          Browser    timeout=${TIMEOUT}    auto_closing_level=TEST
Library          RequestsLibrary
Library          pabot.PabotLib


*** Variables ***
${APP_PID_FILE}    ${EXECDIR}/results/acme_hr.pid


*** Keywords ***
Ensure Acme HR Is Running
    [Documentation]    Starts the bundled demo app when it is not reachable yet and START_APP is true.
    ...    scripts/run.sh normally starts it first, so this is a no-op there.
    ${running}=    Acme HR Is Healthy
    IF    ${running}    RETURN
    IF    not ${START_APP}
        Fail    Acme HR is not reachable at ${BASE_URL} and START_APP is false
    END
    Create Directory    ${EXECDIR}/results
    ${port}=    Evaluate    urllib.parse.urlparse($BASE_URL).port or 80    modules=urllib.parse
    ${python}=    Evaluate    sys.executable    modules=sys
    ${app}=    Start Process    ${python}    -m    demo_app.acme_hr    cwd=${EXECDIR}
    ...    env:ACME_PORT=${port}    env:ACME_DB_PATH=${DB_PATH}
    ...    stdout=${EXECDIR}/results/acme_hr.log    stderr=STDOUT
    Create File    ${APP_PID_FILE}    ${app.pid}
    Wait Until Keyword Succeeds    20x    0.5s    Acme HR Should Be Healthy

Stop Acme HR If This Run Started It
    ${started}=    Run Keyword And Return Status    File Should Exist    ${APP_PID_FILE}
    IF    not ${started}    RETURN
    ${pid}=    Get File    ${APP_PID_FILE}
    Evaluate    os.kill(int($pid), signal.SIGTERM)    modules=os,signal
    Remove File    ${APP_PID_FILE}

Acme HR Is Healthy
    ${status}=    Run Keyword And Return Status    Acme HR Should Be Healthy
    RETURN    ${status}

Acme HR Should Be Healthy
    ${response}=    GET    ${API_URL}/health    expected_status=200    timeout=2
    Should Be Equal    ${response.json()}[status]    ok

Open Browser Session
    [Documentation]    One browser per suite; each test gets a fresh context (cookies, storage).
    ...    Failure screenshots are embedded so they survive the pabot + rebot merge.
    Register Keyword To Run On Failure    Take Screenshot    EMBED
    New Browser    ${BROWSER}    headless=${HEADLESS}
