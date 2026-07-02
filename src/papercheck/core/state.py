"""Audit state machine.

Tracks a paper's progress through the ordered audit stages and persists it to
disk. The stage ordering in :data:`STAGES` is the single source of truth for
what "advancing" means.
"""

from __future__ import annotations

import json
from pathlib import Path

from papercheck.core.paths import state_file
from papercheck.core.schemas import validate

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

    def __init__(
        self,
        *,
        paper_root: Path,
        run_id: str,
        harness_version: str,
        stage: str,
        completed_stages: list[str],
        paper_git_commit: str | None = None,
        stage_history: list[dict] | None = None,
        blocking_errors: list[str] | None = None,
    ) -> None:
        self.paper_root = Path(paper_root)
        self.run_id = run_id
        self.harness_version = harness_version
        self.stage = stage
        self.completed_stages = completed_stages
        self.paper_git_commit = paper_git_commit
        self.stage_history = stage_history if stage_history is not None else []
        self.blocking_errors = blocking_errors if blocking_errors is not None else []

    # -- serialization ----------------------------------------------------

    def to_dict(self) -> dict:
        """Return the schema-shaped dict representation of this state."""
        return {
            "run_id": self.run_id,
            "harness_version": self.harness_version,
            "paper_root": str(self.paper_root),
            "paper_git_commit": self.paper_git_commit,
            "stage": self.stage,
            "completed_stages": list(self.completed_stages),
            "stage_history": list(self.stage_history),
            "blocking_errors": list(self.blocking_errors),
        }

    @classmethod
    def _from_dict(cls, data: dict, paper_root: Path) -> "AuditState":
        return cls(
            paper_root=paper_root,
            run_id=data["run_id"],
            harness_version=data["harness_version"],
            stage=data["stage"],
            completed_stages=list(data.get("completed_stages", [])),
            paper_git_commit=data.get("paper_git_commit"),
            stage_history=list(data.get("stage_history", [])),
            blocking_errors=list(data.get("blocking_errors", [])),
        )

    # -- construction / persistence --------------------------------------

    @classmethod
    def init(
        cls,
        paper_root: Path,
        run_id: str,
        harness_version: str,
        git_commit: str | None,
        by: str = "cli",
    ) -> "AuditState":
        """Create and persist a fresh audit state at stage ``INIT``.

        ``run_id`` doubles as the timestamp for the initial stage-history
        entry (no wall clock is assumed to be available).
        """
        state = cls(
            paper_root=Path(paper_root),
            run_id=run_id,
            harness_version=harness_version,
            stage="INIT",
            completed_stages=["INIT"],
            paper_git_commit=git_commit,
            stage_history=[{"stage": "INIT", "at": run_id, "by": by}],
            blocking_errors=[],
        )
        state.save()
        return state

    @classmethod
    def load(cls, paper_root: Path) -> "AuditState":
        """Load the audit state for a paper from disk."""
        path = state_file(Path(paper_root))
        if not path.exists():
            raise StateError(f"No audit state found at {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        validate(data, "state")
        return cls._from_dict(data, Path(paper_root))

    def save(self) -> None:
        """Validate then persist the audit state to disk."""
        data = self.to_dict()
        validate(data, "state")
        path = state_file(self.paper_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    # -- transitions ------------------------------------------------------

    def advance(self, target: str, at: str = "", by: str = "cli") -> None:
        """Advance to ``target``: the next stage, or a re-entry of the current one.

        Forward-skipping more than one stage or moving backward raises
        :class:`StateError`. Re-entering the current stage is idempotent.
        """
        if target not in STAGES:
            raise StateError(f"Unknown target stage {target!r}")
        current_idx = STAGES.index(self.stage)
        target_idx = STAGES.index(target)
        if target_idx < current_idx:
            raise StateError(
                f"Cannot move backward from {self.stage} to {target}"
            )
        if target_idx > current_idx + 1:
            raise StateError(
                f"Cannot skip stages from {self.stage} to {target}"
            )
        # target_idx == current_idx (idempotent re-entry) or current_idx + 1.
        self.stage = target
        if target not in self.completed_stages:
            self.completed_stages.append(target)
        self.stage_history.append({"stage": target, "at": at, "by": by})
        self.save()

    def require_at_least(self, stage: str) -> None:
        """Raise if the current stage precedes the given stage."""
        if stage not in STAGES:
            raise StateError(f"Unknown required stage {stage!r}")
        if STAGES.index(self.stage) < STAGES.index(stage):
            raise StateError(
                f"Operation requires stage {stage} but current stage is {self.stage}"
            )
