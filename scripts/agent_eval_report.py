"""Summarize a completed papercheck audit against a fixture's expectations.

This is a NON-LLM helper for Tier 2 agent-eval (see ``docs/agent_eval.md``). It
reads the issue ledgers written under ``<fixture>/Paper_Audit/issues/*/*.json``
and the fixture's ``expected.json``, then prints:

  * how many issues were proposed / accepted / rejected,
  * whether any accepted issue's location plausibly matches the fixture's
    ``location_hint`` / ``defect_type``, and
  * for ``toy_false_positive_trap``, whether anything was wrongly accepted.

It calls no model and makes no network request. Pure stdlib.

Run as::

    python scripts/agent_eval_report.py tests/fixtures/toy_bad_gronwall_constant
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Issue-status values that count as "accepted" (i.e. survived adjudication).
_ACCEPTED_STATUSES = {
    "ACCEPTED",
    "PATCH_PLANNED",
    "PATCHED",
    "REGRESSION_PASSED",
    "CLOSED",
}

# Issue-status values that count as "rejected".
_REJECTED_STATUSES = {
    "REJECTED",
    "REJECTED_SOURCE_TARGET_INVALID",
}


def _load_json(path: Path) -> dict | None:
    """Return parsed JSON at ``path`` or ``None`` if it can't be read."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _load_issues(audit_dir: Path) -> list[dict]:
    """Load every issue record under ``<audit_dir>/issues/*/*.json``."""
    issues: list[dict] = []
    issues_root = audit_dir / "issues"
    if not issues_root.is_dir():
        return issues
    for issue_path in sorted(issues_root.glob("*/*.json")):
        record = _load_json(issue_path)
        if isinstance(record, dict):
            issues.append(record)
    return issues


def _issue_text(issue: dict) -> str:
    """Return a lowercased blob of an issue's location + descriptive fields."""
    location = issue.get("location") or {}
    parts = [
        str(location.get("section") or ""),
        str(location.get("label") or ""),
        str(location.get("file") or ""),
        str(issue.get("claim") or ""),
        str(issue.get("concrete_failure_mode") or ""),
        str(issue.get("category") or ""),
        str(issue.get("exact_quote") or ""),
    ]
    return " ".join(parts).lower()


def _hint_tokens(text: str) -> list[str]:
    """Split a location hint / defect type into meaningful lowercased tokens."""
    cleaned = "".join(ch if ch.isalnum() else " " for ch in text.lower())
    stop = {"the", "of", "a", "an", "in", "on", "to", "and", "or", "vs", "step"}
    return [tok for tok in cleaned.split() if len(tok) > 2 and tok not in stop]


def _location_matches(issue: dict, expected: dict) -> bool:
    """True if the issue's text overlaps the expected hint/defect tokens."""
    hint = str(expected.get("location_hint") or "")
    defect = str(expected.get("defect_type") or "")
    tokens = set(_hint_tokens(hint)) | set(_hint_tokens(defect))
    if not tokens:
        return False
    blob = _issue_text(issue)
    return any(tok in blob for tok in tokens)


def _bucket(issues: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Partition issues into (proposed, accepted, rejected) lists by status."""
    proposed: list[dict] = []
    accepted: list[dict] = []
    rejected: list[dict] = []
    for issue in issues:
        status = str(issue.get("status") or "").upper()
        if status in _ACCEPTED_STATUSES:
            accepted.append(issue)
        elif status in _REJECTED_STATUSES:
            rejected.append(issue)
        elif status == "PROPOSED":
            proposed.append(issue)
    return proposed, accepted, rejected


def report(fixture_dir: Path) -> int:
    """Print a summary for one audited fixture. Return a process exit code."""
    fixture_dir = fixture_dir.resolve()
    audit_dir = fixture_dir / "Paper_Audit"

    if not audit_dir.is_dir():
        print(f"{fixture_dir.name}: no Paper_Audit found — run the audit first")
        return 0

    expected = _load_json(fixture_dir / "expected.json") or {}
    issues = _load_issues(audit_dir)
    proposed, accepted, rejected = _bucket(issues)

    is_trap = (fixture_dir.name == "toy_false_positive_trap") or (
        str(expected.get("expected_adjudication") or "").upper() == "REJECT"
    )

    print(f"fixture: {fixture_dir.name}")
    print(f"  issues on disk: {len(issues)}")
    print(f"  proposed:       {len(proposed)}")
    print(f"  accepted:       {len(accepted)}")
    print(f"  rejected:       {len(rejected)}")

    if expected:
        hint = expected.get("location_hint")
        defect = expected.get("defect_type")
        if hint or defect:
            print(f"  expected defect: {defect or '?'} @ {hint or '?'}")

    if is_trap:
        wrongly_accepted = accepted
        if wrongly_accepted:
            print(
                f"  TRAP FAIL: {len(wrongly_accepted)} issue(s) wrongly accepted "
                "(expected: none accepted / adjudicator REJECT)"
            )
            for issue in wrongly_accepted:
                print(f"    - {issue.get('issue_id', '?')}: {issue.get('claim', '')}")
            return 0
        print("  TRAP OK: nothing accepted (adjudicator rejected as expected)")
        return 0

    matches = [issue for issue in accepted if _location_matches(issue, expected)]
    if matches:
        print(f"  DEFECT FOUND: {len(matches)} accepted issue(s) match the expected location")
        for issue in matches:
            loc = issue.get("location") or {}
            where = loc.get("section") or loc.get("label") or loc.get("file") or "?"
            print(f"    - {issue.get('issue_id', '?')} @ {where}: {issue.get('claim', '')}")
    elif accepted:
        print(
            "  NO LOCATION MATCH: accepted issue(s) exist but none clearly match "
            "the expected location — review manually against expected.json"
        )
    else:
        print("  DEFECT MISSED: no accepted issues (expected the planted defect to be found)")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "fixture_dir",
        type=Path,
        help="Path to an audited fixture directory (contains Paper_Audit/).",
    )
    args = parser.parse_args(argv)
    return report(args.fixture_dir)


if __name__ == "__main__":
    sys.exit(main())
