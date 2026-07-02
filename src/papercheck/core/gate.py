"""Final gating checks for an audit.

The gate is a *mechanical* final check: it gathers deterministic signals
(build status, structural defects, open blocking issues, unresolved manual
checks) and maps them to a single verdict via a fixed priority order. It never
raises on build failures -- an absent or failing build simply becomes a signal.

Canonical verdict strings (do not invent others)::

    NOT READY: MANUAL CHECK REQUIRED
    NOT READY: MATHEMATICAL ISSUE
    NOT READY: NUMERICAL / EXPERIMENT ISSUE
    NOT READY: CLAIM / FRAMING ISSUE
    NOT READY: BUILD / SOURCE ISSUE
    READY AFTER MECHANICAL FIXES
    READY

Note: upstream design docs also use "READY FOR SUBMISSION" as the human-facing
final blessing. This mechanical gate emits "READY" for the clean case; the
"READY FOR SUBMISSION" wording is reserved for a later human sign-off stage.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from papercheck.core import ledger, paths, texscan

_BUILD_TIMEOUT_S = 120

# Issue statuses that count as still-open (a fix has not been verified done).
_OPEN_STATUSES = {"ACCEPTED", "PATCH_PLANNED", "PATCHED"}

# Severities that make an open issue block the gate.
_BLOCKING_SEVERITIES = {"FATAL", "SERIOUS"}


def _load_structure(paper_root: Path) -> dict:
    """Load structure.json if present, else run the scanner."""
    struct_path = paths.structure_file(paper_root)
    if struct_path.exists():
        return json.loads(struct_path.read_text(encoding="utf-8"))
    return texscan.scan(paper_root)


def _attempt_build(paper_root: Path, structure: dict) -> bool | None:
    """Return True/False for build success, or None if it could not be run.

    None means "unknown" (no latexmk, no main candidate, or an error/timeout) --
    it is explicitly NOT treated as a failure downstream.
    """
    main_candidates = structure.get("main_candidates", [])
    if not main_candidates:
        return None
    if shutil.which("latexmk") is None:
        return None
    main_file = main_candidates[0]["file"]
    try:
        proc = subprocess.run(
            [
                "latexmk",
                "-pdf",
                "-interaction=nonstopmode",
                "-halt-on-error",
                main_file,
            ],
            cwd=str(paper_root),
            capture_output=True,
            timeout=_BUILD_TIMEOUT_S,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    return proc.returncode == 0


def _severity_of(issue: dict) -> str | None:
    """Effective severity: final if set, else proposed."""
    return issue.get("severity_final") or issue.get("severity_proposed")


def run_gate(paper_root: Path, mechanical_only: bool = False) -> dict:
    """Run gate checks for a paper and return (and persist) a result report."""
    paper_root = Path(paper_root)
    structure = _load_structure(paper_root)

    # -- mechanical build ----------------------------------------------------
    build_ok = _attempt_build(paper_root, structure)

    # -- structural signals --------------------------------------------------
    duplicate_labels = list(structure.get("duplicate_labels", []))
    unresolved_refs = list(structure.get("unresolved_refs", []))
    unresolved_citations = list(structure.get("unresolved_citations", []))
    draft_markers = list(structure.get("draft_markers", []))

    # -- open blocking issues, grouped by (category, severity) ---------------
    open_issues = [
        i for i in ledger.list_issues(paper_root) if i.get("status") in _OPEN_STATUSES
    ]
    blocking_issues = [
        i for i in open_issues if _severity_of(i) in _BLOCKING_SEVERITIES
    ]
    categories_blocking = {i.get("category") for i in blocking_issues}

    # -- unresolved blocking manual checks -----------------------------------
    blocking_manual = [
        c
        for c in ledger.list_manual_checks(paper_root)
        if c.get("blocking") and not c.get("resolved", False)
    ]

    # -- assemble human-readable blockers ------------------------------------
    blockers: list[str] = []
    for c in blocking_manual:
        blockers.append(f"Manual check {c.get('check_id')}: {c.get('question')}")
    for i in blocking_issues:
        blockers.append(
            f"{i.get('issue_id')} [{i.get('category')}/{_severity_of(i)}]: "
            f"{i.get('claim', '')}"
        )
    if build_ok is False:
        blockers.append("LaTeX build failed (latexmk returned non-zero).")
    if duplicate_labels:
        blockers.append(f"Duplicate labels: {', '.join(duplicate_labels)}")
    if unresolved_refs:
        blockers.append(f"Unresolved refs: {', '.join(unresolved_refs)}")
    if unresolved_citations:
        blockers.append(f"Unresolved citations: {', '.join(unresolved_citations)}")
    if draft_markers:
        marker_names = sorted({m.get("marker", "?") for m in draft_markers})
        blockers.append(
            f"{len(draft_markers)} draft marker(s): {', '.join(marker_names)}"
        )

    # -- verdict by priority order (first match wins) ------------------------
    has_build_or_source = bool(
        build_ok is False
        or duplicate_labels
        or unresolved_refs
        or unresolved_citations
    )
    if blocking_manual:
        verdict = "NOT READY: MANUAL CHECK REQUIRED"
    elif "math" in categories_blocking:
        verdict = "NOT READY: MATHEMATICAL ISSUE"
    elif "numerics" in categories_blocking:
        verdict = "NOT READY: NUMERICAL / EXPERIMENT ISSUE"
    elif categories_blocking & {"novelty", "framing"}:
        verdict = "NOT READY: CLAIM / FRAMING ISSUE"
    elif has_build_or_source:
        verdict = "NOT READY: BUILD / SOURCE ISSUE"
    elif draft_markers:
        verdict = "READY AFTER MECHANICAL FIXES"
    else:
        verdict = "READY"

    result = {
        "verdict": verdict,
        "blockers": blockers,
        "signals": {
            "build_ok": build_ok,
            "duplicate_labels": duplicate_labels,
            "unresolved_refs": unresolved_refs,
            "unresolved_citations": unresolved_citations,
            "draft_marker_count": len(draft_markers),
            "blocking_issue_count": len(blocking_issues),
            "blocking_manual_count": len(blocking_manual),
        },
        "mechanical_only": mechanical_only,
    }

    out_path = paths.audit_dir(paper_root) / "final_gate.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    return result
