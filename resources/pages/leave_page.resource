*** Settings ***
Documentation    Leave request page keywords (employee view).

Resource         ../common.resource


*** Keywords ***
I Open The Leave Page
    Go To    ${BASE_URL}/leave
    Get Element States    data-testid=leave-form    contains    visible

I Request "${type}" Leave From "${start}" To "${end}" Because "${reason}"
    Select Options By    data-testid=leave-type    value    ${type}
    Fill Text    data-testid=leave-start    ${start}
    Fill Text    data-testid=leave-end    ${end}
    Fill Text    data-testid=leave-reason    ${reason}
    Click    data-testid=leave-submit

The Request Should Be Submitted
    [Documentation]    Returns the id of the new request from the confirmation message.
    ${notice}=    Get Text    data-testid=leave-notice    matches    Leave request #\\d+ submitted
    ${id}=    Evaluate    re.search(r"#(\\d+)", $notice).group(1)    modules=re
    RETURN    ${id}

My Request ${id} Should Have Status "${status}"
    Get Text    data-testid=leave-status-${id}    ==    ${status}

I Should See The Leave Error "${message}"
    Get Text    data-testid=leave-error    ==    ${message}
