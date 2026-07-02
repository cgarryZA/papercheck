"""Privacy check: fail if forbidden identifiers appear in tracked-ish files.

Recursively scans the repository (skipping VCS/cache dirs and binary-looking
files) for case-insensitive matches of forbidden tokens. Prints offending
``file:line`` locations and exits 1 if any are found, else exits 0.

Runnable as: ``python scripts/privacy_check.py``
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PATTERN = re.compile(r"fbsdej|mckean[- ]?vlasov", re.IGNORECASE)

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}


def _looks_binary(path: Path) -> bool:
    """Return True if the file appears to be binary (contains a NUL byte)."""
    try:
        with path.open("rb") as fh:
            chunk = fh.read(8192)
    except OSError:
        return True
    return b"\x00" in chunk


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    self_path = Path(__file__).resolve()
    hits: list[str] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.resolve() == self_path:
            # This file defines the pattern itself; don't self-flag.
            continue
        if _looks_binary(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if PATTERN.search(line):
                rel = path.relative_to(root)
                hits.append(f"{rel}:{lineno}")

    if hits:
        for hit in hits:
            print(hit)
        return 1

    print("privacy check clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
