"""Verification helpers for quotes and structural labels."""

from __future__ import annotations

from pathlib import Path


def verify_quote(
    file: Path,
    quote: str,
    line_start: int | None = None,
    line_end: int | None = None,
    slack: int = 0,
) -> bool:
    """Return whether ``quote`` appears in ``file`` within the given line range."""
    raise NotImplementedError


def label_exists(structure: dict, label: str) -> bool:
    """Return whether ``label`` is defined in the parsed document structure."""
    raise NotImplementedError
