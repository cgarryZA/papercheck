"""Structural comparison between two versions of a paper.

Given an ``old`` and ``new`` paper root, this module runs the deterministic
:func:`papercheck.core.texscan.scan` on both and computes a structural diff
(theorems, abstract, labels, citations, sections, equations). It never crashes
on missing files -- unreadable sources degrade gracefully to empty text.

Stdlib only.
"""

from __future__ import annotations

import re
from pathlib import Path

from papercheck.core import paths, texscan

_ABSTRACT_RE = re.compile(
    r"\\begin\{abstract\}(.*?)\\end\{abstract\}",
    re.DOTALL,
)


def _normalize(text: str) -> str:
    """Collapse all runs of whitespace to single spaces and strip ends."""
    return " ".join(text.split())


def _read_lines(path: Path) -> list[str]:
    """Read a file's lines, tolerating missing/unreadable files."""
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _theorem_body(root: Path, entry: dict) -> str:
    """Return the normalized source text of a theorem env's line span."""
    rel = entry.get("file")
    if not rel:
        return ""
    start = entry.get("line_start")
    end = entry.get("line_end")
    if not isinstance(start, int) or not isinstance(end, int):
        return ""
    lines = _read_lines(Path(root) / rel)
    if not lines:
        return ""
    # line numbers are 1-based, inclusive.
    lo = max(start - 1, 0)
    hi = min(end, len(lines))
    if lo >= hi:
        # best-effort: single-line env recorded with end == start
        lo = min(max(start - 1, 0), len(lines) - 1)
        hi = lo + 1
    return _normalize("\n".join(lines[lo:hi]))


def _labeled_theorems(structure: dict, root: Path) -> dict[str, str]:
    """Map theorem label -> normalized body text for labeled theorem envs."""
    out: dict[str, str] = {}
    for entry in structure.get("theorem_envs", []):
        label = entry.get("label")
        if not label:
            continue
        # keep the first occurrence of a given label (deterministic by scan order)
        out.setdefault(label, _theorem_body(root, entry))
    return out


def _extract_abstract(structure: dict, root: Path) -> str | None:
    """Return the normalized abstract text (first occurrence), or None."""
    tex_files = structure.get("files", {}).get("tex", [])
    for rel in tex_files:
        try:
            text = (Path(root) / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        m = _ABSTRACT_RE.search(text)
        if m is not None:
            return _normalize(m.group(1))
    return None


def _cite_keys(structure: dict) -> set[str]:
    """Set of cite keys used in the document."""
    return {c.get("key") for c in structure.get("citations", []) if c.get("key")}


def _section_titles(structure: dict) -> set[str]:
    """Set of section titles in the document."""
    return {s.get("title", "") for s in structure.get("sections", [])}


def _label_names(structure: dict) -> set[str]:
    """Set of label names defined in the document."""
    return {lbl.get("label") for lbl in structure.get("labels", []) if lbl.get("label")}


def compare_versions(old_root: Path, new_root: Path) -> dict:
    """Compare two paper versions and return a structural diff dict."""
    old_root = Path(old_root)
    new_root = Path(new_root)

    old = texscan.scan(old_root)
    new = texscan.scan(new_root)

    # -- theorems (matched by label) -----------------------------------------
    old_thms = _labeled_theorems(old, old_root)
    new_thms = _labeled_theorems(new, new_root)
    old_thm_labels = set(old_thms)
    new_thm_labels = set(new_thms)

    thm_added = sorted(new_thm_labels - old_thm_labels)
    thm_removed = sorted(old_thm_labels - new_thm_labels)
    thm_changed = sorted(
        lbl
        for lbl in (old_thm_labels & new_thm_labels)
        if old_thms[lbl] != new_thms[lbl]
    )

    theorems = {
        "added": thm_added,
        "removed": thm_removed,
        "changed": thm_changed,
    }

    # -- abstract ------------------------------------------------------------
    old_abstract = _extract_abstract(old, old_root)
    new_abstract = _extract_abstract(new, new_root)
    if old_abstract is None and new_abstract is None:
        abstract_status = "absent"
    elif old_abstract == new_abstract:
        abstract_status = "unchanged"
    else:
        abstract_status = "changed"
    abstract = {"status": abstract_status}

    # -- labels --------------------------------------------------------------
    old_labels = _label_names(old)
    new_labels = _label_names(new)
    labels = {
        "added": sorted(new_labels - old_labels),
        "removed": sorted(old_labels - new_labels),
    }

    # -- citations -----------------------------------------------------------
    old_cites = _cite_keys(old)
    new_cites = _cite_keys(new)
    citations = {
        "added": sorted(new_cites - old_cites),
        "removed": sorted(old_cites - new_cites),
    }

    # -- sections ------------------------------------------------------------
    old_sections = _section_titles(old)
    new_sections = _section_titles(new)
    sections = {
        "added": sorted(new_sections - old_sections),
        "removed": sorted(old_sections - new_sections),
    }

    # -- equations -----------------------------------------------------------
    equations = {
        "count_old": len(old.get("equations", [])),
        "count_new": len(new.get("equations", [])),
    }

    return {
        "old_root": str(old_root),
        "new_root": str(new_root),
        "theorems": theorems,
        "abstract": abstract,
        "labels": labels,
        "citations": citations,
        "sections": sections,
        "equations": equations,
    }


def _render_list_block(title: str, items: list[str]) -> list[str]:
    """Render a titled bullet list (or a '(none)' marker) as markdown lines."""
    lines = [f"- {title}:"]
    if items:
        for item in items:
            lines.append(f"  - {item}")
    else:
        lines.append("  - (none)")
    return lines


def _render_report(diff: dict) -> str:
    """Render the comparison diff as a deterministic markdown report."""
    lines: list[str] = ["# Version comparison", "", "_Generated by papercheck._", ""]

    lines.append(f"- old_root: `{diff['old_root']}`")
    lines.append(f"- new_root: `{diff['new_root']}`")
    lines.append("")

    thms = diff["theorems"]
    lines.append("## Theorems")
    lines.append("")
    lines.extend(_render_list_block("added", thms["added"]))
    lines.extend(_render_list_block("removed", thms["removed"]))
    lines.extend(_render_list_block("changed", thms["changed"]))
    lines.append("")

    lines.append("## Abstract")
    lines.append("")
    lines.append(f"- status: {diff['abstract']['status']}")
    lines.append("")

    labels = diff["labels"]
    lines.append("## Labels")
    lines.append("")
    lines.extend(_render_list_block("added", labels["added"]))
    lines.extend(_render_list_block("removed", labels["removed"]))
    lines.append("")

    cites = diff["citations"]
    lines.append("## Citations")
    lines.append("")
    lines.extend(_render_list_block("added", cites["added"]))
    lines.extend(_render_list_block("removed", cites["removed"]))
    lines.append("")

    secs = diff["sections"]
    lines.append("## Sections")
    lines.append("")
    lines.extend(_render_list_block("added", secs["added"]))
    lines.extend(_render_list_block("removed", secs["removed"]))
    lines.append("")

    eqs = diff["equations"]
    lines.append("## Equations")
    lines.append("")
    lines.append(f"- count_old: {eqs['count_old']}")
    lines.append(f"- count_new: {eqs['count_new']}")
    lines.append("")

    return "\n".join(lines)


def write_compare_report(
    old_root: Path,
    new_root: Path,
    out_path: Path | None = None,
) -> Path:
    """Compare two versions, render a markdown report, and write it to disk."""
    diff = compare_versions(old_root, new_root)

    if out_path is None:
        out_path = paths.audit_dir(Path(new_root)) / "version_comparison.md"
    out_path = Path(out_path)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(_render_report(diff), encoding="utf-8")
    return out_path
