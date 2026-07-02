"""Verification helpers for quotes and structural labels."""

from __future__ import annotations

from pathlib import Path


def normalize_ws(s: str) -> str:
    """Collapse all runs of whitespace to a single space and strip the ends."""
    return " ".join(s.split())


def verify_quote(
    file: Path,
    quote: str,
    line_start: int | None = None,
    line_end: int | None = None,
    slack: int = 0,
) -> bool:
    """Return whether ``quote`` appears in ``file`` within the given line range.

    Whitespace is normalized (all runs collapsed to a single space, ends
    stripped) for both the search region and the quote before comparison. When
    ``line_start`` is given the search is limited to lines
    ``[line_start - slack, line_end (or line_start) + slack]`` (1-based, clamped
    to the file). An empty quote or a missing file returns ``False``.
    """
    normalized_quote = normalize_ws(quote)
    if not normalized_quote:
        return False

    path = Path(file)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False

    if line_start is None:
        region = text
    else:
        lines = text.splitlines()
        end = line_end if line_end is not None else line_start
        # Convert to 0-based, apply slack, clamp to file bounds.
        lo = max(0, (line_start - slack) - 1)
        hi = min(len(lines), end + slack)
        region = "\n".join(lines[lo:hi])

    return normalized_quote in normalize_ws(region)


def label_exists(structure: dict, label: str) -> bool:
    """Return whether ``label`` is defined in the parsed document structure.

    ``structure["labels"]`` may be a list of label strings or a list of dicts
    each carrying a ``"label"`` key. A missing ``labels`` key yields ``False``.
    """
    labels = structure.get("labels")
    if not labels:
        return False
    for entry in labels:
        if isinstance(entry, dict):
            if entry.get("label") == label:
                return True
        elif entry == label:
            return True
    return False
