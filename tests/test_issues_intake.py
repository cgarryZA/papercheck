"""Tests for the issue intake gate."""

from __future__ import annotations

import json

import pytest

from papercheck.core import ledger
from papercheck.core.issues import submit_issue
from papercheck.core.paths import issues_dir, structure_file
from papercheck.core.state import AuditState, StateError

_SENTENCE = "The convergence rate is provably optimal under mild assumptions."


def _make_paper(tmp_path):
    """Create body.tex + structure.json and advance state to AUDITING."""
    body = tmp_path / "body.tex"
    body.write_text(f"Intro line.\n{_SENTENCE}\nAnother line.\n", encoding="utf-8")

    struct = structure_file(tmp_path)
    struct.parent.mkdir(parents=True, exist_ok=True)
    struct.write_text(json.dumps({"labels": ["thm:main"]}), encoding="utf-8")

    state = AuditState.init(
        tmp_path, run_id="run-1", harness_version="0.0.0", git_commit=None
    )
    for stage in ("SCANNED", "SEGMENTED", "INVENTORIED", "AUDITING"):
        state.advance(stage)
    return tmp_path


def _issue(**overrides) -> dict:
    issue = {
        "issue_id": "",
        "source_auditors": ["auditor-a"],
        "status": "PROPOSED",
        "severity_proposed": "SERIOUS",
        "category": "math",
        "location": {"file": "body.tex", "label": "thm:main"},
        "exact_quote": _SENTENCE,
        "claim": "a claim",
        "concrete_failure_mode": "it breaks",
        "required_fix": "fix it",
        "patch_locality": "local",
        "confidence": "high",
    }
    issue.update(overrides)
    return issue


def test_valid_issue_proposed(tmp_path) -> None:
    root = _make_paper(tmp_path)
    result = submit_issue(root, _issue())
    assert result["status"] == "PROPOSED"
    assert result["verification"]["quote_found"] is True
    assert result["verification"]["label_exists"] is True
    landed = issues_dir(root, "proposed") / f"{result['issue_id']}.json"
    assert landed.is_file()


def test_missing_quote_rejected(tmp_path) -> None:
    root = _make_paper(tmp_path)
    result = submit_issue(root, _issue(exact_quote="this text never appears anywhere"))
    assert result["status"] == "REJECTED_SOURCE_TARGET_INVALID"
    assert result["verification"]["quote_found"] is False
    landed = issues_dir(root, "rejected") / f"{result['issue_id']}.json"
    assert landed.is_file()


def test_nonexistent_file_rejected(tmp_path) -> None:
    root = _make_paper(tmp_path)
    result = submit_issue(root, _issue(location={"file": "ghost.tex"}))
    assert result["status"] == "REJECTED_SOURCE_TARGET_INVALID"
    assert (issues_dir(root, "rejected") / f"{result['issue_id']}.json").is_file()


def test_submit_before_auditing_raises(tmp_path) -> None:
    body = tmp_path / "body.tex"
    body.write_text(_SENTENCE + "\n", encoding="utf-8")
    AuditState.init(tmp_path, run_id="run-1", harness_version="0.0.0", git_commit=None)
    with pytest.raises(StateError):
        submit_issue(tmp_path, _issue())


def test_auto_assigns_id_with_prefix(tmp_path) -> None:
    root = _make_paper(tmp_path)
    result = submit_issue(root, _issue(category="numerics", location={"file": "body.tex"}))
    assert result["issue_id"] == "NUM-1"
    # A subsequent one increments.
    result2 = submit_issue(root, _issue(category="numerics", location={"file": "body.tex"}))
    assert result2["issue_id"] == "NUM-2"


def test_preserves_existing_id(tmp_path) -> None:
    root = _make_paper(tmp_path)
    result = submit_issue(root, _issue(issue_id="MATH-42"))
    assert result["issue_id"] == "MATH-42"
    assert ledger.load_issue(root, "MATH-42")["issue_id"] == "MATH-42"
