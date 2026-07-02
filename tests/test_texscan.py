"""Tests for the deterministic TeX scanner."""

from __future__ import annotations

import json
from pathlib import Path

from papercheck.core import texscan
from papercheck.core.paths import structure_file

FIXTURE = Path(__file__).parent / "fixtures" / "toy_bad_label_refs"


def test_scan_fixture_detects_planted_defects() -> None:
    result = texscan.scan(FIXTURE)

    # Duplicate label planted in main.tex + sec.tex.
    assert "thm:main" in result["duplicate_labels"]

    # Unresolved ref (no such label).
    assert "fig:nowhere" in result["unresolved_refs"]

    # Unresolved citation (absent from refs.bib).
    assert "ghost2020" in result["unresolved_citations"]

    # Unused bib key.
    assert "jones2018" in result["unused_bib_keys"]

    # At least one theorem environment.
    assert len(result["theorem_envs"]) >= 1

    # At least one draft marker (the % TODO line).
    assert len(result["draft_markers"]) >= 1

    # Claim trigger word "novel" present.
    trigger_words = {t["word"] for t in result["claim_triggers"]}
    assert "novel" in trigger_words

    # main.tex is the top main candidate.
    assert result["main_candidates"][0]["file"] == "main.tex"

    # include_graph links main.tex -> sec.tex.
    assert {"from": "main.tex", "includes": "sec.tex"} in result["include_graph"]


def test_scan_writes_structure_json() -> None:
    result = texscan.scan(FIXTURE)
    out = structure_file(FIXTURE)
    assert out.exists()
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert on_disk["duplicate_labels"] == result["duplicate_labels"]


def test_scan_matches_expected_json() -> None:
    result = texscan.scan(FIXTURE)
    expected = json.loads((FIXTURE / "expected.json").read_text(encoding="utf-8"))
    assert result["duplicate_labels"] == expected["duplicate_labels"]
    assert result["unresolved_refs"] == expected["unresolved_refs"]
    assert result["unresolved_citations"] == expected["unresolved_citations"]
    assert (len(result["draft_markers"]) > 0) == expected["has_draft_marker"]
    assert len(result["theorem_envs"]) >= expected["min_theorem_envs"]


def test_scan_empty_dir_is_well_formed(tmp_path) -> None:
    result = texscan.scan(tmp_path)

    assert result["paper_root"] == str(tmp_path)
    assert result["files"] == {
        "tex": [],
        "bib": [],
        "sty": [],
        "cls": [],
        "figures": [],
    }
    for key in (
        "main_candidates",
        "include_graph",
        "sections",
        "theorem_envs",
        "labels",
        "duplicate_labels",
        "refs",
        "unresolved_refs",
        "citations",
        "bib_keys",
        "unresolved_citations",
        "unused_bib_keys",
        "equations",
        "draft_markers",
        "claim_triggers",
    ):
        assert result[key] == []
    # Defaults are always present even with no files.
    assert "theorem" in result["theorem_env_names"]
    # structure.json is still written.
    assert structure_file(tmp_path).exists()
