"""Scan a paper's LaTeX sources into a structured representation.

This extractor is LaTeX-AST-aware: it parses each ``.tex`` file into a node
tree with :mod:`pylatexenc.latexwalker` and derives structure (sections,
theorem-like environments, labels, refs, citations, equations) from the tree.
Line numbers are recovered by mapping node character offsets back onto the
source text. Where an AST does not help -- draft markers hidden in comments,
the claim-trigger word scan, file/figure discovery, ``.bib`` parsing, and the
include graph -- it keeps straightforward line/regex scanning.

If ``pylatexenc`` raises on malformed input, the per-file pass falls back to a
best-effort regex scan (the historical implementation, retained privately). In
all cases :func:`scan` returns a well-formed dict and never raises on bad
input.
"""

from __future__ import annotations

import bisect
import json
import re
from pathlib import Path

from pylatexenc.latexwalker import (
    LatexEnvironmentNode,
    LatexGroupNode,
    LatexMacroNode,
    LatexWalker,
)

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

# -- macro name groups -------------------------------------------------------

_SECTION_MACROS = {"chapter", "section", "subsection"}
_REF_MACROS = {"ref", "eqref", "cref", "Cref", "autoref"}
# citation macros: any \cite... variant. We match on a prefix + explicit extras.
_CITE_EXTRA = {"citep", "citet", "citeauthor"}

# -- regexes (fallback path + non-AST scans) ---------------------------------

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


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _read_lines(path: Path) -> list[str]:
    return _read_text(path).splitlines()


class _LineMap:
    """Map 0-based character offsets in a source string to 1-based line numbers."""

    def __init__(self, text: str) -> None:
        # newline_offsets[i] = char index of the i-th '\n'.
        self._newlines = [i for i, ch in enumerate(text) if ch == "\n"]
        self._len = len(text)

    def line_of(self, pos: int) -> int:
        """Return the 1-based line number containing character offset ``pos``."""
        if pos <= 0:
            return 1
        if pos > self._len:
            pos = self._len
        # number of newlines strictly before pos, + 1.
        return bisect.bisect_right(self._newlines, pos - 1) + 1


# -- AST helpers -------------------------------------------------------------


def _macro_group_texts(node: LatexMacroNode, source: str) -> list[str]:
    """Return the contents of each brace group that follows a macro.

    Robust to pylatexenc's per-macro argument handling: known macros expose
    their ``{...}`` args via ``nodeargd``; unknown macros (e.g. ``\\newtheorem``)
    leave the groups as following siblings. We sidestep both by re-reading the
    balanced brace groups directly from the source, starting at the macro's end.
    """
    texts: list[str] = []
    # Start scanning right after the macro name (and optional star).
    i = node.pos + 1 + len(node.macroname)
    n = len(source)
    while i < n:
        ch = source[i]
        if ch in " \t":
            i += 1
            continue
        if ch == "*":
            i += 1
            continue
        if ch == "[":
            # optional arg -- skip to matching ']'
            depth = 0
            j = i
            while j < n:
                if source[j] == "[":
                    depth += 1
                elif source[j] == "]":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            i = j + 1
            continue
        if ch == "{":
            content = _match_brace(source, i)
            if content is None:
                break
            texts.append(content)
            i += len(content) + 2  # skip '{' + content + '}'
            continue
        break
    return texts


def _macro_first_group(node: LatexMacroNode, source: str) -> str | None:
    """Return the first brace-group content of a macro, or None."""
    groups = _macro_group_texts(node, source)
    return groups[0] if groups else None


def _is_cite_macro(name: str) -> bool:
    """Return True if a macro name is a citation command."""
    return name.startswith("cite") or name in _CITE_EXTRA


def _collect_newtheorem_names(nodes: list, source: str, out: set[str]) -> None:
    """Walk the tree collecting names declared via ``\\newtheorem``."""
    for node in nodes:
        if node is None:
            continue
        if isinstance(node, LatexMacroNode) and node.macroname == "newtheorem":
            name = _macro_first_group(node, source)
            if name:
                out.add(name.strip())
        # descend
        for child in _child_nodes(node):
            _collect_newtheorem_names([child], source, out)


def _child_nodes(node) -> list:
    """Return the child nodes of a node (env/group body + macro arg groups)."""
    children: list = []
    nodelist = getattr(node, "nodelist", None)
    if nodelist:
        children.extend(n for n in nodelist if n is not None)
    argd = getattr(node, "nodeargd", None)
    if argd is not None and getattr(argd, "argnlist", None):
        children.extend(a for a in argd.argnlist if a is not None)
    return children


def _walk_structure(
    nodes: list,
    source: str,
    linemap: _LineMap,
    rel: str,
    theorem_env_names: set[str],
    *,
    sections: list[dict],
    theorem_envs: list[dict],
    labels: list[dict],
    refs: list[dict],
    citations: list[dict],
    equations: list[dict],
    include_graph: list[dict],
    paper_root: Path,
    stats: dict,
) -> None:
    """Recursively derive structure from an AST node list (document order)."""
    for node in nodes:
        if node is None:
            continue

        if isinstance(node, LatexMacroNode):
            name = node.macroname
            line = linemap.line_of(node.pos)

            if name == "documentclass":
                stats["has_docclass"] = True
            elif name in _SECTION_MACROS:
                title = _macro_first_group(node, source)
                sections.append(
                    {
                        "level": name,
                        "title": title if title is not None else "",
                        "file": rel,
                        "line": line,
                    }
                )
            elif name == "label":
                lbl = _macro_first_group(node, source)
                if lbl is not None:
                    labels.append({"label": lbl, "file": rel, "line": line})
            elif name in _REF_MACROS:
                raw = _macro_first_group(node, source)
                if raw is not None:
                    for target in _split_keys(raw):
                        refs.append(
                            {"kind": name, "target": target, "file": rel, "line": line}
                        )
            elif _is_cite_macro(name):
                raw = _macro_first_group(node, source)
                if raw is not None:
                    for key in _split_keys(raw):
                        citations.append({"key": key, "file": rel, "line": line})
            elif name in ("input", "include"):
                target = _macro_first_group(node, source)
                if target is not None:
                    inc_rel = _normalize_include(paper_root, target)
                    include_graph.append({"from": rel, "includes": inc_rel})
                    stats["include_count"] += 1

            # macro args may themselves contain structure (rare, but safe)
            for child in _child_nodes(node):
                _walk_structure(
                    [child], source, linemap, rel, theorem_env_names,
                    sections=sections, theorem_envs=theorem_envs, labels=labels,
                    refs=refs, citations=citations, equations=equations,
                    include_graph=include_graph, paper_root=paper_root, stats=stats,
                )
            continue

        if isinstance(node, LatexEnvironmentNode):
            env = node.environmentname
            if env == "document":
                stats["has_begin_doc"] = True

            line_start = linemap.line_of(node.pos)
            end_off = node.pos + node.len - 1
            line_end = linemap.line_of(end_off)

            is_theorem = env in theorem_env_names
            eq_env = _eq_env_name(env)

            if is_theorem or eq_env is not None:
                # find the first \label anywhere inside this environment.
                inner_label = _first_label_in(node.nodelist, source)
                if is_theorem:
                    theorem_envs.append(
                        {
                            "kind": env,
                            "label": inner_label,
                            "file": rel,
                            "line_start": line_start,
                            "line_end": line_end,
                        }
                    )
                if eq_env is not None:
                    equations.append(
                        {
                            "label": inner_label,
                            "env": eq_env,
                            "file": rel,
                            "line_start": line_start,
                            "line_end": line_end,
                        }
                    )

            # descend into the body so nested envs/labels/refs are recorded too.
            _walk_structure(
                node.nodelist or [], source, linemap, rel, theorem_env_names,
                sections=sections, theorem_envs=theorem_envs, labels=labels,
                refs=refs, citations=citations, equations=equations,
                include_graph=include_graph, paper_root=paper_root, stats=stats,
            )
            continue

        if isinstance(node, LatexGroupNode):
            _walk_structure(
                node.nodelist or [], source, linemap, rel, theorem_env_names,
                sections=sections, theorem_envs=theorem_envs, labels=labels,
                refs=refs, citations=citations, equations=equations,
                include_graph=include_graph, paper_root=paper_root, stats=stats,
            )
            continue

        # math nodes and other containers may hold macros (e.g. \label in align)
        for child in _child_nodes(node):
            _walk_structure(
                [child], source, linemap, rel, theorem_env_names,
                sections=sections, theorem_envs=theorem_envs, labels=labels,
                refs=refs, citations=citations, equations=equations,
                include_graph=include_graph, paper_root=paper_root, stats=stats,
            )


def _first_label_in(nodes: list, source: str) -> str | None:
    """Return the first ``\\label{...}`` content found anywhere below ``nodes``.

    Descends into nested groups/environments but does NOT cross into a nested
    theorem-like or equation environment's own label ownership? It does not need
    to: the first label in document order inside a theorem is the theorem's
    label, matching the historical behavior where the innermost-open env claimed
    the next label. We simply take the first label encountered depth-first.
    """
    for node in nodes or []:
        if node is None:
            continue
        if isinstance(node, LatexMacroNode) and node.macroname == "label":
            lbl = _macro_first_group(node, source)
            if lbl is not None:
                return lbl
        for child in _child_nodes(node):
            found = _first_label_in([child], source)
            if found is not None:
                return found
    return None


# -- per-file scanning -------------------------------------------------------


def _scan_file_ast(
    text: str,
    rel: str,
    theorem_env_names: set[str],
    paper_root: Path,
    *,
    sections: list[dict],
    theorem_envs: list[dict],
    labels: list[dict],
    refs: list[dict],
    citations: list[dict],
    equations: list[dict],
    include_graph: list[dict],
) -> dict:
    """AST path: parse ``text`` and append structure. Returns scoring stats.

    Raises whatever ``pylatexenc`` raises on malformed input; the caller falls
    back to :func:`_scan_file_regex`.
    """
    linemap = _LineMap(text)
    walker = LatexWalker(text, tolerant_parsing=False)
    nodelist, _pos, _len = walker.get_latex_nodes()

    stats = {"has_docclass": False, "has_begin_doc": False, "include_count": 0}
    _walk_structure(
        nodelist, text, linemap, rel, theorem_env_names,
        sections=sections, theorem_envs=theorem_envs, labels=labels,
        refs=refs, citations=citations, equations=equations,
        include_graph=include_graph, paper_root=paper_root, stats=stats,
    )
    return stats


def _scan_file_regex(
    lines: list[str],
    rel: str,
    theorem_env_names: set[str],
    paper_root: Path,
    *,
    sections: list[dict],
    theorem_envs: list[dict],
    labels: list[dict],
    refs: list[dict],
    citations: list[dict],
    equations: list[dict],
    include_graph: list[dict],
) -> dict:
    """Fallback path: historical line/regex extraction. Never raises."""
    stats = {"has_docclass": False, "has_begin_doc": False, "include_count": 0}

    thm_stack: list[dict] = []
    eq_stack: list[dict] = []

    for idx, raw in enumerate(lines):
        lineno = idx + 1
        if _is_commented(raw):
            continue
        code = _code_portion(raw)

        if _DOCUMENTCLASS.search(code):
            stats["has_docclass"] = True
        if _BEGIN_DOCUMENT.search(code):
            stats["has_begin_doc"] = True

        for m in _INPUT.finditer(code):
            inc_rel = _normalize_include(paper_root, m.group(1))
            include_graph.append({"from": rel, "includes": inc_rel})
            stats["include_count"] += 1

        for m in _SECTION.finditer(code):
            brace_start = m.end() - 1
            title = _match_brace(code, brace_start)
            sections.append(
                {
                    "level": m.group(1),
                    "title": title if title is not None else "",
                    "file": rel,
                    "line": lineno,
                }
            )

        for m in _LABEL.finditer(code):
            lbl = m.group(1)
            labels.append({"label": lbl, "file": rel, "line": lineno})
            if thm_stack and thm_stack[-1]["label"] is None:
                thm_stack[-1]["label"] = lbl
            if eq_stack and eq_stack[-1]["label"] is None:
                eq_stack[-1]["label"] = lbl

        for m in _REF.finditer(code):
            kind = m.group(1)
            for target in _split_keys(m.group(2)):
                refs.append(
                    {"kind": kind, "target": target, "file": rel, "line": lineno}
                )

        for m in _CITE.finditer(code):
            for key in _split_keys(m.group(1)):
                citations.append({"key": key, "file": rel, "line": lineno})

        for m in _BEGIN_ENV.finditer(code):
            env = m.group(1)
            if env in theorem_env_names:
                thm_stack.append({"kind": env, "label": None, "line_start": lineno})
            eq_env = _eq_env_name(env)
            if eq_env is not None:
                eq_stack.append({"env": eq_env, "label": None, "line_start": lineno})

        for m in _END_ENV.finditer(code):
            env = m.group(1)
            if env in theorem_env_names and thm_stack:
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
    return stats


def _scan_non_ast(
    lines: list[str],
    rel: str,
    *,
    draft_markers: list[dict],
    claim_triggers: list[dict],
) -> None:
    """Line-based scans the AST does not help with: draft markers + claims.

    Draft markers are found on the WHOLE raw line (comments count). Claim
    triggers are found only in the code portion of non-commented lines.
    """
    for idx, raw in enumerate(lines):
        lineno = idx + 1
        for m in _DRAFT_WORD.finditer(raw):
            marker = m.group(1) or m.group(2)
            draft_markers.append(
                {"marker": marker, "file": rel, "line": lineno, "text": raw.strip()}
            )
        if _is_commented(raw):
            continue
        code = _code_portion(raw)
        for word in _find_claim_triggers(code):
            claim_triggers.append({"word": word, "file": rel, "line": lineno})


def scan(paper_root: Path) -> dict:
    """Scan the LaTeX sources under ``paper_root`` and return structure data.

    Also writes the result to ``structure.json`` in the paper's audit dir.
    Never raises on malformed LaTeX: per-file parsing falls back to a
    best-effort regex scan, and the returned dict always has every key present.
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

    # -- read each tex file once ---------------------------------------------
    tex_sources: list[tuple[Path, str, str]] = []  # (path, rel, text)
    for p in tex_paths:
        rel = p.relative_to(paper_root).as_posix()
        tex_sources.append((p, rel, _read_text(p)))

    # -- theorem env names via \newtheorem (AST, regex fallback) -------------
    theorem_env_names: set[str] = set(DEFAULT_THEOREM_ENVS)
    for _p, _rel, text in tex_sources:
        try:
            walker = LatexWalker(text, tolerant_parsing=False)
            nodelist, _pos, _len = walker.get_latex_nodes()
            _collect_newtheorem_names(nodelist, text, theorem_env_names)
        except Exception:
            for line in text.splitlines():
                if _is_commented(line):
                    continue
                code = _code_portion(line)
                for m in _NEWTHEOREM.finditer(code):
                    theorem_env_names.add(m.group(1))

    # -- per-file extraction -------------------------------------------------
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

    for _p, rel, text in tex_sources:
        lines = text.splitlines()

        # comment-aware line scans (draft markers, claim triggers)
        _scan_non_ast(
            lines, rel, draft_markers=draft_markers, claim_triggers=claim_triggers
        )

        try:
            stats = _scan_file_ast(
                text, rel, theorem_env_names, paper_root,
                sections=sections, theorem_envs=theorem_envs, labels=labels,
                refs=refs, citations=citations, equations=equations,
                include_graph=include_graph,
            )
        except Exception:
            stats = _scan_file_regex(
                lines, rel, theorem_env_names, paper_root,
                sections=sections, theorem_envs=theorem_envs, labels=labels,
                refs=refs, citations=citations, equations=equations,
                include_graph=include_graph,
            )

        score = 0
        reasons: list[str] = []
        if stats["has_docclass"]:
            score += 5
            reasons.append("has \\documentclass")
        if stats["has_begin_doc"]:
            score += 5
            reasons.append("has \\begin{document}")
        score += stats["include_count"]

        main_candidates.append({"file": rel, "score": score, "reasons": reasons})

    # -- rank main candidates (score desc, then path asc) --------------------
    main_candidates.sort(key=lambda c: (-c["score"], c["file"]))

    # -- duplicate labels ----------------------------------------------------
    label_counts: dict[str, int] = {}
    for lbl in labels:
        label_counts[lbl["label"]] = label_counts.get(lbl["label"], 0) + 1
    defined_labels = {lbl["label"] for lbl in labels}
    duplicate_labels = sorted(lbl for lbl, count in label_counts.items() if count > 1)

    # -- unresolved refs -----------------------------------------------------
    ref_targets = {r["target"] for r in refs}
    unresolved_refs = sorted(t for t in ref_targets if t not in defined_labels)

    # -- bib keys ------------------------------------------------------------
    bib_keys: list[str] = []
    for p in bib_paths:
        for m in _BIB_ENTRY.finditer(_read_text(p)):
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
