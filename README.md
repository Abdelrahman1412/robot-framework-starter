# robot-framework-starter

A keyword-driven **Robot Framework 7** starter for UI and API acceptance tests, written in the readable
Given/When/Then style Robot is known for. It ships with a tiny local **Acme HR** app and API, so the
whole suite runs offline, in parallel, in seconds.

```robot
Manager Approves A Request Created Through The API
    ${leave}=    Given "employee" Requests Leave Via The API    reason=Dentist appointment
    And I Am Signed In As "manager"
    And I Open The Approvals Page
    When I Approve Request ${leave}[id]
    Then Leave Request ${leave}[id] Should Have Status "approved" Via The API
```

## Why this approach

- **Browser library (Playwright)** for UI: auto-waiting, assertion-engine keywords (`Get Text  ==  ...`),
  isolated contexts per test, and saved **storage state** so each role logs in once per run.
- **RequestsLibrary** for the API, and the same API keywords do **test data setup**, so UI tests only
  click through the behaviour they are about.
- **JSON Schema contracts** (`resources/schemas/`) check API responses field by field.
- **Config from YAML + env vars**: one file per environment, any value overridable with `ACME_*` vars.
- **pabot** runs suites in parallel; **rebot** merges parallel and rerun outputs into one report.
- **Robocop** lints and formats the `.robot` files; **uv** with `uv.lock` pins every dependency.

## Quick start

Needs Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras                 # Robot Framework, Browser, RequestsLibrary, pabot, DatabaseLibrary
uv run rfbrowser init chromium       # Playwright node deps + Chromium only
scripts/run.sh                       # starts Acme HR, runs everything in parallel, merges the report
xdg-open results/report.html         # or open results/log.html for step-by-step detail
```

Handy variations:

```bash
scripts/run.sh --include smoke                 # tags: smoke, regression, negative, permissions, ui, api, db
HEADLESS=false PROCESSES=1 scripts/run.sh      # watch the browser
RERUN_FAILED=true scripts/run.sh               # rerun failures once, rebot --merge both results
uv run robot tests/api                         # plain robot also works; the suite setup starts the app
uv run robocop check && uv run robocop format --check
```

## Plug it into your app

1. **Point it at your app**: copy `variables/env/staging.yaml` to `variables/env/<yours>.yaml`, set
   `base_url` and `start_app: false`, then run with `ACME_ENV=<yours>`.
2. **Provide credentials through the environment**, never in files: `ACME_EMPLOYEE_USER`,
   `ACME_EMPLOYEE_PASSWORD`, `ACME_MANAGER_*`, `ACME_ADMIN_*` (CI secrets, or a local `.env` that
   `scripts/run.sh` loads and git ignores). Rename the roles in `variables/config.py` to match yours.
3. **Replace the page keywords** in `resources/pages/` with your screens; keep the
   `data-testid=` selectors or swap in your own.
4. **Replace the API keywords and schemas** in `resources/api/` and `resources/schemas/`, then reuse them
   for data setup in UI tests.
5. Delete `demo_app/` and the `start_app` setting once you test a real deployment.

### Configuration reference

| Variable | Default (local) | Purpose |
|---|---|---|
| `ACME_ENV` | `local` | Which `variables/env/<name>.yaml` to load |
| `ACME_BASE_URL`, `ACME_API_URL` | `http://127.0.0.1:8771`, `<base>/api` | App and API addresses |
| `ACME_<ROLE>_USER`, `ACME_<ROLE>_PASSWORD` | demo values | Credentials per role (`EMPLOYEE`, `MANAGER`, `ADMIN`) |
| `ACME_START_APP` | `true` | Start the bundled demo app if nothing answers at the base URL |
| `HEADLESS`, `BROWSER`, `ACME_TIMEOUT` | `true`, `chromium`, `10s` | Browser settings |
| `PROCESSES`, `RERUN_FAILED` | `2`, `false` | pabot processes, rerun-and-merge |

## What the demo suite proves

| Suite | Covers |
|---|---|
| `tests/ui/login.robot` | Sign-in for employee, manager and admin; wrong password; storage-state reuse |
| `tests/ui/leave_request.robot` | Employee submits leave; manager approves a request seeded via the API; employee sees the decision; invalid dates |
| `tests/ui/permissions.robot` | Menus per role; an employee and a manager are refused pages above their role |
| `tests/api/leave_api.robot` | Schema validation, list scoping, 401 / 403 / 409 / 422 paths |
| `tests/db/leave_persistence.robot` | Optional DatabaseLibrary check that API writes land in SQLite (`--exclude db` to skip) |

Failure screenshots are embedded in `log.html`, and passwords are kept out of it.

## Structure

```
demo_app/acme_hr.py        Acme HR: stdlib HTTP server, HTML pages + JSON API, SQLite storage
variables/config.py        variable file: YAML per environment + env var overrides
variables/env/*.yaml       local, ci, staging (example)
resources/common.resource  libraries, app lifecycle, browser session
resources/pages/           page keywords (login, dashboard, leave, approvals)
resources/api/             API keywords, also used for data setup
resources/db/              optional DatabaseLibrary keywords
resources/schemas/         JSON Schemas for API responses
libraries/SchemaLibrary.py "Response Should Match Schema" keyword
tests/                     ui/, api/, db/ suites; __init__.robot starts the app when needed
scripts/run.sh             start app -> pabot -> optional rerun -> rebot merge
.github/workflows/         lint + headless acceptance run, report uploaded as an artifact
```

Originally written in 2021, modernised in 2026.

## License

[MIT](LICENSE)
