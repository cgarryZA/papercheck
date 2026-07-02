"""Canonical filesystem paths for a paper's audit workspace.

All audit artifacts for a paper live under ``<paper_root>/Paper_Audit``. These
helpers are pure ``pathlib`` joins and are implemented fully so that later
phases can rely on a single source of truth for layout.
"""

from __future__ import annotations

from pathlib import Path


def audit_dir(paper_root: Path) -> Path:
    """Return the root audit directory for a paper."""
    return paper_root / "Paper_Audit"


def state_file(paper_root: Path) -> Path:
    """Return the path to the audit state JSON file."""
    return audit_dir(paper_root) / "audit_state.json"


def structure_file(paper_root: Path) -> Path:
    """Return the path to the parsed document structure JSON file."""
    return audit_dir(paper_root) / "structure.json"


def segments_file(paper_root: Path) -> Path:
    """Return the path to the proposed segments JSON file."""
    return audit_dir(paper_root) / "segments.json"


def issues_dir(paper_root: Path, status: str) -> Path:
    """Return the issues directory for a given status bucket."""
    return audit_dir(paper_root) / "issues" / status


def patches_dir(paper_root: Path) -> Path:
    """Return the patches directory."""
    return audit_dir(paper_root) / "patches"


def manual_checks_dir(paper_root: Path) -> Path:
    """Return the manual-checks directory."""
    return audit_dir(paper_root) / "manual_checks"


def reports_dir(paper_root: Path) -> Path:
    """Return the reports directory."""
    return audit_dir(paper_root) / "reports"
