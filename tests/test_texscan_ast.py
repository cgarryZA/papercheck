"""Robustness tests for the LaTeX-AST-aware TeX scanner.

These guard the upgrade from line/regex scanning to a pylatexenc AST: the
single-line-label bug fix, macro-defined theorem environments, nested
environments, and graceful degradation on malformed input.
"""

from __future__ import annotations

from pathlib import Path

from papercheck.core import texscan

# The full set of keys every scan() result must always carry.
_REQUIRED_KEYS = {
    "paper_root",
    "files",
    "main_candidates",
    "include_graph",
    "sections",
    "theorem_envs",
    "theorem_env_names",
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
}


def _write(root: Path, name: str, body: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / name).write_text(body, encoding="utf-8")


def test_single_line_theorem_label_is_attached(tmp_path: Path) -> None:
    """A single-line theorem with an inline \\label must capture that label.

    This is the historical bug: the label pass ran before the env pass, so a
    same-line ``\\begin{theorem}\\label{...}...\\end{theorem}`` yielded label
    None. The AST attaches the label node inside the env node regardless.
    """
    body = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\begin{theorem}\\label{thm:x} A one-liner. \\end{theorem}\n"
        "\\end{document}\n"
    )
    _write(tmp_path, "main.tex", body)

    result = texscan.scan(tmp_path)

    thms = [t for t in result["theorem_envs"] if t["kind"] == "theorem"]
    assert len(thms) == 1
    assert thms[0]["label"] == "thm:x"
    # The label is also recorded in the flat labels list.
    assert any(lbl["label"] == "thm:x" for lbl in result["labels"])


def test_macro_defined_theorem_env_detected(tmp_path: Path) -> None:
    """An env declared via \\newtheorem is detected with its declared name."""
    body = (
        "\\documentclass{article}\n"
        "\\newtheorem{prop}{Proposition}\n"
        "\\begin{document}\n"
        "\\begin{prop}\n"
        "\\label{p:1}\n"
        "A macro-defined environment.\n"
        "\\end{prop}\n"
        "\\end{document}\n"
    )
    _write(tmp_path, "main.tex", body)

    result = texscan.scan(tmp_path)

    assert "prop" in result["theorem_env_names"]
    props = [t for t in result["theorem_envs"] if t["kind"] == "prop"]
    assert len(props) == 1
    assert props[0]["label"] == "p:1"


def test_nested_environments_detected(tmp_path: Path) -> None:
    """A nested equation inside a theorem: both detected with correct labels."""
    body = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\begin{theorem}\n"
        "\\label{thm:outer}\n"
        "Consider the identity\n"
        "\\begin{equation}\n"
        "\\label{eq:inner}\n"
        "a = b\n"
        "\\end{equation}\n"
        "which holds.\n"
        "\\end{theorem}\n"
        "\\end{document}\n"
    )
    _write(tmp_path, "main.tex", body)

    result = texscan.scan(tmp_path)

    thms = [t for t in result["theorem_envs"] if t["kind"] == "theorem"]
    assert len(thms) == 1
    # The outer theorem keeps its own label, not the nested equation's.
    assert thms[0]["label"] == "thm:outer"

    eqs = [e for e in result["equations"] if e["env"] == "equation"]
    assert len(eqs) == 1
    assert eqs[0]["label"] == "eq:inner"

    # Both labels present in the flat list; both nodes span >= 1 line.
    label_names = {lbl["label"] for lbl in result["labels"]}
    assert {"thm:outer", "eq:inner"} <= label_names
    assert thms[0]["line_end"] >= thms[0]["line_start"]


def test_nested_align_in_proof_detected(tmp_path: Path) -> None:
    """A proof containing an align: the align equation is detected, no crash."""
    body = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\begin{proof}\n"
        "\\begin{align}\n"
        "\\label{eq:steps}\n"
        "x &= y \\\\\n"
        "  &= z\n"
        "\\end{align}\n"
        "\\end{proof}\n"
        "\\end{document}\n"
    )
    _write(tmp_path, "main.tex", body)

    result = texscan.scan(tmp_path)

    aligns = [e for e in result["equations"] if e["env"] == "align"]
    assert len(aligns) == 1
    assert aligns[0]["label"] == "eq:steps"


def test_malformed_unbalanced_env_does_not_raise(tmp_path: Path) -> None:
    """A theorem with no matching \\end must not crash scan(); dict well-formed."""
    body = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "\\begin{theorem}\n"
        "\\label{thm:dangling}\n"
        "This environment is never closed.\n"
        "\\end{document}\n"
    )
    _write(tmp_path, "main.tex", body)

    # Must not raise.
    result = texscan.scan(tmp_path)

    # All contract keys present.
    assert _REQUIRED_KEYS <= set(result.keys())
    # List-typed keys are still lists.
    for key in (
        "main_candidates", "include_graph", "sections", "theorem_envs",
        "labels", "duplicate_labels", "refs", "unresolved_refs", "citations",
        "bib_keys", "unresolved_citations", "unused_bib_keys", "equations",
        "draft_markers", "claim_triggers", "theorem_env_names",
    ):
        assert isinstance(result[key], list)
    assert isinstance(result["files"], dict)


def test_scan_never_raises_on_garbage(tmp_path: Path) -> None:
    """Deeply broken input still yields a well-formed dict with all keys."""
    body = "\\begin{theorem}{{{ \\label{a} \\cite{ \\ref{ \\end{align*}\n"
    _write(tmp_path, "main.tex", body)

    result = texscan.scan(tmp_path)

    assert _REQUIRED_KEYS <= set(result.keys())
    assert result["paper_root"] == str(tmp_path)
