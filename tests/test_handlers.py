"""Tests for the transport-free MCP handler logic."""

from __future__ import annotations

import pytest

from papercheck.core.state import AuditState, StateError
from papercheck.mcp_server import handlers

_SENTENCE = "The convergence rate is provably optimal under mild assumptions."


def _write_body(tmp_path):
    body = tmp_path / "body.tex"
    body.write_text(
        f"\\section{{Intro}}\nIntro line.\n{_SENTENCE}\nAnother line.\n",
        encoding="utf-8",
    )
    return body


def _issue(**overrides) -> dict:
    issue = {
        "issue_id": "",
        "source_auditors": ["auditor-a"],
        "status": "PROPOSED",
        "severity_proposed": "SERIOUS",
        "category": "math",
        "location": {"file": "body.tex"},
        "exact_quote": _SENTENCE,
        "claim": "a claim",
        "concrete_failure_mode": "it breaks",
        "required_fix": "fix it",
        "patch_locality": "local",
        "confidence": "high",
    }
    issue.update(overrides)
    return issue


def _patch(issue_ids, **overrides) -> dict:
    patch = {
        "patch_id": "PATCH-1",
        "accepted_issue_ids": list(issue_ids),
        "patch_type": "proof",
        "files_changed": ["body.tex"],
    }
    patch.update(overrides)
    return patch


def _pipeline_to_auditing(tmp_path):
    """init -> scan -> segments -> inventory -> AUDITING; return submitted issue."""
    _write_body(tmp_path)
    handlers.init_audit(tmp_path, run_id="run-1")
    handlers.run_scan(tmp_path)
    handlers.propose_segments(tmp_path)
    handlers.save_inventory_record(tmp_path, {"note": "seed"})
    handlers.advance_stage(tmp_path, "AUDITING")


def test_submit_before_init_raises(tmp_path) -> None:
    _write_body(tmp_path)
    with pytest.raises(StateError):
        handlers.submit_issue(tmp_path, _issue())


def test_happy_path_to_plan_patch(tmp_path) -> None:
    _pipeline_to_auditing(tmp_path)

    submitted = handlers.submit_issue(tmp_path, _issue())
    assert submitted["status"] == "PROPOSED"
    issue_id = submitted["issue_id"]

    adjudicated = handlers.adjudicate_issue(
        tmp_path,
        issue_id,
        decision="ACCEPT",
        rationale="valid",
        adjudicator="human",
    )
    assert adjudicated["status"] == "ACCEPTED"
    assert adjudicated["adjudication"]["decision"] == "ACCEPT"
    assert handlers.get_issue(tmp_path, issue_id)["status"] == "ACCEPTED"

    handlers.advance_stage(tmp_path, "SYNTHESIZED")
    handlers.advance_stage(tmp_path, "ADJUDICATED")

    patch = handlers.plan_patch(tmp_path, _patch([issue_id]))
    assert patch["patch_id"] == "PATCH-1"
    assert handlers.get_issue(tmp_path, issue_id)["status"] == "PATCH_PLANNED"


def test_plan_patch_before_adjudicated_raises(tmp_path) -> None:
    _pipeline_to_auditing(tmp_path)
    submitted = handlers.submit_issue(tmp_path, _issue())
    handlers.adjudicate_issue(
        tmp_path, submitted["issue_id"], "ACCEPT", "ok", "human"
    )
    # State is still AUDITING — patch planning is gated on ADJUDICATED.
    with pytest.raises(StateError):
        handlers.plan_patch(tmp_path, _patch([submitted["issue_id"]]))


def test_plan_patch_non_accepted_issue_raises(tmp_path) -> None:
    _pipeline_to_auditing(tmp_path)
    submitted = handlers.submit_issue(tmp_path, _issue())
    # Leave the issue PROPOSED (not adjudicated), but reach ADJUDICATED stage.
    handlers.advance_stage(tmp_path, "SYNTHESIZED")
    handlers.advance_stage(tmp_path, "ADJUDICATED")
    with pytest.raises(ValueError):
        handlers.plan_patch(tmp_path, _patch([submitted["issue_id"]]))


def test_submit_missing_quote_rejected(tmp_path) -> None:
    _pipeline_to_auditing(tmp_path)
    result = handlers.submit_issue(
        tmp_path, _issue(exact_quote="text that never appears anywhere at all")
    )
    assert result["status"] == "REJECTED_SOURCE_TARGET_INVALID"


def test_read_source_window_jail(tmp_path) -> None:
    _pipeline_to_auditing(tmp_path)
    with pytest.raises(ValueError):
        handlers.read_source_window(
            tmp_path, "../../secret.txt", 1, 5
        )


def test_read_source_window_ok(tmp_path) -> None:
    _pipeline_to_auditing(tmp_path)
    window = handlers.read_source_window(tmp_path, "body.tex", 1, 2)
    assert window["line_start"] == 1
    assert "Intro" in window["text"]


def test_manual_check_gate_and_resolution(tmp_path) -> None:
    _pipeline_to_auditing(tmp_path)
    check = handlers.add_manual_check(
        tmp_path, question="Is Lemma 2 sound?", blocking=True
    )
    verdict = handlers.run_gate(tmp_path)["verdict"]
    assert verdict == "NOT READY: MANUAL CHECK REQUIRED"

    handlers.resolve_manual_check(tmp_path, check["check_id"], "verified sound")
    verdict2 = handlers.run_gate(tmp_path)["verdict"]
    assert verdict2 != "NOT READY: MANUAL CHECK REQUIRED"


def test_save_inventory_record_after_auditing(tmp_path) -> None:
    import json

    from papercheck.core import paths

    _write_body(tmp_path)
    handlers.init_audit(tmp_path, run_id="run-1")
    handlers.run_scan(tmp_path)
    handlers.propose_segments(tmp_path)
    handlers.save_inventory_record(tmp_path, {"note": "first"})
    handlers.advance_stage(tmp_path, "AUDITING")

    # Must NOT raise despite being past INVENTORIED.
    handlers.save_inventory_record(tmp_path, {"note": "second"})

    inv_path = paths.audit_dir(tmp_path) / "inventory.json"
    records = json.loads(inv_path.read_text(encoding="utf-8"))
    assert len(records) == 2
    assert AuditState.load(tmp_path).stage == "AUDITING"


def test_resolve_manual_check_records_resolver(tmp_path) -> None:
    _pipeline_to_auditing(tmp_path)
    check = handlers.add_manual_check(tmp_path, question="Is Lemma 2 sound?", blocking=True)
    resolved = handlers.resolve_manual_check(
        tmp_path, check["check_id"], "verified sound", resolved_by="alice"
    )
    assert resolved["resolved"] is True
    assert resolved["resolved_by"] == "alice"
    stored = handlers.get_manual_checks(tmp_path)[0]
    assert stored["resolved_by"] == "alice"


def test_list_prompts_empty_is_graceful(tmp_path) -> None:
    # prompts/ directory may not exist yet — must return a list, not crash.
    assert isinstance(handlers.list_prompts(), list)


def test_init_scaffolds_directories(tmp_path) -> None:
    _write_body(tmp_path)
    state = handlers.init_audit(tmp_path, run_id="run-x")
    assert state["stage"] == "INIT"
    from papercheck.core import paths

    for status in ("proposed", "accepted", "rejected", "manual_check"):
        assert paths.issues_dir(tmp_path, status).is_dir()
    assert paths.patches_dir(tmp_path).is_dir()
    assert paths.manual_checks_dir(tmp_path).is_dir()
    assert paths.reports_dir(tmp_path).is_dir()
    assert AuditState.load(tmp_path).stage == "INIT"
