"""Segment proposal for auditing a paper in reviewable chunks.

A *segment* is a contiguous slice of a paper (usually one top-level section)
that is audited as a unit. Segments are derived deterministically from the
scanned structure: each top-level ``\\section`` opens a new segment, and any
content before the first section becomes a "front matter" segment (``S0``).

Each segment carries a heuristic ``risk_score`` and a coarse ``budget`` bucket
(HIGH / MEDIUM / LOW) driving how much auditor effort it deserves.
"""

from __future__ import annotations

import json
from pathlib import Path

from papercheck.core import paths
from papercheck.core.schemas import validate

# Section levels that open a new segment. We segment on the coarsest structural
# unit only; subsections stay within their parent section's segment.
_TOP_LEVEL = {"section", "chapter"}

# Risk weighting per structural element found within a segment's span.
_W_THEOREM = 3
_W_ASSUMPTION = 2
_W_EQUATION = 2
_W_CLAIM_TRIGGER = 1

# Risk -> budget thresholds.
_HIGH_THRESHOLD = 12
_MEDIUM_THRESHOLD = 4

_BASE_AUDITORS = ["formalist", "notation", "hygiene"]


def _in_span(item: dict, file: str, start: int, end: int, line_key: str) -> bool:
    """Return True if ``item`` (file + a line field) falls within the span."""
    if item.get("file") != file:
        return False
    line = item.get(line_key)
    if line is None:
        return False
    return start <= line <= end


def _budget_for(risk: float) -> str:
    if risk >= _HIGH_THRESHOLD:
        return "HIGH"
    if risk >= _MEDIUM_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def propose_segments(structure: dict) -> list[dict]:
    """Propose audit segments from a parsed document structure.

    Derives one segment per top-level section (plus a front-matter segment for
    content before the first section), scores each heuristically, and returns
    schema-valid segment records in document order.
    """
    sections = structure.get("sections", [])
    theorem_envs = structure.get("theorem_envs", [])
    equations = structure.get("equations", [])
    claim_triggers = structure.get("claim_triggers", [])
    labels = structure.get("labels", [])

    # Pick the primary source file: the top main candidate, else the first tex
    # file, else a placeholder. Single-file papers are the common case.
    main_candidates = structure.get("main_candidates", [])
    tex_files = structure.get("files", {}).get("tex", [])
    if main_candidates:
        main_file = main_candidates[0]["file"]
    elif tex_files:
        main_file = tex_files[0]
    else:
        main_file = "main.tex"

    # Highest line seen in the main file, so the last segment has a real end.
    max_line = 1
    for item in theorem_envs + equations:
        if item.get("file") == main_file:
            max_line = max(max_line, item.get("line_end", 1) or 1)
    for item in claim_triggers + labels + sections:
        if item.get("file") == main_file:
            max_line = max(max_line, item.get("line", 1) or 1)

    # Top-level sections in the main file, in document (line) order.
    top_sections = [
        s
        for s in sections
        if s.get("file") == main_file and s.get("level") in _TOP_LEVEL
    ]
    top_sections.sort(key=lambda s: s.get("line", 0))

    # Build (title, start, end) spans. S0 = front matter (line 1 .. first
    # section - 1); each section spans from its line to the next section - 1.
    spans: list[tuple[str, int, int]] = []
    if top_sections:
        first_line = top_sections[0]["line"]
        if first_line > 1:
            spans.append(("Front matter", 1, first_line - 1))
        for i, sec in enumerate(top_sections):
            start = sec["line"]
            if i + 1 < len(top_sections):
                end = top_sections[i + 1]["line"] - 1
            else:
                end = max(max_line, start)
            title = sec.get("title") or "Untitled section"
            spans.append((title, start, end))
    else:
        # No sections: one big segment over the whole main file.
        spans.append(("Front matter", 1, max_line))

    segments: list[dict] = []
    for idx, (title, start, end) in enumerate(spans):
        n_theorems = sum(
            1
            for t in theorem_envs
            if t.get("kind") != "assumption"
            and t.get("file") == main_file
            and t.get("line_start") is not None
            and start <= t["line_start"] <= end
        )
        n_assumptions = sum(
            1
            for t in theorem_envs
            if t.get("kind") == "assumption"
            and t.get("file") == main_file
            and t.get("line_start") is not None
            and start <= t["line_start"] <= end
        )
        n_equations = sum(
            1
            for e in equations
            if e.get("file") == main_file
            and e.get("line_start") is not None
            and start <= e["line_start"] <= end
        )
        n_triggers = sum(
            1 for c in claim_triggers if _in_span(c, main_file, start, end, "line")
        )

        risk = (
            _W_THEOREM * n_theorems
            + _W_ASSUMPTION * n_assumptions
            + _W_EQUATION * n_equations
            + _W_CLAIM_TRIGGER * n_triggers
        )
        budget = _budget_for(risk)

        span_labels = sorted(
            {
                lbl["label"]
                for lbl in labels
                if _in_span(lbl, main_file, start, end, "line")
            }
        )

        reason_parts: list[str] = []
        if n_theorems:
            reason_parts.append(f"{n_theorems} theorem-like env(s)")
        if n_assumptions:
            reason_parts.append(f"{n_assumptions} assumption(s)")
        if n_equations:
            reason_parts.append(f"{n_equations} equation(s)")
        if n_triggers:
            reason_parts.append(f"{n_triggers} claim trigger(s)")
        reason = ", ".join(reason_parts) if reason_parts else "no risk signals"

        auditors = list(_BASE_AUDITORS)
        if budget == "HIGH":
            auditors.append("domain_specialist")

        record = {
            "segment_id": f"S{idx}",
            "title": title,
            "files": [main_file],
            "line_ranges": [{"file": main_file, "start": start, "end": end}],
            "labels": span_labels,
            "risk_score": risk,
            "budget": budget,
            "reason": reason,
            "auditors": auditors,
        }
        validate(record, "segment")
        segments.append(record)

    return segments


def write_segments(paper_root: Path, structure: dict) -> list[dict]:
    """Compute segments, write them to ``segments.json``, and return them."""
    segments = propose_segments(structure)
    out_path = paths.segments_file(Path(paper_root))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(segments, indent=2) + "\n", encoding="utf-8")
    return segments
