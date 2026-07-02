"""Adjudication, patch planning, and regression helpers.

These functions operate on the file-based ledgers to move issues through their
post-audit lifecycle: an adjudicator accepts/rejects/defers each proposed
issue, accepted issues are folded into planned then applied patches, and
regression results are recorded. Manual checks are created and resolved here
too.

All functions are pure with respect to wall-clock time (no timestamps are
generated) so they remain deterministic and testable.
"""

from __future__ import annotations

import json
from pathlib import Path

from papercheck.core import ledger, schemas
from papercheck.core.paths import audit_dir, manual_checks_dir

# Decisions accepted by :func:`adjudicate_issue` and the status each maps to.
_DECISION_TO_STATUS: dict[str, str] = {
    "ACCEPT": "ACCEPTED",
    "REJECT": "REJECTED",
    "NEEDS_MANUAL_CHECK": "NEEDS_MANUAL_CHECK",
}

# Issue statuses that count as belonging to the "accepted family": an issue in
# any of these has passed adjudication and is eligible for patch planning.
_ACCEPTED_FAMILY: frozenset[str] = frozenset(
    {"ACCEPTED", "PATCH_PLANNED", "PATCHED", "REGRESSION_PASSED", "CLOSED"}
)

# Regression outcomes accepted by :func:`record_regression_result`.
_REGRESSION_RESULTS: frozenset[str] = frozenset(
    {"FIXED", "PARTIALLY_FIXED", "NOT_FIXED", "NEW_PROBLEM"}
)


def _regression_file(paper_root: Path) -> Path:
    return audit_dir(Path(paper_root)) / "regression.json"


def adjudicate_issue(
    paper_root: Path,
    issue_id: str,
    decision: str,
    rationale: str,
    adjudicator: str,
    severity_final: str | None = None,
) -> dict:
    """Record an adjudication decision on an issue and re-route its file.

    ``decision`` must be one of ACCEPT / REJECT / NEEDS_MANUAL_CHECK. The issue
    is loaded from whichever status folder holds it, annotated with the
    decision, optionally given a final severity, and re-saved into the folder
    implied by its new status.

    Raises :class:`KeyError` when the issue is absent and :class:`ValueError`
    for an unknown decision.
    """
    paper_root = Path(paper_root)

    if decision not in _DECISION_TO_STATUS:
        raise ValueError(
            f"Unknown decision {decision!r}; expected one of "
            f"{sorted(_DECISION_TO_STATUS)}"
        )

    # KeyError propagates when the issue does not exist.
    issue = ledger.load_issue(paper_root, issue_id)

    issue["adjudication"] = {
        "decision": decision,
        "rationale": rationale,
        "adjudicator": adjudicator,
    }
    if severity_final is not None:
        issue["severity_final"] = severity_final
    issue["status"] = _DECISION_TO_STATUS[decision]

    # Remove the old file (it may live in a different folder than the new
    # status routes to) before saving the mutated issue.
    old_path = ledger._find_issue_path(paper_root, issue_id)
    if old_path is not None:
        old_path.unlink()
    ledger.save_issue(paper_root, issue)
    return issue


def plan_patch(paper_root: Path, patch: dict) -> dict:
    """Validate and record a *planned* patch over accepted issues.

    Refuses (raises :class:`ValueError`) unless every id in
    ``patch["accepted_issue_ids"]`` refers to an issue currently in an
    accepted-family status. On success the patch is saved and each referenced
    issue is bumped to ``PATCH_PLANNED``.
    """
    paper_root = Path(paper_root)
    schemas.validate(patch, "patch")

    for issue_id in patch["accepted_issue_ids"]:
        try:
            issue = ledger.load_issue(paper_root, issue_id)
        except KeyError as exc:
            raise ValueError(
                f"Patch references unknown issue {issue_id!r}"
            ) from exc
        if issue.get("status") not in _ACCEPTED_FAMILY:
            raise ValueError(
                f"Patch references issue {issue_id!r} with non-accepted status "
                f"{issue.get('status')!r}"
            )

    ledger.save_patch(paper_root, patch)
    for issue_id in patch["accepted_issue_ids"]:
        ledger.move_issue(paper_root, issue_id, "PATCH_PLANNED")
    return patch


def record_patch(paper_root: Path, patch: dict) -> dict:
    """Validate and record an *applied* patch, moving issues to ``PATCHED``.

    Like :func:`plan_patch` but represents a patch that has actually been
    applied; referenced issues are moved to ``PATCHED``.
    """
    paper_root = Path(paper_root)
    schemas.validate(patch, "patch")

    for issue_id in patch["accepted_issue_ids"]:
        try:
            issue = ledger.load_issue(paper_root, issue_id)
        except KeyError as exc:
            raise ValueError(
                f"Patch references unknown issue {issue_id!r}"
            ) from exc
        if issue.get("status") not in _ACCEPTED_FAMILY:
            raise ValueError(
                f"Patch references issue {issue_id!r} with non-accepted status "
                f"{issue.get('status')!r}"
            )

    ledger.save_patch(paper_root, patch)
    for issue_id in patch["accepted_issue_ids"]:
        ledger.move_issue(paper_root, issue_id, "PATCHED")
    return patch


def record_regression_result(paper_root: Path, issue_id: str, result: str) -> dict:
    """Append a regression outcome for an issue; promote it if ``FIXED``.

    ``result`` must be one of the allowed regression-vocabulary values:
    ``FIXED``, ``PARTIALLY_FIXED``, ``NOT_FIXED``, or ``NEW_PROBLEM``. Anything
    else raises :class:`ValueError`.

    Results are appended to ``Paper_Audit/regression.json`` (a JSON list). A
    ``FIXED`` result also moves the issue to ``REGRESSION_PASSED``.
    """
    paper_root = Path(paper_root)
    if result not in _REGRESSION_RESULTS:
        raise ValueError(
            f"Unknown regression result {result!r}; expected one of "
            f"{sorted(_REGRESSION_RESULTS)}"
        )

    path = _regression_file(paper_root)
    if path.exists():
        records = json.loads(path.read_text(encoding="utf-8"))
    else:
        records = []
    entry = {"issue_id": issue_id, "result": result}
    records.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")

    if result == "FIXED":
        ledger.move_issue(paper_root, issue_id, "REGRESSION_PASSED")

    return dict(entry)


def next_check_id(paper_root: Path) -> str:
    """Return the next unused manual-check id (e.g. ``MANUAL-3``)."""
    max_n = 0
    for check in ledger.list_manual_checks(Path(paper_root)):
        check_id = check.get("check_id", "")
        prefix, sep, suffix = check_id.rpartition("-")
        if sep and prefix == "MANUAL" and suffix.isdigit():
            max_n = max(max_n, int(suffix))
    return f"MANUAL-{max_n + 1}"


def add_manual_check(
    paper_root: Path,
    question: str,
    needed_source: str | None = None,
    blocking: bool = True,
    owner: str = "human",
) -> dict:
    """Create, validate, and persist a new manual check. Return it."""
    paper_root = Path(paper_root)
    check = {
        "check_id": next_check_id(paper_root),
        "question": question,
        "needed_source": needed_source,
        "blocking": blocking,
        "owner": owner,
        "resolution": None,
        "resolved": False,
    }
    schemas.validate(check, "manual_check")
    ledger.save_manual_check(paper_root, check)
    return check


def resolve_manual_check(
    paper_root: Path,
    check_id: str,
    resolution: str,
    resolved_by: str = "human",
) -> dict:
    """Mark a manual check resolved with the given resolution text. Return it.

    ``resolved_by`` records who resolved the check (defaults to ``"human"``).

    Raises :class:`KeyError` if the check does not exist.
    """
    paper_root = Path(paper_root)
    path = manual_checks_dir(paper_root) / f"{check_id}.json"
    if not path.is_file():
        raise KeyError(f"Manual check {check_id!r} not found")
    check = json.loads(path.read_text(encoding="utf-8"))
    check["resolved"] = True
    check["resolution"] = resolution
    check["resolved_by"] = resolved_by
    schemas.validate(check, "manual_check")
    ledger.save_manual_check(paper_root, check)
    return check
