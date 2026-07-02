"""Tests for the mechanical final gate."""

from __future__ import annotations

import shutil
from pathlib import Path

from papercheck.core import ledger
from papercheck.core.gate import run_gate

FIXTURES = Path(__file__).parent / "fixtures"
CLEAN = FIXTURES / "toy_clean_paper"
BAD = FIXTURES / "toy_bad_label_refs"


def _copy(fixture: Path, tmp_path: Path) -> Path:
    dst = tmp_path / fixture.name
    shutil.copytree(fixture, dst)
    # Drop any stale audit artifacts copied along.
    audit = dst / "Paper_Audit"
    if audit.exists():
        shutil.rmtree(audit)
    return dst


def test_clean_paper_is_ready(tmp_path) -> None:
    root = _copy(CLEAN, tmp_path)
    result = run_gate(root, mechanical_only=True)
    # In CI latexmk is absent (build_ok=None -> READY). If latexmk is present
    # and builds, still READY. Never NOT READY for the clean fixture.
    assert result["verdict"] in {"READY", "READY AFTER MECHANICAL FIXES"}
    assert not result["verdict"].startswith("NOT READY")


def test_bad_paper_is_build_source_issue(tmp_path) -> None:
    root = _copy(BAD, tmp_path)
    result = run_gate(root, mechanical_only=True)
    assert result["verdict"] == "NOT READY: BUILD / SOURCE ISSUE"


def _fatal_math_issue() -> dict:
    return {
        "issue_id": "MATH-1",
        "source_auditors": ["formalist"],
        "status": "ACCEPTED",
        "severity_proposed": "FATAL",
        "category": "math",
        "location": {"file": "main.tex"},
        "exact_quote": "the false claim",
        "claim": "a broken claim",
        "concrete_failure_mode": "the proof does not close",
        "required_fix": "fix the proof",
        "patch_locality": "local",
        "confidence": "high",
    }


def _blocking_manual() -> dict:
    return {
        "check_id": "MANUAL-1",
        "question": "Is Theorem 1 actually original?",
        "blocking": True,
        "resolved": False,
    }


def test_manual_check_priority_beats_math_issue(tmp_path) -> None:
    root = tmp_path / "paper"
    root.mkdir()
    # No structure -> scanner runs on an empty dir (clean signals).
    ledger.save_issue(root, _fatal_math_issue())
    ledger.save_manual_check(root, _blocking_manual())

    result = run_gate(root, mechanical_only=True)
    assert result["verdict"] == "NOT READY: MANUAL CHECK REQUIRED"
    assert result["signals"]["blocking_manual_count"] == 1
    assert result["signals"]["blocking_issue_count"] == 1


def test_math_issue_when_no_manual(tmp_path) -> None:
    root = tmp_path / "paper"
    root.mkdir()
    ledger.save_issue(root, _fatal_math_issue())
    result = run_gate(root, mechanical_only=True)
    assert result["verdict"] == "NOT READY: MATHEMATICAL ISSUE"
