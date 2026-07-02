"""Tests for the HTML audit report generator."""

from __future__ import annotations

import json

from papercheck.core import ledger, paths
from papercheck.core.html_report import render_html


def _issue(claim: str = "c") -> dict:
    return {
        "issue_id": "MATH-1",
        "source_auditors": ["formalist"],
        "status": "PROPOSED",
        "severity_proposed": "SERIOUS",
        "category": "math",
        "location": {
            "file": "x.tex",
            "line_start": 1,
            "line_end": 1,
            "section": None,
            "label": None,
        },
        "exact_quote": "q",
        "claim": claim,
        "concrete_failure_mode": "f",
        "required_fix": "r",
        "patch_locality": "local",
        "confidence": "high",
    }


def _seed(paper_root, *, claim: str = "c") -> None:
    audit = paths.audit_dir(paper_root)
    audit.mkdir(parents=True, exist_ok=True)
    gate = {
        "verdict": "READY",
        "blockers": [],
        "signals": {
            "build_ok": True,
            "duplicate_labels": [],
            "unresolved_refs": [],
            "unresolved_citations": [],
            "draft_marker_count": 0,
            "blocking_issue_count": 0,
            "blocking_manual_count": 0,
        },
    }
    (audit / "final_gate.json").write_text(json.dumps(gate), encoding="utf-8")
    segments = [{"segment_id": "S1", "title": "Intro Segment", "budget": "HIGH"}]
    paths.segments_file(paper_root).write_text(
        json.dumps(segments), encoding="utf-8"
    )
    ledger.save_issue(paper_root, _issue(claim=claim))


def test_render_html_writes_report(tmp_path) -> None:
    _seed(tmp_path)
    out = render_html(tmp_path)
    assert out.exists()
    assert out == paths.audit_dir(tmp_path) / "report" / "index.html"


def test_report_contains_expected_content(tmp_path) -> None:
    _seed(tmp_path)
    out = render_html(tmp_path)
    text = out.read_text(encoding="utf-8")
    assert "READY" in text
    assert "MATH-1" in text
    assert "Intro Segment" in text
    assert "<html" in text
    assert "</html>" in text


def test_render_html_on_empty_root(tmp_path) -> None:
    out = render_html(tmp_path)
    assert out.exists()
    assert out == paths.audit_dir(tmp_path) / "report" / "index.html"
    text = out.read_text(encoding="utf-8")
    assert "<html" in text
    assert "No verdict available" in text


def test_dynamic_text_is_escaped(tmp_path) -> None:
    _seed(tmp_path, claim="<script>alert(1)</script>")
    out = render_html(tmp_path)
    text = out.read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in text
    assert "&lt;script&gt;" in text
