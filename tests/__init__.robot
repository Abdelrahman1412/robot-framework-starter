*** Settings ***
Documentation     Acme HR acceptance suite. Starts the demo app if nothing is serving BASE_URL yet.

Resource          ../resources/common.resource

Suite Setup       Run Setup Only Once    Ensure Acme HR Is Running
Suite Teardown    Run Teardown Only Once    Stop Acme HR If This Run Started It
