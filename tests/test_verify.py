"""Tests for quote and label verification helpers."""

from __future__ import annotations

from papercheck.core.verify import label_exists, normalize_ws, verify_quote


def test_normalize_ws_collapses_runs() -> None:
    assert normalize_ws("  a\t\tb\n\nc  ") == "a b c"
    assert normalize_ws("\n\t  ") == ""


def test_exact_match(tmp_path) -> None:
    f = tmp_path / "body.tex"
    f.write_text("The quick brown fox jumps.", encoding="utf-8")
    assert verify_quote(f, "quick brown fox") is True


def test_match_despite_whitespace(tmp_path) -> None:
    f = tmp_path / "body.tex"
    f.write_text("The quick\n    brown\t\tfox   jumps.", encoding="utf-8")
    # Quote written with entirely different whitespace still matches.
    assert verify_quote(f, "quick brown fox jumps") is True


def test_quote_not_present(tmp_path) -> None:
    f = tmp_path / "body.tex"
    f.write_text("The quick brown fox.", encoding="utf-8")
    assert verify_quote(f, "lazy dog") is False


def test_quote_outside_window_then_slack(tmp_path) -> None:
    f = tmp_path / "body.tex"
    f.write_text(
        "line one\nline two\nthe needle here\nline four\nline five\n",
        encoding="utf-8",
    )
    # Window lines 1-1 does not include the needle on line 3.
    assert verify_quote(f, "needle", line_start=1, line_end=1, slack=0) is False
    # Widening slack to 2 pulls line 3 into the window.
    assert verify_quote(f, "needle", line_start=1, line_end=1, slack=2) is True


def test_missing_file(tmp_path) -> None:
    assert verify_quote(tmp_path / "nope.tex", "anything") is False


def test_empty_quote(tmp_path) -> None:
    f = tmp_path / "body.tex"
    f.write_text("some content", encoding="utf-8")
    assert verify_quote(f, "") is False
    assert verify_quote(f, "   \n\t ") is False


def test_label_exists_string_list() -> None:
    structure = {"labels": ["eq:main", "thm:key"]}
    assert label_exists(structure, "eq:main") is True
    assert label_exists(structure, "eq:missing") is False


def test_label_exists_dict_list() -> None:
    structure = {"labels": [{"label": "eq:main"}, {"label": "thm:key"}]}
    assert label_exists(structure, "thm:key") is True
    assert label_exists(structure, "eq:missing") is False


def test_label_exists_missing_key() -> None:
    assert label_exists({}, "eq:main") is False
