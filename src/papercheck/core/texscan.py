"""Scan a paper's LaTeX sources into a structured representation."""

from __future__ import annotations

from pathlib import Path


def scan(paper_root: Path) -> dict:
    """Scan the LaTeX sources under ``paper_root`` and return structure data."""
    raise NotImplementedError
