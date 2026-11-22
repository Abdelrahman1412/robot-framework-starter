"""Validate JSON payloads against the JSON Schemas in ``resources/schemas``."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from robot.api.deco import keyword, library

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "resources" / "schemas"


@library(scope="GLOBAL")
class SchemaLibrary:
    @keyword
    def response_should_match_schema(self, payload: object, schema_name: str) -> None:
        """Fails with every violation listed when ``payload`` does not match ``<schema_name>.schema.json``."""
        schema = json.loads((SCHEMA_DIR / f"{schema_name}.schema.json").read_text())
        errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.path))
        if errors:
            details = "\n".join(f"- {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors)
            raise AssertionError(f"Payload does not match schema '{schema_name}':\n{details}")
