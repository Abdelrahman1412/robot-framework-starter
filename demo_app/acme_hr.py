"""Acme HR: a tiny, dependency-free HR app and JSON API used as the demo target.

Run it with ``python -m demo_app.acme_hr`` (or ``scripts/run.sh``). It serves:

* HTML pages: /login, /dashboard, /leave, /approvals (manager, admin), /admin/users (admin)
* JSON API under /api: auth, current user, leave requests and decisions

Data lives in a SQLite file (``ACME_DB_PATH``) so tests can also check persistence.
"""

from __future__ import annotations

import html
import json
import os
import secrets
import sqlite3
import threading
from datetime import date, datetime, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOST = os.environ.get("ACME_HOST", "127.0.0.1")
PORT = int(os.environ.get("ACME_PORT", "8771"))
DB_PATH = Path(os.environ.get("ACME_DB_PATH", "results/acme_hr.sqlite3"))

USERS = {
    os.environ.get("ACME_EMPLOYEE_USER", "emma"): {
        "password": os.environ.get("ACME_EMPLOYEE_PASSWORD", "demo-employee-pass"),
        "name": "Emma Employee",
        "role": "employee",
    },
    os.environ.get("ACME_MANAGER_USER", "mark"): {
        "password": os.environ.get("ACME_MANAGER_PASSWORD", "demo-manager-pass"),
        "name": "Mark Manager",
        "role": "manager",
    },
    os.environ.get("ACME_ADMIN_USER", "ada"): {
        "password": os.environ.get("ACME_ADMIN_PASSWORD", "demo-admin-pass"),
        "name": "Ada Admin",
        "role": "admin",
    },
}
LEAVE_TYPES = ("annual", "sick", "unpaid")
APPROVER_ROLES = ("manager", "admin")

_sessions: dict[str, str] = {}
_lock = threading.Lock()


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.execute("DROP TABLE IF EXISTS leave_requests")
        conn.execute(
            """CREATE TABLE leave_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee TEXT NOT NULL,
                leave_type TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                days INTEGER NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                decided_by TEXT,
                created_at TEXT NOT NULL
            )"""
        )


def row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "employee": row["employee"],
        "type": row["leave_type"],
        "startDate": row["start_date"],
        "endDate": row["end_date"],
        "days": row["days"],
        "reason": row["reason"],
        "status": row["status"],
        "decidedBy": row["decided_by"],
        "createdAt": row["created_at"],
    }


def validate_leave(data: dict) -> tuple[dict | None, str | None]:
    leave_type = str(data.get("type", "")).strip()
    reason = str(data.get("reason", "")).strip()
    if leave_type not in LEAVE_TYPES:
        return None, f"Leave type must be one of: {', '.join(LEAVE_TYPES)}"
    try:
        start = date.fromisoformat(str(data.get("startDate", "")))
        end = date.fromisoformat(str(data.get("endDate", "")))
    except ValueError:
        return None, "Start and end dates must be valid dates (YYYY-MM-DD)"
    if end < start:
        return None, "End date cannot be before start date"
    if not reason:
        return None, "Reason is required"
    return {
        "type": leave_type,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "days": (end - start).days + 1,
        "reason": reason[:200],
    }, None


def create_leave(username: str, clean: dict) -> dict:
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO leave_requests (employee, leave_type, start_date, end_date, days, reason, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                username,
                clean["type"],
                clean["start"],
                clean["end"],
                clean["days"],
                clean["reason"],
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
        row = conn.execute("SELECT * FROM leave_requests WHERE id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


def get_leave(leave_id: int) -> dict | None:
    with db() as conn:
        row = conn.execute("SELECT * FROM leave_requests WHERE id = ?", (leave_id,)).fetchone()
    return row_to_dict(row) if row else None


def list_leave(username: str | None = None, status: str | None = None) -> list[dict]:
    query, params = "SELECT * FROM leave_requests WHERE 1=1", []
    if username:
        query += " AND employee = ?"
        params.append(username)
    if status:
        query += " AND status = ?"
        params.append(status)
    with db() as conn:
        rows = conn.execute(query + " ORDER BY id DESC", params).fetchall()
    return [row_to_dict(r) for r in rows]


def decide_leave(leave_id: int, decision: str, approver: str) -> dict | None:
    with db() as conn:
        conn.execute(
            "UPDATE leave_requests SET status = ?, decided_by = ? WHERE id = ? AND status = 'pending'",
            (decision, approver, leave_id),
        )
    return get_leave(leave_id)


def public_user(username: str) -> dict:
    user = USERS[username]
    return {"username": username, "name": user["name"], "role": user["role"]}


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title} | Acme HR</title>
<style>
body{{font-family:system-ui,sans-serif;margin:0;background:#f5f6f8;color:#1d2330}}
header{{background:#243b6b;color:#fff;padding:12px 24px;display:flex;gap:16px;align-items:center}}
header a{{color:#fff}} main{{max-width:880px;margin:24px auto;padding:0 16px}}
.card{{background:#fff;border-radius:8px;padding:20px;margin-bottom:16px;box-shadow:0 1px 3px #0002}}
.error{{background:#fde8e8;color:#9b1c1c;padding:10px;border-radius:6px}}
.notice{{background:#e6f4ea;color:#1e6b34;padding:10px;border-radius:6px}}
table{{width:100%;border-collapse:collapse}} td,th{{padding:6px;border-bottom:1px solid #ddd;text-align:left}}
label{{display:block;margin:8px 0}} input,select{{padding:6px}} button{{padding:6px 14px}}
</style></head><body>{nav}<main>{body}</main></body></html>"""


def render(title: str, body: str, user: str | None = None) -> str:
    nav = ""
    if user:
        info = USERS[user]
        links = ['<a href="/dashboard">Dashboard</a>', '<a href="/leave" data-testid="nav-leave">Leave</a>']
        if info["role"] in APPROVER_ROLES:
            links.append('<a href="/approvals" data-testid="nav-approvals">Approvals</a>')
        if info["role"] == "admin":
            links.append('<a href="/admin/users" data-testid="nav-admin">Users</a>')
        nav = (
            "<header><strong>Acme HR</strong>" + "".join(links)
            + f'<span style="margin-left:auto" data-testid="current-user">{html.escape(info["name"])}'
            f' ({info["role"]})</span><a href="/logout" data-testid="logout">Log out</a></header>'
        )
    return PAGE.format(title=html.escape(title), nav=nav, body=body)


def leave_rows(items: list[dict], with_actions: bool = False) -> str:
    rows = []
    for item in items:
        actions = ""
        if with_actions:
            actions = (
                f'<td><form method="post" action="/approvals/{item["id"]}/approved" style="display:inline">'
                f'<button data-testid="approve-{item["id"]}">Approve</button></form> '
                f'<form method="post" action="/approvals/{item["id"]}/rejected" style="display:inline">'
                f'<button data-testid="reject-{item["id"]}">Reject</button></form></td>'
            )
        rows.append(
            f'<tr data-testid="leave-row-{item["id"]}"><td>{item["id"]}</td><td>{html.escape(item["employee"])}</td>'
            f'<td>{item["type"]}</td><td>{item["startDate"]} to {item["endDate"]}</td><td>{item["days"]}</td>'
            f'<td>{html.escape(item["reason"])}</td><td data-testid="leave-status-{item["id"]}">{item["status"]}</td>'
            f"{actions}</tr>"
        )
    head = "<tr><th>#</th><th>Employee</th><th>Type</th><th>Dates</th><th>Days</th><th>Reason</th><th>Status</th>"
    head += "<th>Action</th></tr>" if with_actions else "</tr>"
    return f'<table data-testid="leave-table">{head}{"".join(rows)}</table>' if rows else "<p>No requests.</p>"


class Handler(BaseHTTPRequestHandler):
    server_version = "AcmeHR/1.0"

    def log_message(self, fmt: str, *args) -> None:  # keep test output quiet
        if os.environ.get("ACME_VERBOSE"):
            super().log_message(fmt, *args)

    # ---- helpers -------------------------------------------------------
    def _send(self, status: int, body: str | bytes, content_type: str, headers: dict | None = None) -> None:
        data = body.encode() if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(data)

    def html(self, status: int, body: str, headers: dict | None = None) -> None:
        self._send(status, body, "text/html; charset=utf-8", headers)

    def json(self, status: int, payload: object) -> None:
        self._send(status, json.dumps(payload), "application/json")

    def redirect(self, location: str, headers: dict | None = None) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()

    def body_bytes(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length else b""

    def form(self) -> dict:
        return {k: v[0] for k, v in parse_qs(self.body_bytes().decode()).items()}

    def json_body(self) -> dict | None:
        try:
            data = json.loads(self.body_bytes() or b"{}")
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None

    def session_user(self) -> str | None:
        token = None
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
        else:
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            if "acme_session" in cookie:
                token = cookie["acme_session"].value
        with _lock:
            return _sessions.get(token or "")

    @staticmethod
    def new_session(username: str) -> str:
        token = secrets.token_hex(16)
        with _lock:
            _sessions[token] = username
        return token

    # ---- routing -------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        if url.path.startswith("/api/"):
            return self.api("GET", url.path)
        return self.page_get(url.path, parse_qs(url.query))

    def do_POST(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        if url.path.startswith("/api/"):
            return self.api("POST", url.path)
        return self.page_post(url.path)

    # ---- HTML pages ----------------------------------------------------
    def login_page(self, status: int = 200, error: str = "") -> None:
        err = f'<p class="error" data-testid="login-error" role="alert">{html.escape(error)}</p>' if error else ""
        body = (
            '<div class="card" style="max-width:360px;margin:60px auto"><h1>Sign in to Acme HR</h1>' + err
            + '<form method="post" action="/login" data-testid="login-form">'
            '<label>Username <input name="username" data-testid="username" autocomplete="username"></label>'
            '<label>Password <input name="password" type="password" data-testid="password"></label>'
            '<button type="submit" data-testid="login-submit">Sign in</button></form></div>'
        )
        self.html(status, render("Sign in", body))

    def forbidden_page(self, user: str) -> None:
        body = '<div class="card"><h1 data-testid="access-denied">Access denied</h1>' \
               "<p>Your role cannot open this page.</p></div>"
        self.html(HTTPStatus.FORBIDDEN, render("Access denied", body, user))

    def leave_page(self, user: str, status: int = 200, error: str = "", notice: str = "") -> None:
        msg = f'<p class="error" data-testid="leave-error" role="alert">{html.escape(error)}</p>' if error else ""
        msg += f'<p class="notice" data-testid="leave-notice">{html.escape(notice)}</p>' if notice else ""
        options = "".join(f'<option value="{t}">{t.title()}</option>' for t in LEAVE_TYPES)
        body = (
            '<div class="card"><h1>Request leave</h1>' + msg
            + '<form method="post" action="/leave" data-testid="leave-form">'
            f'<label>Type <select name="type" data-testid="leave-type">{options}</select></label>'
            '<label>Start date <input type="date" name="startDate" data-testid="leave-start"></label>'
            '<label>End date <input type="date" name="endDate" data-testid="leave-end"></label>'
            '<label>Reason <input name="reason" data-testid="leave-reason" size="40"></label>'
            '<button type="submit" data-testid="leave-submit">Submit request</button></form></div>'
            '<div class="card"><h2>My requests</h2>' + leave_rows(list_leave(user)) + "</div>"
        )
        self.html(status, render("Leave", body, user))

    def page_get(self, path: str, query: dict) -> None:
        user = self.session_user()
        if path == "/":
            return self.redirect("/dashboard" if user else "/login")
        if path == "/login":
            return self.login_page()
        if path == "/logout":
            return self.redirect("/login", {"Set-Cookie": "acme_session=; Path=/; Max-Age=0"})
        if not user:
            return self.redirect("/login")
        role = USERS[user]["role"]
        if path == "/dashboard":
            pending = len(list_leave(None if role in APPROVER_ROLES else user, "pending"))
            body = (
                f'<div class="card"><h1 data-testid="welcome">Welcome, {html.escape(USERS[user]["name"])}</h1>'
                f'<p>Role: <strong data-testid="role">{role}</strong></p>'
                f'<p>Pending leave requests: <strong data-testid="pending-count">{pending}</strong></p></div>'
            )
            return self.html(200, render("Dashboard", body, user))
        if path == "/leave":
            notice = f"Leave request #{query['created'][0]} submitted" if "created" in query else ""
            return self.leave_page(user, notice=notice)
        if path == "/approvals":
            if role not in APPROVER_ROLES:
                return self.forbidden_page(user)
            body = '<div class="card"><h1>Pending approvals</h1>' + leave_rows(
                list_leave(status="pending"), with_actions=True
            ) + "</div>"
            return self.html(200, render("Approvals", body, user))
        if path == "/admin/users":
            if role != "admin":
                return self.forbidden_page(user)
            rows = "".join(
                f"<tr><td>{u}</td><td>{html.escape(i['name'])}</td><td>{i['role']}</td></tr>" for u, i in USERS.items()
            )
            body = f'<div class="card"><h1>Users</h1><table data-testid="users-table">{rows}</table></div>'
            return self.html(200, render("Users", body, user))
        self.html(404, render("Not found", "<h1>Not found</h1>", user))

    def page_post(self, path: str) -> None:
        if path == "/login":
            data = self.form()
            username, password = data.get("username", ""), data.get("password", "")
            if username in USERS and secrets.compare_digest(USERS[username]["password"], password):
                token = self.new_session(username)
                return self.redirect("/dashboard", {"Set-Cookie": f"acme_session={token}; Path=/; HttpOnly"})
            return self.login_page(HTTPStatus.UNAUTHORIZED, "Invalid username or password")
        user = self.session_user()
        if not user:
            return self.redirect("/login")
        if path == "/leave":
            clean, error = validate_leave(self.form())
            if error:
                return self.leave_page(user, HTTPStatus.BAD_REQUEST, error=error)
            item = create_leave(user, clean)
            return self.redirect(f"/leave?created={item['id']}")
        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "approvals" and parts[2] in ("approved", "rejected"):
            if USERS[user]["role"] not in APPROVER_ROLES:
                return self.forbidden_page(user)
            decide_leave(int(parts[1]), parts[2], user)
            return self.redirect("/approvals")
        self.html(404, render("Not found", "<h1>Not found</h1>", user))

    # ---- JSON API ------------------------------------------------------
    def api(self, method: str, path: str) -> None:
        if method == "GET" and path == "/api/health":
            return self.json(200, {"status": "ok"})
        if method == "POST" and path == "/api/auth/login":
            data = self.json_body() or {}
            username, password = str(data.get("username", "")), str(data.get("password", ""))
            if username in USERS and secrets.compare_digest(USERS[username]["password"], password):
                return self.json(200, {"token": self.new_session(username), "user": public_user(username)})
            return self.json(401, {"error": "invalid_credentials", "message": "Invalid username or password"})

        user = self.session_user()
        if not user:
            return self.json(401, {"error": "unauthorized", "message": "Missing or invalid token"})
        role = USERS[user]["role"]

        if method == "GET" and path == "/api/me":
            return self.json(200, public_user(user))
        if path == "/api/leave-requests":
            if method == "GET":
                items = list_leave(None if role in APPROVER_ROLES else user)
                return self.json(200, {"items": items, "count": len(items)})
            data = self.json_body()
            if data is None:
                return self.json(400, {"error": "validation_error", "message": "Body must be a JSON object"})
            clean, error = validate_leave(data)
            if error:
                return self.json(422, {"error": "validation_error", "message": error})
            return self.json(201, create_leave(user, clean))

        parts = path.strip("/").split("/")  # api, leave-requests, <id>[, decision]
        if len(parts) >= 3 and parts[1] == "leave-requests" and parts[2].isdigit():
            item = get_leave(int(parts[2]))
            if not item or (role not in APPROVER_ROLES and item["employee"] != user):
                return self.json(404, {"error": "not_found", "message": "Leave request not found"})
            if len(parts) == 3 and method == "GET":
                return self.json(200, item)
            if len(parts) == 4 and parts[3] == "decision" and method == "POST":
                if role not in APPROVER_ROLES:
                    return self.json(403, {"error": "forbidden", "message": "Only managers can decide leave"})
                decision = str((self.json_body() or {}).get("decision", ""))
                if decision not in ("approved", "rejected"):
                    return self.json(422, {"error": "validation_error", "message": "decision must be approved|rejected"})
                if item["status"] != "pending":
                    return self.json(409, {"error": "conflict", "message": "Leave request already decided"})
                return self.json(200, decide_leave(item["id"], decision, user))
        self.json(404, {"error": "not_found", "message": "No such endpoint"})


def main() -> None:
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Acme HR listening on http://{HOST}:{PORT} (db: {DB_PATH})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
