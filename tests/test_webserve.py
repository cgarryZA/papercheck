"""Tests for the interactive web UI (``papercheck.core.webserve``).

These tests exercise the two pure functions (:func:`build_page`,
:func:`read_source_window`) and the socket-free :func:`_route` helper directly,
so nothing binds a long-lived socket or blocks on ``serve_forever``.
"""

from __future__ import annotations

import json
from urllib.parse import quote

import pytest

from papercheck.core import ledger, paths
from papercheck.core.webserve import _route, build_page, read_source_window


def _issue(claim: str = "c") -> dict:
    return {
        "issue_id": "MATH-1",
        "source_auditors": ["formalist"],
        "status": "PROPOSED",
        "severity_proposed": "SERIOUS",
        "category": "math",
        "location": {
            "file": "x.tex",
            "line_start": 3,
            "line_end": 5,
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
    paths.segments_file(paper_root).write_text(json.dumps(segments), encoding="utf-8")
    ledger.save_issue(paper_root, _issue(claim=claim))


# -- build_page -----------------------------------------------------------


def test_build_page_contains_expected_content(tmp_path) -> None:
    _seed(tmp_path)
    page = build_page(tmp_path)
    assert isinstance(page, str)
    assert "READY" in page
    assert "MATH-1" in page
    assert "Intro Segment" in page
    assert "<html" in page
    assert "</html>" in page
    # Interactive row attributes are present server-side.
    assert 'data-status=\'PROPOSED\'' in page or 'data-status="PROPOSED"' in page


def test_build_page_on_empty_root(tmp_path) -> None:
    page = build_page(tmp_path)
    assert isinstance(page, str)
    assert "<html" in page
    assert "No verdict available" in page


def test_build_page_xss_safe(tmp_path) -> None:
    _seed(tmp_path, claim="</script><script>alert(1)")
    page = build_page(tmp_path)
    # The raw closing/opening script sequence must never appear unescaped,
    # whether in the visible HTML or the embedded JSON blob.
    assert "</script><script>" not in page


# -- read_source_window ---------------------------------------------------


def test_read_source_window_valid(tmp_path) -> None:
    (tmp_path / "x.tex").write_text("l1\nl2\nl3\nl4\nl5\n", encoding="utf-8")
    out = read_source_window(tmp_path, "x.tex", 2, 4)
    assert out["file"] == "x.tex"
    assert out["line_start"] == 2
    assert out["line_end"] == 4
    assert out["text"] == "l2\nl3\nl4"


def test_read_source_window_jail(tmp_path) -> None:
    with pytest.raises(ValueError, match="escapes paper root"):
        read_source_window(tmp_path, "../../etc/passwd", 1, 5)


def test_read_source_window_span_capped(tmp_path) -> None:
    (tmp_path / "big.tex").write_text(
        "\n".join(f"line{i}" for i in range(1, 1001)) + "\n", encoding="utf-8"
    )
    out = read_source_window(tmp_path, "big.tex", 1, 1000)
    assert out["line_start"] == 1
    assert out["line_end"] == 400
    assert len(out["text"].splitlines()) == 400


# -- routing (socket-free) ------------------------------------------------


def test_route_index(tmp_path) -> None:
    _seed(tmp_path)
    status, content_type, body = _route(tmp_path, "/")
    assert status == 200
    assert "text/html" in content_type
    assert b"MATH-1" in body


def test_route_state(tmp_path) -> None:
    _seed(tmp_path)
    state_obj = {"stage": "gate", "harness_version": "9.9"}
    paths.state_file(tmp_path).write_text(json.dumps(state_obj), encoding="utf-8")
    status, content_type, body = _route(tmp_path, "/api/state")
    assert status == 200
    assert "application/json" in content_type
    assert json.loads(body)["stage"] == "gate"


def test_route_source_valid(tmp_path) -> None:
    (tmp_path / "x.tex").write_text("a\nb\nc\nd\n", encoding="utf-8")
    status, content_type, body = _route(tmp_path, "/api/source?file=x.tex&start=2&end=3")
    assert status == 200
    assert "application/json" in content_type
    payload = json.loads(body)
    assert payload["text"] == "b\nc"


def test_route_source_jailed(tmp_path) -> None:
    escape = quote("../../etc/passwd")
    status, _content_type, body = _route(
        tmp_path, f"/api/source?file={escape}&start=1&end=5"
    )
    assert status == 403
    assert b"escapes" in body


def test_route_source_bad_params(tmp_path) -> None:
    status, _content_type, _body = _route(tmp_path, "/api/source?file=x.tex")
    assert status == 400


def test_route_unknown_path(tmp_path) -> None:
    status, _content_type, _body = _route(tmp_path, "/nope")
    assert status == 404
