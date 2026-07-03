"""P5.12 — inline `% papercheck: ignore` suppression for draft markers.

Deliberate `??`/TODO that can't reach the PDF (e.g. an unreachable
\\IfFileExists fallback) can be silenced per-line, and the suppressed items are
still recorded (in `suppressed_draft_markers`) rather than dropped silently.
"""

from __future__ import annotations

from pathlib import Path

from papercheck.core import texscan


def _scan(tmp_path: Path, body: str) -> dict:
    (tmp_path / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n" + body + "\n\\end{document}\n",
        encoding="utf-8",
    )
    return texscan.scan(tmp_path)


def _markers(struct: dict) -> set[str]:
    return {m["marker"] for m in struct["draft_markers"]}


def test_trailing_pragma_suppresses_same_line(tmp_path: Path) -> None:
    # The reviewer's case: an unreachable ?? fallback, silenced inline.
    body = (
        "\\IfFileExists{results-macros.tex}{\\input{results-macros.tex}}"
        "{\\providecommand{\\rv}[1]{\\textbf{??}}}  % papercheck: ignore draft-marker"
    )
    struct = _scan(tmp_path, body)
    assert "??" not in _markers(struct)
    assert any(s["marker"] == "??" for s in struct["suppressed_draft_markers"])


def test_pragma_on_line_above_suppresses(tmp_path: Path) -> None:
    body = "% papercheck: ignore draft-marker\nHere is a stray \\textbf{??} token."
    struct = _scan(tmp_path, body)
    assert "??" not in _markers(struct)
    assert len(struct["suppressed_draft_markers"]) == 1


def test_bare_ignore_suppresses_all_kinds(tmp_path: Path) -> None:
    body = "A leftover TODO here.  % papercheck: ignore"
    struct = _scan(tmp_path, body)
    assert "TODO" not in _markers(struct)


def test_unrelated_marker_still_flagged(tmp_path: Path) -> None:
    # A pragma on one line must not silence a marker two lines away.
    body = "% papercheck: ignore draft-marker\n\nA real TODO remains here."
    struct = _scan(tmp_path, body)
    assert "TODO" in _markers(struct)


def test_pragma_line_itself_not_flagged(tmp_path: Path) -> None:
    # "draft" inside "draft-marker" must not be detected as a marker.
    body = "Some ordinary prose.  % papercheck: ignore draft-marker"
    struct = _scan(tmp_path, body)
    assert struct["draft_markers"] == []
    assert struct["suppressed_draft_markers"] == []


def test_claim_trigger_suppression(tmp_path: Path) -> None:
    body = "This bound is optimal.  % papercheck: ignore claim-trigger"
    struct = _scan(tmp_path, body)
    assert all(t["word"] != "optimal" for t in struct["claim_triggers"])
