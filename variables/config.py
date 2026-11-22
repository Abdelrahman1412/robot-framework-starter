"""Robot Framework variable file: YAML defaults per environment, overridden by env vars.

Pick the environment with ``ACME_ENV`` (default ``local``) or ``--variablefile variables/config.py:<env>``.
Any ``ACME_*`` env var below wins over the YAML value, so CI and other machines never edit files.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

ENV_DIR = Path(__file__).parent / "env"
ROLES = ("employee", "manager", "admin")


def _bool(value: object) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def get_variables(env: str | None = None) -> dict:
    env = env or os.environ.get("ACME_ENV", "local")
    config = yaml.safe_load((ENV_DIR / f"{env}.yaml").read_text())

    base_url = os.environ.get("ACME_BASE_URL", config["base_url"]).rstrip("/")
    users = {}
    for role in ROLES:
        defaults = config["users"][role]
        users[role] = {
            "username": os.environ.get(f"ACME_{role.upper()}_USER", defaults["username"]),
            "password": os.environ.get(f"ACME_{role.upper()}_PASSWORD", defaults["password"]),
        }
    return {
        "ENV": env,
        "BASE_URL": base_url,
        "API_URL": os.environ.get("ACME_API_URL", config.get("api_url") or f"{base_url}/api").rstrip("/"),
        "BROWSER": os.environ.get("BROWSER", config.get("browser", "chromium")),
        "HEADLESS": _bool(os.environ.get("HEADLESS", config.get("headless", True))),
        "TIMEOUT": os.environ.get("ACME_TIMEOUT", config.get("timeout", "10s")),
        "START_APP": _bool(os.environ.get("ACME_START_APP", config.get("start_app", False))),
        "DB_PATH": os.environ.get("ACME_DB_PATH", config.get("db_path", "results/acme_hr.sqlite3")),
        "AUTH_DIR": os.environ.get("ACME_AUTH_DIR", config.get("auth_dir", "results/.auth")),
        "USERS": users,
    }
