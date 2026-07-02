"""JSON-schema validation for audit artifacts."""

from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from papercheck.core._resources import resource_file

SCHEMA_NAMES: list[str] = ["issue", "patch", "segment", "manual_check", "state"]

_SCHEMA_CACHE: dict[str, dict] = {}


def load_schema(schema_name: str) -> dict:
    """Load and cache the named schema, returning its parsed contents."""
    if schema_name not in SCHEMA_NAMES:
        raise ValueError(
            f"Unknown schema {schema_name!r}; expected one of {SCHEMA_NAMES}"
        )
    if schema_name in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[schema_name]
    path = resource_file("schemas", f"{schema_name}.schema.json")
    schema = json.loads(path.read_text(encoding="utf-8"))
    _SCHEMA_CACHE[schema_name] = schema
    return schema


def validate(instance: dict, schema_name: str) -> None:
    """Validate ``instance`` against the named schema, raising on failure.

    Raises ``ValueError`` if ``schema_name`` is unknown, and lets
    ``jsonschema.ValidationError`` propagate when the instance is invalid.
    """
    schema = load_schema(schema_name)
    validator = Draft202012Validator(schema)
    validator.validate(instance)
