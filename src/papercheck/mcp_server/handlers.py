"""Pure, transport-free tool logic for the papercheck MCP server.

Every function here takes an explicit ``paper_root`` (plus any op-specific
arguments) and returns a JSON-serializable dict (or raises). The FastMCP
server in :mod:`papercheck.mcp_server.server` wraps each of these as a tool;
tests exercise them directly with no stdio transport.

Stage gates are enforced by loading the :class:`AuditState` and calling
``require_at_least`` before a mutating op (init is the exception — it creates
the state). ``StateError`` propagates to the caller when a gate fails.
"""

from __future__ import annotations

import json
from pathlib import Path

import papercheck
from papercheck.core import adjudicate as _adjudicate
from papercheck.core import (
    domainpack,
    gate,
    issues,
    ledger,
    paths,
    render,
    segments,
    texscan,
)
from papercheck.core import verify as _verify
from papercheck.core._resources import resource_dir
from papercheck.core.state import AuditState

# Maximum number of source lines a single window read may return.
_MAX_WINDOW_LINES = 400


def _root(paper_root: str | Path) -> Path:
    return Path(paper_root)


def _load_json(path: Path, default):
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


# -- read-only ------------------------------------------------------------


def get_state(paper_root: str | Path) -> dict:
    """Return the paper's audit state as a dict."""
    return AuditState.load(_root(paper_root)).to_dict()


def get_structure(paper_root: str | Path) -> dict:
    """Return the parsed document structure (or ``{}`` if not scanned)."""
    return _load_json(paths.structure_file(_root(paper_root)), {})


def get_segments(paper_root: str | Path) -> list:
    """Return the proposed segments (or ``[]`` if none)."""
    return _load_json(paths.segments_file(_root(paper_root)), [])


def get_theorem_inventory(paper_root: str | Path) -> list:
    """Return the theorem-like environments recorded in the structure."""
    structure = get_structure(paper_root)
    return structure.get("theorem_envs", [])


def get_issue(paper_root: str | Path, issue_id: str) -> dict:
    """Return a single issue by id (raises ``KeyError`` if absent)."""
    return ledger.load_issue(_root(paper_root), issue_id)


def list_issues(paper_root: str | Path, status: str | None = None) -> list:
    """Return all issues, optionally filtered by exact status."""
    return ledger.list_issues(_root(paper_root), status)


def get_manual_checks(paper_root: str | Path) -> list:
    """Return all manual checks for the paper."""
    return ledger.list_manual_checks(_root(paper_root))


def read_source_window(
    paper_root: str | Path,
    file: str,
    line_start: int,
    line_end: int,
) -> dict:
    """Return a 1-based line window from a source file inside the paper root.

    The resolved target path must stay within ``paper_root``; anything that
    escapes (``..`` traversal, absolute paths) raises :class:`ValueError`. The
    returned span is capped at :data:`_MAX_WINDOW_LINES` lines.
    """
    root = _root(paper_root).resolve()
    target = (root / file).resolve()
    if not target.is_relative_to(root):
        raise ValueError("path escapes paper root")

    text = target.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    start = max(1, line_start)
    end = min(len(lines), line_end)
    if end < start:
        end = start
    # Cap the span length.
    end = min(end, start + _MAX_WINDOW_LINES - 1)

    window = lines[start - 1 : end]
    return {
        "file": file,
        "line_start": start,
        "line_end": end,
        "text": "\n".join(window),
    }


def verify_quote(
    paper_root: str | Path,
    file: str,
    quote: str,
    line_start: int | None = None,
    line_end: int | None = None,
    slack: int = 0,
) -> dict:
    """Return whether ``quote`` appears in ``file`` within the given window."""
    root = _root(paper_root)
    found = _verify.verify_quote(
        root / file, quote, line_start, line_end, slack
    )
    return {"file": file, "quote_found": found}


# -- mutating (stage-gated) ----------------------------------------------


def init_audit(
    paper_root: str | Path,
    run_id: str,
    git_commit: str | None = None,
) -> dict:
    """Initialize the audit workspace and scaffold its subdirectories."""
    root = _root(paper_root)
    state = AuditState.init(
        root,
        run_id=run_id,
        harness_version=papercheck.__version__,
        git_commit=git_commit,
    )
    # Scaffold the standard directory layout.
    for status in ("proposed", "accepted", "rejected", "manual_check"):
        paths.issues_dir(root, status).mkdir(parents=True, exist_ok=True)
    paths.patches_dir(root).mkdir(parents=True, exist_ok=True)
    paths.manual_checks_dir(root).mkdir(parents=True, exist_ok=True)
    paths.reports_dir(root).mkdir(parents=True, exist_ok=True)
    return state.to_dict()


def run_scan(paper_root: str | Path) -> dict:
    """Scan the paper's sources, persist the structure, and advance to SCANNED."""
    root = _root(paper_root)
    state = AuditState.load(root)
    state.require_at_least("INIT")
    structure = texscan.scan(root)
    out_path = paths.structure_file(root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(structure, indent=2) + "\n", encoding="utf-8")
    state.ensure_at_least("SCANNED")
    return structure


def propose_segments(paper_root: str | Path) -> list:
    """Propose and persist audit segments, then advance to SEGMENTED."""
    root = _root(paper_root)
    state = AuditState.load(root)
    state.require_at_least("SCANNED")
    structure = get_structure(root)
    records = segments.write_segments(root, structure)
    state.ensure_at_least("SEGMENTED")
    return records


def save_inventory_record(paper_root: str | Path, record: dict) -> dict:
    """Append an inventory record and advance to INVENTORIED."""
    root = _root(paper_root)
    state = AuditState.load(root)
    state.require_at_least("SEGMENTED")
    path = paths.audit_dir(root) / "inventory.json"
    records = _load_json(path, [])
    records.append(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    # Idempotent: appending a record once the audit has moved past INVENTORIED
    # must not attempt an (illegal) backward transition.
    state.ensure_at_least("INVENTORIED")
    return record


def advance_stage(paper_root: str | Path, target: str) -> dict:
    """Advance the audit state to ``target`` and return the new state."""
    root = _root(paper_root)
    state = AuditState.load(root)
    state.advance(target)
    return state.to_dict()


def submit_issue(paper_root: str | Path, issue: dict) -> dict:
    """Submit an issue (delegates to the intake gate, which enforces AUDITING)."""
    return issues.submit_issue(_root(paper_root), issue)


def adjudicate_issue(
    paper_root: str | Path,
    issue_id: str,
    decision: str,
    rationale: str,
    adjudicator: str,
    severity_final: str | None = None,
) -> dict:
    """Adjudicate an issue (ACCEPT / REJECT / NEEDS_MANUAL_CHECK)."""
    return _adjudicate.adjudicate_issue(
        _root(paper_root),
        issue_id,
        decision,
        rationale,
        adjudicator,
        severity_final,
    )


def add_manual_check(
    paper_root: str | Path,
    question: str,
    needed_source: str | None = None,
    blocking: bool = True,
    owner: str = "human",
) -> dict:
    """Create a manual check the human auditor must resolve."""
    return _adjudicate.add_manual_check(
        _root(paper_root), question, needed_source, blocking, owner
    )


def resolve_manual_check(
    paper_root: str | Path,
    check_id: str,
    resolution: str,
    resolved_by: str = "human",
) -> dict:
    """Resolve a manual check with the given resolution text."""
    return _adjudicate.resolve_manual_check(
        _root(paper_root), check_id, resolution, resolved_by
    )


def plan_patch(paper_root: str | Path, patch: dict) -> dict:
    """Record a planned patch (requires ADJUDICATED)."""
    root = _root(paper_root)
    AuditState.load(root).require_at_least("ADJUDICATED")
    return _adjudicate.plan_patch(root, patch)


def record_patch(paper_root: str | Path, patch: dict) -> dict:
    """Record an applied patch (requires ADJUDICATED)."""
    root = _root(paper_root)
    AuditState.load(root).require_at_least("ADJUDICATED")
    return _adjudicate.record_patch(root, patch)


def record_regression_result(
    paper_root: str | Path,
    issue_id: str,
    result: str,
) -> dict:
    """Record a regression outcome for an issue (requires PATCHING)."""
    root = _root(paper_root)
    AuditState.load(root).require_at_least("PATCHING")
    return _adjudicate.record_regression_result(root, issue_id, result)


def run_gate(paper_root: str | Path, mechanical_only: bool = True) -> dict:
    """Run the final mechanical gate and return its verdict report."""
    return gate.run_gate(_root(paper_root), mechanical_only=mechanical_only)


def render_reports(paper_root: str | Path) -> dict:
    """Render all audit reports for the paper."""
    render.render_all(_root(paper_root))
    return {"ok": True}


# -- domain packs ---------------------------------------------------------


def list_domain_packs(paper_root: str | Path) -> list:
    """Return available domain-pack names (shipped, plus generated if present)."""
    return domainpack.list_packs(_root(paper_root))


def get_domain_pack(name: str, paper_root: str | Path | None = None) -> dict:
    """Return a domain pack by name (raises ``KeyError`` if absent)."""
    root = _root(paper_root) if paper_root else None
    return domainpack.load_pack(name, root)


def scaffold_domain_pack(paper_root: str | Path) -> dict:
    """Draft a candidate domain pack from the paper's structure (read-only)."""
    structure = _load_json(paths.structure_file(_root(paper_root)), {})
    return domainpack.scaffold_pack(structure)


def create_domain_pack(paper_root: str | Path, pack: dict) -> str:
    """Validate and persist a generated domain pack; return its path."""
    return str(domainpack.create_pack(_root(paper_root), pack))


# -- prompts --------------------------------------------------------------


def list_prompts() -> list:
    """Return sorted names of ``*.md`` prompt files (``[]`` if none)."""
    try:
        prompts_dir = resource_dir("prompts")
    except FileNotFoundError:
        return []
    return sorted(p.name for p in prompts_dir.glob("*.md"))


def get_prompt(name: str) -> str:
    """Return the text of a named prompt (raises ``KeyError`` if absent).

    The name may be given with or without the ``.md`` suffix.
    """
    try:
        prompts_dir = resource_dir("prompts")
    except FileNotFoundError:
        raise KeyError(f"Prompt {name!r} not found")
    candidates = [name]
    if not name.endswith(".md"):
        candidates.append(name + ".md")
    for candidate in candidates:
        path = prompts_dir / candidate
        if path.is_file():
            return path.read_text(encoding="utf-8")
    raise KeyError(f"Prompt {name!r} not found")
