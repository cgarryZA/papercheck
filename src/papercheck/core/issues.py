"""Issue submission and lifecycle management."""

from __future__ import annotations

import json
from pathlib import Path

from papercheck.core import ledger, schemas
from papercheck.core.paths import structure_file
from papercheck.core.state import AuditState
from papercheck.core.verify import label_exists, verify_quote

# Map issue category to the issue-id prefix used by the ledger.
_CATEGORY_PREFIX: dict[str, str] = {
    "math": "MATH",
    "numerics": "NUM",
    "novelty": "NOV",
    "notation": "NOTA",
    "hygiene": "HYG",
    "framing": "FRAME",
}


def submit_issue(paper_root: Path, issue: dict) -> dict:
    """Submit an issue for a paper and return the stored issue record.

    Acts as the intake gate: enforces the AUDITING stage, validates the issue
    shape, assigns an id when missing, verifies the quote/label/file against the
    paper's sources, and routes the issue to the proposed or rejected ledger.
    """
    paper_root = Path(paper_root)

    # 1. Stage gate — StateError propagates when missing or below AUDITING.
    AuditState.load(paper_root).require_at_least("AUDITING")

    # 2. Assign an id when absent or blank (before schema validation, since a
    #    blank id fails the schema pattern).
    if not issue.get("issue_id"):
        prefix = _CATEGORY_PREFIX.get(issue.get("category", ""), "MATH")
        issue["issue_id"] = ledger.next_issue_id(paper_root, prefix)

    # 3. Schema gate — ValidationError propagates on a malformed issue.
    schemas.validate(issue, "issue")

    # 4. Verification.
    struct_path = structure_file(paper_root)
    structure: dict | None = None
    if struct_path.is_file():
        structure = json.loads(struct_path.read_text(encoding="utf-8"))

    location = issue["location"]
    target_file = paper_root / location["file"]
    file_exists = target_file.is_file()

    quote_found = verify_quote(
        target_file,
        issue["exact_quote"],
        location.get("line_start"),
        location.get("line_end"),
        slack=2,
    )

    label = location.get("label")
    if not label:
        # No label supplied -> nothing was checked; report unknown, not True.
        label_exists_result = None
    elif structure is None:
        # Cannot verify a label without structure — do not fail on it alone.
        label_exists_result = None
    else:
        label_exists_result = label_exists(structure, label)

    issue["verification"] = {
        "quote_found": quote_found,
        "label_exists": label_exists_result,
        "checked_at": "",
    }

    # 5. Decision.
    label_invalid = bool(label) and structure is not None and label_exists_result is False
    if (not file_exists) or (quote_found is False) or label_invalid:
        issue["status"] = "REJECTED_SOURCE_TARGET_INVALID"
    else:
        issue["status"] = "PROPOSED"

    ledger.save_issue(paper_root, issue)
    return issue
