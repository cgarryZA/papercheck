"""Tests for the heuristic segmenter."""

from __future__ import annotations

from pathlib import Path

from papercheck.core import segments as segments_mod
from papercheck.core import texscan
from papercheck.core.schemas import validate

FIXTURE = Path(__file__).parent / "fixtures" / "toy_clean_paper"


def test_propose_segments_returns_valid_records() -> None:
    structure = texscan.scan(FIXTURE)
    segs = segments_mod.propose_segments(structure)
    assert len(segs) >= 1
    for seg in segs:
        validate(seg, "segment")
    ids = [s["segment_id"] for s in segs]
    assert ids == sorted(ids)
    assert ids[0] == "S0"


def test_clean_paper_low_budget() -> None:
    structure = texscan.scan(FIXTURE)
    segs = segments_mod.propose_segments(structure)
    # One theorem, no equations -> low risk everywhere.
    assert all(s["budget"] == "LOW" for s in segs)


def test_many_theorems_yield_high_budget() -> None:
    # A hand-built structure with many theorems + equations should clear the
    # HIGH threshold (risk = 3*theorems + 2*equations = 3*4 + 2*2 = 16 >= 12).
    structure = {
        "files": {"tex": ["main.tex"]},
        "main_candidates": [{"file": "main.tex", "score": 10, "reasons": []}],
        "sections": [
            {"level": "section", "title": "Dense Section", "file": "main.tex", "line": 5}
        ],
        "theorem_envs": [
            {"kind": "theorem", "file": "main.tex", "line_start": 10, "line_end": 12},
            {"kind": "lemma", "file": "main.tex", "line_start": 14, "line_end": 16},
            {"kind": "proposition", "file": "main.tex", "line_start": 18, "line_end": 20},
            {"kind": "corollary", "file": "main.tex", "line_start": 22, "line_end": 24},
        ],
        "equations": [
            {"env": "equation", "file": "main.tex", "line_start": 26, "line_end": 27},
            {"env": "align", "file": "main.tex", "line_start": 28, "line_end": 30},
        ],
        "claim_triggers": [],
        "labels": [],
    }
    segs = segments_mod.propose_segments(structure)
    dense = next(s for s in segs if s["title"] == "Dense Section")
    assert dense["budget"] == "HIGH"
    assert dense["risk_score"] >= 12
    assert "domain_specialist" in dense["auditors"]
    validate(dense, "segment")


def test_write_segments_persists(tmp_path) -> None:
    import json
    import shutil

    dst = tmp_path / "paper"
    shutil.copytree(FIXTURE, dst)
    structure = texscan.scan(dst)
    records = segments_mod.write_segments(dst, structure)
    from papercheck.core.paths import segments_file

    out = segments_file(dst)
    assert out.exists()
    on_disk = json.loads(out.read_text(encoding="utf-8"))
    assert on_disk == records
