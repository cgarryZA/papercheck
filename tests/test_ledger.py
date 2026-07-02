"""Tests for the file-based issue ledger."""

from __future__ import annotations

import pytest

from papercheck.core import ledger
from papercheck.core.paths import issues_dir


def _issue(issue_id: str = "MATH-1", status: str = "PROPOSED") -> dict:
    return {
        "issue_id": issue_id,
        "source_auditors": ["auditor-a"],
        "status": status,
        "severity_proposed": "SERIOUS",
        "category": "math",
        "location": {"file": "main.tex"},
        "exact_quote": "the claim",
        "claim": "a claim",
        "concrete_failure_mode": "it breaks",
        "required_fix": "fix it",
        "patch_locality": "local",
        "confidence": "high",
    }


def test_save_issue_routes_proposed(tmp_path) -> None:
    path = ledger.save_issue(tmp_path, _issue())
    assert path == issues_dir(tmp_path, "proposed") / "MATH-1.json"
    assert path.exists()


def test_move_issue_relocates(tmp_path) -> None:
    ledger.save_issue(tmp_path, _issue())
    old = issues_dir(tmp_path, "proposed") / "MATH-1.json"
    moved = ledger.move_issue(tmp_path, "MATH-1", "ACCEPTED")
    assert moved["status"] == "ACCEPTED"
    assert not old.exists()
    assert (issues_dir(tmp_path, "accepted") / "MATH-1.json").exists()


def test_list_issues_filters(tmp_path) -> None:
    ledger.save_issue(tmp_path, _issue("MATH-1", "PROPOSED"))
    ledger.save_issue(tmp_path, _issue("MATH-2", "ACCEPTED"))
    assert len(ledger.list_issues(tmp_path)) == 2
    proposed = ledger.list_issues(tmp_path, status="PROPOSED")
    assert [i["issue_id"] for i in proposed] == ["MATH-1"]


def test_next_issue_id_increments(tmp_path) -> None:
    assert ledger.next_issue_id(tmp_path, "MATH") == "MATH-1"
    ledger.save_issue(tmp_path, _issue("MATH-1"))
    ledger.save_issue(tmp_path, _issue("MATH-3"))
    assert ledger.next_issue_id(tmp_path, "MATH") == "MATH-4"
    # A different prefix starts fresh.
    assert ledger.next_issue_id(tmp_path, "NUM") == "NUM-1"


def test_load_issue_missing_raises(tmp_path) -> None:
    with pytest.raises(KeyError):
        ledger.load_issue(tmp_path, "MATH-99")


def test_load_issue_round_trips(tmp_path) -> None:
    ledger.save_issue(tmp_path, _issue())
    loaded = ledger.load_issue(tmp_path, "MATH-1")
    assert loaded["issue_id"] == "MATH-1"
