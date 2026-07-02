"""JSON-schema validation for audit artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_NAMES: list[str] = ["issue", "patch", "segment", "manual_check", "state"]

_SCHEMA_CACHE: dict[str, dict] = {}


def _schemas_root() -> Path:
    """Locate the directory holding the ``*.schema.json`` files.

    The package lives at ``<repo>/src/papercheck/core``; schemas sit at the
    repo root under ``schemas/``. That is ``parents[3]`` from this file. If
    that directory is absent (e.g. an unusual install layout), fall back to a
    ``schemas`` directory packaged alongside the ``papercheck`` package.
    """
    repo_root = Path(__file__).resolve().parents[3]
    candidate = repo_root / "schemas"
    if candidate.is_dir():
        return candidate
    # Installed-data fallback: schemas shipped next to the package.
    packaged = Path(__file__).resolve().parents[1] / "schemas"
    if packaged.is_dir():
        return packaged
    raise FileNotFoundError(
        f"Could not locate a schemas/ directory (tried {candidate} and {packaged})"
    )


def load_schema(schema_name: str) -> dict:
    """Load and cache the named schema, returning its parsed contents."""
    if schema_name not in SCHEMA_NAMES:
        raise ValueError(
            f"Unknown schema {schema_name!r}; expected one of {SCHEMA_NAMES}"
        )
    if schema_name in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[schema_name]
    path = _schemas_root() / f"{schema_name}.schema.json"
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
