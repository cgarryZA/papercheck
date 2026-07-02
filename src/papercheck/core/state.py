"""Audit state machine.

Tracks a paper's progress through the ordered audit stages and persists it to
disk. Bodies are filled in a later phase; the signatures here are the contract.
"""

from __future__ import annotations

from pathlib import Path

STAGES: list[str] = [
    "INIT",
    "SCANNED",
    "SEGMENTED",
    "INVENTORIED",
    "AUDITING",
    "SYNTHESIZED",
    "ADJUDICATED",
    "PATCH_PLANNED",
    "PATCHING",
    "REGRESSED",
    "GATED",
]


class StateError(Exception):
    """Raised when an audit-state operation is invalid."""


class AuditState:
    """In-memory representation of a paper's audit state."""

    @classmethod
    def load(cls, paper_root: Path) -> "AuditState":
        """Load the audit state for a paper from disk."""
        raise NotImplementedError

    def save(self) -> None:
        """Persist the audit state to disk."""
        raise NotImplementedError

    def advance(self, target: str) -> None:
        """Advance the audit state to the given target stage."""
        raise NotImplementedError

    def require_at_least(self, stage: str) -> None:
        """Raise if the current stage precedes the given stage."""
        raise NotImplementedError
