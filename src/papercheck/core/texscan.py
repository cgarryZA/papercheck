"""Scan a paper's LaTeX sources into a structured representation.

This is a deterministic, line/regex-based extractor -- not a full TeX parser.
It recurses from ``paper_root``, collects source and figure files, and pulls out
mechanical structure (sections, labels, refs, citations, theorem environments,
equations, draft markers, claim triggers) that later phases build on.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from papercheck.core import paths

# -- file discovery ----------------------------------------------------------

SKIP_DIRS = {"Paper_Audit", ".git", "__pycache__"}

TEX_EXT = ".tex"
BIB_EXT = ".bib"
STY_EXT = ".sty"
CLS_EXT = ".cls"
FIGURE_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg"}

# -- theorem-like defaults ---------------------------------------------------

DEFAULT_THEOREM_ENVS = [
    "theorem",
    "lemma",
    "proposition",
    "corollary",
    "definition",
    "assumption",
    "remark",
]

EQUATION_ENVS = ["equation", "align", "gather", "multline"]

DRAFT_MARKERS = ["TODO", "FIXME", "TBD", "XXX", "placeholder", "draft", "??"]

CLAIM_TRIGGER_WORDS = [
    "obvious",
    "clearly",
    "trivial",
    "straightforward",
    "immediate",
    "prove",
    "guarantee",
    "confirm",
    "first",
    "novel",
    "exact",
    "optimal",
    "universal",
]

# -- regexes -----------------------------------------------------------------

_COMMENT_SPLIT = re.compile(r"(?<!\\)%")

_NEWTHEOREM = re.compile(r"\\newtheorem\*?\{([^}]*)\}")
_SECTION = re.compile(r"\\(chapter|section|subsection)\*?\{")
_LABEL = re.compile(r"\\label\{([^}]*)\}")
_INPUT = re.compile(r"\\(?:input|include)\{([^}]*)\}")
_REF = re.compile(r"\\(ref|eqref|cref|Cref|autoref)\{([^}]*)\}")
_CITE = re.compile(r"\\(?:cite[a-zA-Z]*|citep|citet|citeauthor)\{([^}]*)\}")
_DOCUMENTCLASS = re.compile(r"\\documentclass")
_BEGIN_DOCUMENT = re.compile(r"\\begin\{document\}")
_BIB_ENTRY = re.compile(r"@\w+\s*\{\s*([^,\s]+)")
_BEGIN_ENV = re.compile(r"\\begin\{([^}]*)\}")
_END_ENV = re.compile(r"\\end\{([^}]*)\}")

# Draft markers: word-ish markers need boundaries; ?? is literal.
_DRAFT_WORD = re.compile(
    r"(?i)\b(TODO|FIXME|TBD|XXX|placeholder|draft)\b|(\?\?)"
)


def _code_portion(line: str) -> str:
    """Return the portion of a line before an unescaped ``%`` comment."""
    return _COMMENT_SPLIT.split(line, maxsplit=1)[0]


def _is_commented(line: str) -> bool:
    """Return True if the first non-whitespace char is ``%``."""
    stripped = line.lstrip()
    return stripped.startswith("%")


def _match_brace(text: str, start: int) -> str | None:
    """Extract balanced brace content starting at index ``start`` (a ``{``)."""
    if start >= len(text) or text[start] != "{":
        return None
    depth = 0
    out = []
    for ch in text[start:]:
        if ch == "{":
            depth += 1
            if depth == 1:
                continue
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return "".join(out)
        out.append(ch)
    return None


def _read_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return text.splitlines()


def scan(paper_root: Path) -> dict:
    """Scan the LaTeX sources under ``paper_root`` and return structure data.

    Also writes the result to ``structure.json`` in the paper's audit dir.
    """
    paper_root = Path(paper_root)

    files: dict[str, list[str]] = {
        "tex": [],
        "bib": [],
        "sty": [],
        "cls": [],
        "figures": [],
    }

    # -- discover files ------------------------------------------------------
    all_paths: list[Path] = []
    if paper_root.exists():
        for p in sorted(paper_root.rglob("*")):
            rel_parts = p.relative_to(paper_root).parts
            if any(part in SKIP_DIRS for part in rel_parts):
                continue
            if not p.is_file():
                continue
            all_paths.append(p)

    tex_paths: list[Path] = []
    bib_paths: list[Path] = []
    for p in all_paths:
        rel = p.relative_to(paper_root).as_posix()
        suffix = p.suffix.lower()
        if suffix == TEX_EXT:
            files["tex"].append(rel)
            tex_paths.append(p)
        elif suffix == BIB_EXT:
            files["bib"].append(rel)
            bib_paths.append(p)
        elif suffix == STY_EXT:
            files["sty"].append(rel)
        elif suffix == CLS_EXT:
            files["cls"].append(rel)
        elif suffix in FIGURE_EXTS:
            files["figures"].append(rel)

    for key in files:
        files[key].sort()

    # -- first pass: theorem env names via \newtheorem -----------------------
    theorem_env_names: set[str] = set(DEFAULT_THEOREM_ENVS)
    for p in tex_paths:
        for line in _read_lines(p):
            if _is_commented(line):
                continue
            code = _code_portion(line)
            for m in _NEWTHEOREM.finditer(code):
                theorem_env_names.add(m.group(1))

    # -- second pass: per-file extraction ------------------------------------
    main_candidates: list[dict] = []
    include_graph: list[dict] = []
    sections: list[dict] = []
    theorem_envs: list[dict] = []
    labels: list[dict] = []
    refs: list[dict] = []
    citations: list[dict] = []
    equations: list[dict] = []
    draft_markers: list[dict] = []
    claim_triggers: list[dict] = []

    label_counts: dict[str, int] = {}

    for p in tex_paths:
        rel = p.relative_to(paper_root).as_posix()
        lines = _read_lines(p)

        score = 0
        reasons: list[str] = []
        has_docclass = False
        has_begin_doc = False
        include_count = 0

        # env stack for theorem + equation environment tracking
        # each stack entry: (env_name, start_line, label_or_None, kind)
        thm_stack: list[dict] = []
        eq_stack: list[dict] = []

        for idx, raw in enumerate(lines):
            lineno = idx + 1
            commented = _is_commented(raw)
            code = _code_portion(raw)

            # ---- draft markers: scan the WHOLE raw line (comments count) ----
            for m in _DRAFT_WORD.finditer(raw):
                marker = m.group(1) or m.group(2)
                draft_markers.append(
                    {
                        "marker": marker,
                        "file": rel,
                        "line": lineno,
                        "text": raw.strip(),
                    }
                )

            if commented:
                continue

            # ---- main candidate signals ----
            if _DOCUMENTCLASS.search(code):
                if not has_docclass:
                    has_docclass = True
                    score += 5
                    reasons.append("has \\documentclass")
            if _BEGIN_DOCUMENT.search(code):
                if not has_begin_doc:
                    has_begin_doc = True
                    score += 5
                    reasons.append("has \\begin{document}")

            # ---- include graph ----
            for m in _INPUT.finditer(code):
                target = m.group(1)
                inc_rel = _normalize_include(paper_root, target)
                include_graph.append({"from": rel, "includes": inc_rel})
                include_count += 1
                score += 1

            # ---- sections ----
            for m in _SECTION.finditer(code):
                brace_start = m.end() - 1  # position of the '{'
                title = _match_brace(code, brace_start)
                sections.append(
                    {
                        "level": m.group(1),
                        "title": title if title is not None else "",
                        "file": rel,
                        "line": lineno,
                    }
                )

            # ---- labels ----
            for m in _LABEL.finditer(code):
                lbl = m.group(1)
                labels.append({"label": lbl, "file": rel, "line": lineno})
                label_counts[lbl] = label_counts.get(lbl, 0) + 1
                # attach to any open theorem / equation env
                if thm_stack and thm_stack[-1]["label"] is None:
                    thm_stack[-1]["label"] = lbl
                if eq_stack and eq_stack[-1]["label"] is None:
                    eq_stack[-1]["label"] = lbl

            # ---- refs ----
            for m in _REF.finditer(code):
                kind = m.group(1)
                for target in _split_keys(m.group(2)):
                    refs.append(
                        {
                            "kind": kind,
                            "target": target,
                            "file": rel,
                            "line": lineno,
                        }
                    )

            # ---- citations ----
            for m in _CITE.finditer(code):
                for key in _split_keys(m.group(1)):
                    citations.append({"key": key, "file": rel, "line": lineno})

            # ---- claim triggers ----
            for word in _find_claim_triggers(code):
                claim_triggers.append({"word": word, "file": rel, "line": lineno})

            # ---- environments (theorem + equation) ----
            for m in _BEGIN_ENV.finditer(code):
                env = m.group(1)
                if env in theorem_env_names:
                    thm_stack.append(
                        {"kind": env, "label": None, "line_start": lineno}
                    )
                eq_env = _eq_env_name(env)
                if eq_env is not None:
                    eq_stack.append(
                        {"env": eq_env, "label": None, "line_start": lineno}
                    )

            for m in _END_ENV.finditer(code):
                env = m.group(1)
                if env in theorem_env_names and thm_stack:
                    # find matching innermost of same kind (best-effort)
                    entry = _pop_env(thm_stack, "kind", env)
                    if entry is not None:
                        theorem_envs.append(
                            {
                                "kind": entry["kind"],
                                "label": entry["label"],
                                "file": rel,
                                "line_start": entry["line_start"],
                                "line_end": lineno,
                            }
                        )
                eq_env = _eq_env_name(env)
                if eq_env is not None and eq_stack:
                    entry = _pop_env(eq_stack, "env", eq_env)
                    if entry is not None:
                        equations.append(
                            {
                                "label": entry["label"],
                                "env": entry["env"],
                                "file": rel,
                                "line_start": entry["line_start"],
                                "line_end": lineno,
                            }
                        )

        # unmatched theorem/equation envs: best-effort, record with line_end=start
        for entry in thm_stack:
            theorem_envs.append(
                {
                    "kind": entry["kind"],
                    "label": entry["label"],
                    "file": rel,
                    "line_start": entry["line_start"],
                    "line_end": entry["line_start"],
                }
            )
        for entry in eq_stack:
            equations.append(
                {
                    "label": entry["label"],
                    "env": entry["env"],
                    "file": rel,
                    "line_start": entry["line_start"],
                    "line_end": entry["line_start"],
                }
            )

        main_candidates.append({"file": rel, "score": score, "reasons": reasons})

    # -- rank main candidates (score desc, then path asc) --------------------
    main_candidates.sort(key=lambda c: (-c["score"], c["file"]))

    # -- duplicate labels ----------------------------------------------------
    defined_labels = {lbl["label"] for lbl in labels}
    duplicate_labels = sorted(
        lbl for lbl, count in label_counts.items() if count > 1
    )

    # -- unresolved refs -----------------------------------------------------
    ref_targets = {r["target"] for r in refs}
    unresolved_refs = sorted(t for t in ref_targets if t not in defined_labels)

    # -- bib keys ------------------------------------------------------------
    bib_keys: list[str] = []
    for p in bib_paths:
        for m in _BIB_ENTRY.finditer(p.read_text(encoding="utf-8", errors="replace")):
            bib_keys.append(m.group(1))
    bib_key_set = set(bib_keys)

    # -- unresolved / unused citations ---------------------------------------
    cite_keys = {c["key"] for c in citations}
    if bib_paths:
        unresolved_citations = sorted(k for k in cite_keys if k not in bib_key_set)
    else:
        unresolved_citations = []
    unused_bib_keys = sorted(k for k in bib_key_set if k not in cite_keys)

    result: dict = {
        "paper_root": str(paper_root),
        "files": files,
        "main_candidates": main_candidates,
        "include_graph": include_graph,
        "sections": sections,
        "theorem_envs": theorem_envs,
        "theorem_env_names": sorted(theorem_env_names),
        "labels": labels,
        "duplicate_labels": duplicate_labels,
        "refs": refs,
        "unresolved_refs": unresolved_refs,
        "citations": citations,
        "bib_keys": bib_keys,
        "unresolved_citations": unresolved_citations,
        "unused_bib_keys": unused_bib_keys,
        "equations": equations,
        "draft_markers": draft_markers,
        "claim_triggers": claim_triggers,
    }

    # -- persist -------------------------------------------------------------
    out_path = paths.structure_file(paper_root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    return result


def _split_keys(raw: str) -> list[str]:
    """Split a comma-separated key list, stripping whitespace, dropping empties."""
    return [k.strip() for k in raw.split(",") if k.strip()]


def _normalize_include(paper_root: Path, target: str) -> str:
    """Normalize an \\input/\\include target to a rel .tex path with posix seps."""
    target = target.strip()
    if not target.endswith(".tex"):
        target = target + ".tex"
    return Path(target).as_posix()


def _eq_env_name(env: str) -> str | None:
    """Map an environment (possibly starred) to its equation name, or None."""
    base = env[:-1] if env.endswith("*") else env
    return base if base in EQUATION_ENVS else None


def _pop_env(stack: list[dict], key: str, value: str) -> dict | None:
    """Pop the innermost stack entry whose ``key`` matches ``value``."""
    for i in range(len(stack) - 1, -1, -1):
        if stack[i][key] == value:
            return stack.pop(i)
    return None


def _find_claim_triggers(code: str) -> list[str]:
    """Return claim-trigger words present in ``code`` (case-insensitive)."""
    found: list[str] = []
    lowered = code.lower()
    for word in CLAIM_TRIGGER_WORDS:
        for m in re.finditer(r"\b" + re.escape(word) + r"\b", lowered):
            del m  # count each occurrence
            found.append(word)
    return found
