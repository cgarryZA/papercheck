"""Deterministic replay of the semantic-fixture agent eval (no LLM, no API key).

Replays the model-derived findings in ``eval/findings.json`` through the real
harness and asserts the expected outcomes:

  * the three real-defect fixtures each get exactly one ACCEPTED issue whose
    location matches the fixture's ``expected.json``, and no finding fails
    quote verification, and
  * the false-positive trap gets nothing accepted (adjudicator REJECT).

This does NOT re-derive findings with a model — that is the live agent-eval in
``docs/agent_eval.md``. What it guards for free is the intake gate + adjudication
wiring and fixture-source drift: if a recorded ``exact_quote`` stops matching a
fixture's source, ``submit_issue`` rejects it as REJECTED_SOURCE_TARGET_INVALID
and this test fails.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _p in (_REPO / "eval", _REPO / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import agent_eval_report  # noqa: E402  (from scripts/)
import run_eval  # noqa: E402  (from eval/)

_FIXTURES = _REPO / "tests" / "fixtures"
_FINDINGS = json.loads((_REPO / "eval" / "findings.json").read_text(encoding="utf-8"))["fixtures"]

_REAL_DEFECTS = [
    "toy_bad_gronwall_constant",
    "toy_missing_assumption",
    "toy_overclaimed_abstract",
]


def _prepare(tmp_path: Path, name: str) -> Path:
    dst = tmp_path / name
    shutil.copytree(_FIXTURES / name, dst)
    audit = dst / "Paper_Audit"
    if audit.exists():
        shutil.rmtree(audit)
    return dst


@pytest.mark.parametrize("name", _REAL_DEFECTS)
def test_real_defect_found_and_accepted(tmp_path: Path, name: str) -> None:
    paper = _prepare(tmp_path, name)
    result = run_eval.audit_fixture(paper, _FINDINGS[name])
    assert result["invalid"] == [], f"{name}: findings failed quote verification"
    assert len(result["accepted"]) == 1, f"{name}: expected one accepted defect"

    expected = json.loads((paper / "expected.json").read_text(encoding="utf-8"))
    accepted = [
        i for i in agent_eval_report._load_issues(paper / "Paper_Audit")
        if str(i.get("status", "")).upper() in agent_eval_report._ACCEPTED_STATUSES
    ]
    assert accepted, f"{name}: no accepted issue on disk"
    assert any(
        agent_eval_report._location_matches(i, expected) for i in accepted
    ), f"{name}: accepted issue did not match expected location"


def test_false_positive_trap_rejected(tmp_path: Path) -> None:
    name = "toy_false_positive_trap"
    paper = _prepare(tmp_path, name)
    result = run_eval.audit_fixture(paper, _FINDINGS[name])
    assert result["invalid"] == [], "trap: finding failed quote verification"
    assert result["accepted"] == [], "trap: an issue was wrongly accepted"
    assert len(result["rejected"]) == 1, "trap: expected the objection to be rejected"
