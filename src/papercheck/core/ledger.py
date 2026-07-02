"""File-based ledgers for issues, manual checks, and patches.

Issues are stored one JSON file per issue, bucketed into status folders under
``<paper_root>/Paper_Audit/issues/<folder>``. Manual checks and patches live in
their own flat directories.
"""

from __future__ import annotations

import json
from pathlib import Path

from papercheck.core.paths import (
    issues_dir,
    manual_checks_dir,
    patches_dir,
)
from papercheck.core.schemas import validate

# Map an issue's ``status`` value to its on-disk folder name.
_STATUS_TO_FOLDER: dict[str, str] = {
    "PROPOSED": "proposed",
    "ACCEPTED": "accepted",
    "REJECTED": "rejected",
    "REJECTED_SOURCE_TARGET_INVALID": "rejected",
    "NEEDS_MANUAL_CHECK": "manual_check",
    "PATCH_PLANNED": "accepted",
    "PATCHED": "accepted",
    "REGRESSION_PASSED": "accepted",
    "CLOSED": "accepted",
}

# All folders an issue could ever live in (deduplicated, stable order).
_ISSUE_FOLDERS: list[str] = ["proposed", "accepted", "rejected", "manual_check"]


def _folder_for_status(status: str) -> str:
    try:
        return _STATUS_TO_FOLDER[status]
    except KeyError as exc:
        raise ValueError(f"Unknown issue status {status!r}") from exc


# -- issues ---------------------------------------------------------------


def save_issue(paper_root: Path, issue: dict) -> Path:
    """Validate ``issue`` and write it to its status folder. Return the path."""
    validate(issue, "issue")
    folder = _folder_for_status(issue["status"])
    target_dir = issues_dir(Path(paper_root), folder)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{issue['issue_id']}.json"
    path.write_text(json.dumps(issue, indent=2) + "\n", encoding="utf-8")
    return path


def _find_issue_path(paper_root: Path, issue_id: str) -> Path | None:
    for folder in _ISSUE_FOLDERS:
        candidate = issues_dir(Path(paper_root), folder) / f"{issue_id}.json"
        if candidate.exists():
            return candidate
    return None


def load_issue(paper_root: Path, issue_id: str) -> dict:
    """Load a single issue by id from any status folder."""
    path = _find_issue_path(Path(paper_root), issue_id)
    if path is None:
        raise KeyError(f"Issue {issue_id!r} not found")
    return json.loads(path.read_text(encoding="utf-8"))


def move_issue(paper_root: Path, issue_id: str, new_status: str) -> dict:
    """Change an issue's status, relocating its file to the new status folder."""
    path = _find_issue_path(Path(paper_root), issue_id)
    if path is None:
        raise KeyError(f"Issue {issue_id!r} not found")
    issue = json.loads(path.read_text(encoding="utf-8"))
    issue["status"] = new_status
    path.unlink()
    save_issue(Path(paper_root), issue)
    return issue


def list_issues(paper_root: Path, status: str | None = None) -> list[dict]:
    """Return all issues, optionally filtered by exact ``status``, sorted by id."""
    issues: list[dict] = []
    for folder in _ISSUE_FOLDERS:
        folder_dir = issues_dir(Path(paper_root), folder)
        if not folder_dir.is_dir():
            continue
        for path in folder_dir.glob("*.json"):
            issue = json.loads(path.read_text(encoding="utf-8"))
            if status is None or issue.get("status") == status:
                issues.append(issue)
    issues.sort(key=lambda i: i.get("issue_id", ""))
    return issues


def next_issue_id(paper_root: Path, prefix: str = "MATH") -> str:
    """Return the next unused issue id for ``prefix`` (e.g. ``MATH-1``)."""
    max_n = 0
    for issue in list_issues(Path(paper_root)):
        issue_id = issue.get("issue_id", "")
        this_prefix, sep, suffix = issue_id.rpartition("-")
        if sep and this_prefix == prefix and suffix.isdigit():
            max_n = max(max_n, int(suffix))
    return f"{prefix}-{max_n + 1}"


# -- manual checks --------------------------------------------------------


def save_manual_check(paper_root: Path, check: dict) -> Path:
    """Validate and persist a manual check. Return its path."""
    validate(check, "manual_check")
    target_dir = manual_checks_dir(Path(paper_root))
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{check['check_id']}.json"
    path.write_text(json.dumps(check, indent=2) + "\n", encoding="utf-8")
    return path


def list_manual_checks(paper_root: Path) -> list[dict]:
    """Return all manual checks, sorted by ``check_id``."""
    target_dir = manual_checks_dir(Path(paper_root))
    checks: list[dict] = []
    if target_dir.is_dir():
        for path in target_dir.glob("*.json"):
            checks.append(json.loads(path.read_text(encoding="utf-8")))
    checks.sort(key=lambda c: c.get("check_id", ""))
    return checks


# -- patches --------------------------------------------------------------


def save_patch(paper_root: Path, patch: dict) -> Path:
    """Validate and persist a patch. Return its path."""
    validate(patch, "patch")
    target_dir = patches_dir(Path(paper_root))
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{patch['patch_id']}.json"
    path.write_text(json.dumps(patch, indent=2) + "\n", encoding="utf-8")
    return path


def list_patches(paper_root: Path) -> list[dict]:
    """Return all patches, sorted by ``patch_id``."""
    target_dir = patches_dir(Path(paper_root))
    patches: list[dict] = []
    if target_dir.is_dir():
        for path in target_dir.glob("*.json"):
            patches.append(json.loads(path.read_text(encoding="utf-8")))
    patches.sort(key=lambda p: p.get("patch_id", ""))
    return patches
