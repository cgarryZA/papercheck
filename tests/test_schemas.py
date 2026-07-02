"""Tests for JSON-schema validation."""

from __future__ import annotations

import pytest
from jsonschema import ValidationError

from papercheck.core.schemas import validate


def _valid_issue() -> dict:
    return {
        "issue_id": "MATH-1",
        "source_auditors": ["auditor-a"],
        "status": "PROPOSED",
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


def _valid_patch() -> dict:
    return {
        "patch_id": "PATCH-1",
        "accepted_issue_ids": ["MATH-1"],
        "patch_type": "proof",
        "files_changed": ["main.tex"],
    }


def _valid_segment() -> dict:
    return {
        "segment_id": "S1",
        "title": "Introduction",
        "budget": "HIGH",
    }


def _valid_manual_check() -> dict:
    return {
        "check_id": "MANUAL-1",
        "question": "Is the citation real?",
        "blocking": True,
    }


def _valid_state() -> dict:
    return {
        "run_id": "run-123",
        "harness_version": "0.1.0",
        "stage": "INIT",
        "completed_stages": ["INIT"],
    }


_VALID = {
    "issue": _valid_issue,
    "patch": _valid_patch,
    "segment": _valid_segment,
    "manual_check": _valid_manual_check,
    "state": _valid_state,
}


@pytest.mark.parametrize("name", list(_VALID))
def test_valid_instances_pass(name: str) -> None:
    assert validate(_VALID[name](), name) is None


def test_issue_missing_required_raises() -> None:
    bad = _valid_issue()
    del bad["claim"]
    with pytest.raises(ValidationError):
        validate(bad, "issue")


def test_issue_bad_enum_raises() -> None:
    bad = _valid_issue()
    bad["severity_proposed"] = "CATASTROPHIC"
    with pytest.raises(ValidationError):
        validate(bad, "issue")


def test_patch_bad_id_raises() -> None:
    bad = _valid_patch()
    bad["patch_id"] = "P-1"
    with pytest.raises(ValidationError):
        validate(bad, "patch")


def test_segment_bad_budget_raises() -> None:
    bad = _valid_segment()
    bad["budget"] = "EXTREME"
    with pytest.raises(ValidationError):
        validate(bad, "segment")


def test_manual_check_missing_required_raises() -> None:
    bad = _valid_manual_check()
    del bad["question"]
    with pytest.raises(ValidationError):
        validate(bad, "manual_check")


def test_state_bad_stage_raises() -> None:
    bad = _valid_state()
    bad["stage"] = "NOPE"
    with pytest.raises(ValidationError):
        validate(bad, "state")


def test_unknown_schema_raises_value_error() -> None:
    with pytest.raises(ValueError):
        validate({}, "not-a-schema")
