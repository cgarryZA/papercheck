"""Smoke tests for the papercheck Phase 0 skeleton."""

from __future__ import annotations

from pathlib import Path

import papercheck
import papercheck.core.schemas
import papercheck.core.state
from papercheck.core.paths import audit_dir


def test_import_and_version() -> None:
    assert papercheck.__version__ == "0.3.2"


def test_audit_dir() -> None:
    assert audit_dir(Path("x")) == Path("x") / "Paper_Audit"


def test_stages() -> None:
    assert papercheck.core.state.STAGES[0] == "INIT"
    assert papercheck.core.state.STAGES[-1] == "GATED"


def test_schema_names() -> None:
    assert len(papercheck.core.schemas.SCHEMA_NAMES) == 6
    assert "domain_pack" in papercheck.core.schemas.SCHEMA_NAMES
