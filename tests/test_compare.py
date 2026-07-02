"""Tests for version-comparison of paper sources."""

from __future__ import annotations

from pathlib import Path

from papercheck.core.compare import compare_versions, write_compare_report

_OLD_MAIN = r"""\documentclass{article}
\newtheorem{theorem}{Theorem}
\begin{document}
\begin{abstract}Old abstract.\end{abstract}
\begin{theorem}
\label{thm:a}
Statement A.
\end{theorem}
\end{document}
"""

_NEW_MAIN = r"""\documentclass{article}
\newtheorem{theorem}{Theorem}
\begin{document}
\begin{abstract}New and different abstract.\end{abstract}
\begin{theorem}
\label{thm:a}
Statement A, now revised and expanded.
\end{theorem}
\begin{theorem}
\label{thm:b}
Statement B.
\end{theorem}
This work builds on prior art \cite{newref}.
\end{document}
"""


def _write_paper(root: Path, body: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "main.tex").write_text(body, encoding="utf-8")


def test_compare_versions_detects_structural_changes(tmp_path: Path) -> None:
    old = tmp_path / "old"
    new = tmp_path / "new"
    _write_paper(old, _OLD_MAIN)
    _write_paper(new, _NEW_MAIN)

    diff = compare_versions(old, new)

    assert "thm:b" in diff["theorems"]["added"]
    assert "thm:a" in diff["theorems"]["changed"]
    assert diff["abstract"]["status"] == "changed"
    assert "newref" in diff["citations"]["added"]

    # old_root / new_root recorded
    assert diff["old_root"] == str(old)
    assert diff["new_root"] == str(new)


def test_write_compare_report_writes_file(tmp_path: Path) -> None:
    old = tmp_path / "old"
    new = tmp_path / "new"
    _write_paper(old, _OLD_MAIN)
    _write_paper(new, _NEW_MAIN)

    out = write_compare_report(old, new)

    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Version comparison")
    assert "thm:b" in text
    assert "changed" in text


def test_compare_dir_to_itself_is_empty(tmp_path: Path) -> None:
    paper = tmp_path / "paper"
    _write_paper(paper, _OLD_MAIN)

    diff = compare_versions(paper, paper)

    assert diff["theorems"]["added"] == []
    assert diff["theorems"]["removed"] == []
    assert diff["theorems"]["changed"] == []
    assert diff["labels"]["added"] == []
    assert diff["labels"]["removed"] == []
    assert diff["citations"]["added"] == []
    assert diff["citations"]["removed"] == []
    assert diff["abstract"]["status"] == "unchanged"
