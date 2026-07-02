"""JSON-schema validation for audit artifacts."""

from __future__ import annotations

SCHEMA_NAMES: list[str] = ["issue", "patch", "segment", "manual_check", "state"]


def validate(instance: dict, schema_name: str) -> None:
    """Validate ``instance`` against the named schema, raising on failure."""
    raise NotImplementedError
