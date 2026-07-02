"""Final gating checks for an audit."""

from __future__ import annotations

from pathlib import Path


def run_gate(paper_root: Path, mechanical_only: bool = False) -> dict:
    """Run gate checks for a paper and return a result report."""
    raise NotImplementedError
