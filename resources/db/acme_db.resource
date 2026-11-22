*** Settings ***
Documentation    Optional database checks (DatabaseLibrary + SQLite). Install with ``uv sync --extra db``.

Library          DatabaseLibrary
Resource         ../common.resource


*** Keywords ***
I Connect To The Acme HR Database
    Connect To Database    sqlite3    database=${EXECDIR}/${DB_PATH}    isolation_level=${None}

Leave Request ${id} Should Be Stored With Status "${status}"
    VAR    @{params}    ${id}
    Check Row Count    SELECT id FROM leave_requests WHERE id = ?    ==    1    parameters=${params}
    Check Query Result    SELECT status FROM leave_requests WHERE id = ?    ==    ${status}
    ...    parameters=${params}
