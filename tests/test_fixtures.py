"""Structural/parse checks for the planted-defect eval fixtures.

These assert only that each fixture scans into a well-formed structure and that
its ``expected.json`` loads and documents a defect. The *semantic* defect
detection (does an auditor actually catch the planted flaw?) is validated later
by the agent-eval procedure, not here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from papercheck.core import texscan

FIXTURES_DIR = Path(__file__).parent / "fixtures"

NEW_FIXTURES = [
    "toy_bad_gronwall_constant",
    "toy_missing_assumption",
    "toy_overclaimed_abstract",
    "toy_false_positive_trap",
]

# Keys that count as "documenting the planted defect" in an expected.json.
_DOCUMENTED_KEYS = {"defect_type", "trap", "expected_adjudication"}


@pytest.mark.parametrize("name", NEW_FIXTURES)
def test_fixture_scans_to_wellformed_structure(name: str) -> None:
    fixture_dir = FIXTURES_DIR / name
    assert fixture_dir.is_dir(), f"missing fixture dir: {fixture_dir}"

    result = texscan.scan(fixture_dir)

    assert isinstance(result, dict)
    # Well-formed structure: the keys downstream phases rely on.
    for key in ("sections", "theorem_envs"):
        assert key in result, f"{name}: structure missing {key!r} key"
    assert isinstance(result["sections"], list)
    assert isinstance(result["theorem_envs"], list)
    # Each toy paper has at least one theorem-like environment.
    assert len(result["theorem_envs"]) >= 1, f"{name}: no theorem envs found"


@pytest.mark.parametrize("name", NEW_FIXTURES)
def test_fixture_expected_json_loads_and_documents_defect(name: str) -> None:
    expected_path = FIXTURES_DIR / name / "expected.json"
    assert expected_path.is_file(), f"missing expected.json: {expected_path}"

    data = json.loads(expected_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert _DOCUMENTED_KEYS & data.keys(), (
        f"{name}: expected.json must document the defect via one of "
        f"{sorted(_DOCUMENTED_KEYS)}"
    )
    # The primary fixtures use "defect_type"; the trap uses it too ("none").
    assert "defect_type" in data, f"{name}: expected.json missing 'defect_type'"
