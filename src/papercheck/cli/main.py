"""papercheck command-line interface.

Defines the Typer ``app`` and command stubs. Command bodies are filled in later
phases; for now they echo a placeholder so ``papercheck --help`` lists them all.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from papercheck.core import paths, texscan

app = typer.Typer(help="papercheck — audit harness for mathematical LaTeX papers")


def _ensure_audit(root: Path) -> None:
    """Auto-initialize the audit workspace if it hasn't been created yet.

    Lets the stateful CLI verbs (``scan``, ``segments``) drive the same state
    machine as the MCP server without forcing the user to run ``init`` first.
    Existing state is left untouched (never reset).
    """
    if paths.state_file(root).exists():
        return
    import datetime

    from papercheck.mcp_server import handlers

    run_id = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%SZ")
    handlers.init_audit(str(root), run_id=run_id)


@app.command()
def init(
    paper_root: str = typer.Argument(..., help="Path to the paper's source root."),
) -> None:
    """Initialize a paper's audit workspace."""
    import datetime

    from papercheck.mcp_server import handlers

    run_id = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%SZ")
    state = handlers.init_audit(paper_root, run_id=run_id)
    typer.echo(f"Initialized audit at {paths.audit_dir(Path(paper_root))}")
    typer.echo(f"  run_id: {state['run_id']}")
    typer.echo(f"  stage:  {state['stage']}")
    raise typer.Exit(0)


@app.command()
def scan(
    paper_root: str = typer.Argument(..., help="Path to the paper's source root."),
    json_out: bool = typer.Option(
        False, "--json", help="Print the full structure JSON instead of a summary."
    ),
) -> None:
    """Scan a paper's LaTeX sources into a structured representation.

    Advances the shared audit state to SCANNED (auto-initializing the workspace
    if needed), so the CLI and MCP server drive one state machine.
    """
    from papercheck.mcp_server import handlers

    root = Path(paper_root)
    _ensure_audit(root)
    result = handlers.run_scan(str(root))

    if json_out:
        typer.echo(json.dumps(result, indent=2))
        raise typer.Exit(0)

    typer.echo(f"Scanned {root}")
    typer.echo(f"  tex files:             {len(result['files']['tex'])}")
    typer.echo(f"  theorem envs:          {len(result['theorem_envs'])}")
    typer.echo(f"  duplicate labels:      {len(result['duplicate_labels'])}")
    typer.echo(f"  unresolved refs:       {len(result['unresolved_refs'])}")
    typer.echo(f"  unresolved citations:  {len(result['unresolved_citations'])}")
    typer.echo(f"  draft markers:         {len(result['draft_markers'])}")
    suppressed = result.get("suppressed_draft_markers", [])
    if suppressed:
        typer.echo(f"  suppressed (pragma):   {len(suppressed)}")
    typer.echo(f"structure.json -> {paths.structure_file(root)}")
    raise typer.Exit(0)


@app.command()
def segments(
    paper_root: str = typer.Argument(..., help="Path to the paper's source root."),
) -> None:
    """Propose audit segments for a paper.

    Advances the shared audit state to SEGMENTED (scanning first if needed).
    """
    from papercheck.core.state import AuditState
    from papercheck.mcp_server import handlers

    root = Path(paper_root)
    _ensure_audit(root)
    if not paths.structure_file(root).exists():
        handlers.run_scan(str(root))
    else:
        # Structure already present (e.g. from a bare scan); make sure the
        # shared state has caught up before proposing segments.
        AuditState.load(root).ensure_at_least("SCANNED")

    records = handlers.propose_segments(str(root))

    budget_counts: dict[str, int] = {}
    for rec in records:
        budget_counts[rec["budget"]] = budget_counts.get(rec["budget"], 0) + 1
    summary = ", ".join(
        f"{level}={budget_counts.get(level, 0)}" for level in ("HIGH", "MEDIUM", "LOW")
    )
    typer.echo(f"Proposed {len(records)} segment(s): {summary}")

    ranked = sorted(records, key=lambda r: r.get("risk_score", 0), reverse=True)
    typer.echo("")
    typer.echo(f"{'ID':<6} {'BUDGET':<7} {'RISK':<6} {'TITLE':<40} AUDITORS")
    for rec in ranked:
        title = str(rec.get("title", ""))
        if len(title) > 40:
            title = title[:37] + "..."
        auditors = ", ".join(rec.get("auditors", []))
        typer.echo(
            f"{rec.get('segment_id', ''):<6} "
            f"{rec.get('budget', ''):<7} "
            f"{rec.get('risk_score', 0):<6} "
            f"{title:<40} {auditors}"
        )

    typer.echo(f"segments.json -> {paths.segments_file(root)}")
    raise typer.Exit(0)


@app.command()
def gate(
    paper_root: str = typer.Argument(..., help="Path to the paper's source root."),
    mechanical_only: bool = typer.Option(
        False, "--mechanical-only", help="Run only the mechanical gate signals."
    ),
) -> None:
    """Run the final gate checks for a paper.

    Exit codes: 0 = READY, 2 = READY AFTER MECHANICAL FIXES, 1 = any NOT READY.
    """
    from papercheck.core.gate import run_gate

    root = Path(paper_root)
    result = run_gate(root, mechanical_only=mechanical_only)

    typer.echo("")
    typer.echo(f"==== {result['verdict']} ====")
    blockers = result.get("blockers", [])
    if blockers:
        typer.echo("Blockers:")
        for b in blockers:
            typer.echo(f"  - {b}")
    else:
        typer.echo("No blockers.")

    warnings = result.get("warnings", [])
    if warnings:
        typer.echo("Warnings:")
        for w in warnings:
            typer.echo(f"  - {w}")

    verdict = result["verdict"]
    if verdict == "READY":
        code = 0
    elif verdict == "READY AFTER MECHANICAL FIXES":
        code = 2
    else:
        code = 1
    raise typer.Exit(code)


@app.command()
def render(
    paper_root: str = typer.Argument(..., help="Path to the paper's source root."),
) -> None:
    """Render audit reports for a paper."""
    from papercheck.core.render import render_all

    root = Path(paper_root)
    render_all(root)

    out_dir = paths.audit_dir(root)
    candidates = [
        "03_segment_map.md",
        "07_issue_ledger.proposed.md",
        "08_issue_ledger.adjudicated.md",
        "10_final_acceptance_gate.md",
        "manual_check_queue.md",
    ]
    written = [name for name in candidates if (out_dir / name).exists()]
    if written:
        typer.echo("Wrote:")
        for name in written:
            typer.echo(f"  - {out_dir / name}")
    else:
        typer.echo("No reports written (no source artifacts found).")
    raise typer.Exit(0)


@app.command("verify-quote")
def verify_quote(
    file: Path = typer.Argument(..., help="Path to the source file to search."),
    quote: str = typer.Argument(..., help="The exact quote to look for."),
    line_start: int | None = typer.Option(None, "--line-start", help="1-based start line."),
    line_end: int | None = typer.Option(None, "--line-end", help="1-based end line."),
    slack: int = typer.Option(0, "--slack", help="Lines of slack around the window."),
) -> None:
    """Verify that a quote appears in a paper's source."""
    from papercheck.core.verify import verify_quote as _verify_quote

    found = _verify_quote(file, quote, line_start, line_end, slack)
    typer.echo("QUOTE FOUND" if found else "QUOTE NOT FOUND")
    raise typer.Exit(code=0 if found else 1)


@app.command()
def prompts(
    action: str = typer.Argument("list", help="Either 'list' or 'show'."),
    name: str | None = typer.Argument(None, help="Prompt name (for 'show')."),
) -> None:
    """Show the audit prompt pack ('list' names, or 'show <name>')."""
    from papercheck.mcp_server import handlers

    if action == "list":
        typer.echo(handlers.list_prompts())
        raise typer.Exit(0)
    if action == "show":
        if not name:
            typer.echo("prompts show requires a NAME argument")
            raise typer.Exit(2)
        try:
            typer.echo(handlers.get_prompt(name))
        except KeyError:
            typer.echo(f"No such prompt: {name}")
            raise typer.Exit(1) from None
        raise typer.Exit(0)
    typer.echo(f"Unknown action {action!r}; expected 'list' or 'show'")
    raise typer.Exit(2)


@app.command()
def report(
    paper_root: str = typer.Argument(..., help="Path to the paper's source root."),
) -> None:
    """Render a self-contained HTML audit report from the Paper_Audit artifacts."""
    from papercheck.core.html_report import render_html

    out = render_html(Path(paper_root))
    typer.echo(f"HTML report -> {out}")
    raise typer.Exit(0)


@app.command()
def compare(
    old_root: str = typer.Argument(..., help="Path to the OLD version's source root."),
    new_root: str = typer.Argument(..., help="Path to the NEW version's source root."),
) -> None:
    """Compare two versions of a paper and write a structural diff report."""
    from papercheck.core.compare import write_compare_report

    out = write_compare_report(Path(old_root), Path(new_root))
    typer.echo(f"Version comparison -> {out}")
    raise typer.Exit(0)


@app.command()
def profile(
    action: str = typer.Argument("list", help="Either 'list' or 'show'."),
    name: str | None = typer.Argument(None, help="Profile name (for 'show')."),
) -> None:
    """List advisory audit profiles, or show one profile's recommended steps."""
    from papercheck.core import profiles as profiles_mod

    if action == "list":
        for pname in profiles_mod.list_profiles():
            prof = profiles_mod.get_profile(pname)
            typer.echo(f"{pname}: {prof.get('description', '')}")
        raise typer.Exit(0)
    if action == "show":
        if not name:
            typer.echo("profile show requires a NAME argument")
            raise typer.Exit(2)
        try:
            prof = profiles_mod.get_profile(name)
        except KeyError:
            typer.echo(f"No such profile: {name}")
            raise typer.Exit(1) from None
        typer.echo(f"{name}: {prof.get('description', '')}")
        typer.echo(f"  mechanical_only: {prof.get('mechanical_only')}")
        typer.echo("  steps:")
        for step in prof.get("steps", []):
            typer.echo(f"    - {step}")
        raise typer.Exit(0)
    typer.echo(f"Unknown action {action!r}; expected 'list' or 'show'")
    raise typer.Exit(2)


@app.command()
def packs(
    action: str = typer.Argument("list", help="One of 'list', 'show', 'scaffold', 'create'."),
    name: str | None = typer.Argument(None, help="Pack name (for 'show')."),
    paper_root: str | None = typer.Option(
        None, "--paper-root", help="Paper root, for paper-local scaffold/create/generated packs."
    ),
) -> None:
    """Manage domain packs: list/show shipped packs, or scaffold/create one from a paper."""
    from papercheck.core import domainpack

    root = Path(paper_root) if paper_root else None

    if action == "list":
        for pname in domainpack.list_packs(root):
            typer.echo(pname)
        raise typer.Exit(0)
    if action == "show":
        if not name:
            typer.echo("packs show requires a NAME argument")
            raise typer.Exit(2)
        try:
            typer.echo(json.dumps(domainpack.load_pack(name, root), indent=2))
        except KeyError:
            typer.echo(f"No such domain pack: {name}")
            raise typer.Exit(1) from None
        except (RuntimeError, FileNotFoundError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(1) from None
        raise typer.Exit(0)
    if action == "scaffold":
        if root is None:
            typer.echo("packs scaffold requires --paper-root")
            raise typer.Exit(2)
        struct_path = paths.structure_file(root)
        if struct_path.exists():
            structure = json.loads(struct_path.read_text(encoding="utf-8"))
        else:
            structure = texscan.scan(root)
        typer.echo(json.dumps(domainpack.scaffold_pack(structure), indent=2))
        typer.echo("")
        typer.echo(
            "# Draft only. Refine the fields, save to a JSON file, "
            "then: papercheck packs create --paper-root <root> <file.json>"
        )
        raise typer.Exit(0)
    if action == "create":
        if root is None:
            typer.echo("packs create requires --paper-root")
            raise typer.Exit(2)
        if not name:
            typer.echo("packs create requires a PATH to a pack JSON file as NAME argument")
            raise typer.Exit(2)
        try:
            pack = json.loads(Path(name).read_text(encoding="utf-8"))
            out = domainpack.create_pack(root, pack)
        except (RuntimeError, FileNotFoundError) as exc:
            typer.echo(str(exc))
            raise typer.Exit(1) from None
        typer.echo(f"Domain pack -> {out}")
        raise typer.Exit(0)
    typer.echo(f"Unknown action {action!r}; expected list/show/scaffold/create")
    raise typer.Exit(2)


@app.command()
def serve(
    paper_root: str = typer.Argument(..., help="Path to the paper's source root."),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind (localhost)."),
    port: int = typer.Option(8765, "--port", help="Port to bind."),
    open_browser: bool = typer.Option(
        False, "--open", help="Open the UI in a web browser after starting."
    ),
) -> None:
    """Serve an interactive local web UI for a paper's audit state (blocking)."""
    from papercheck.core.webserve import serve as _serve

    _serve(Path(paper_root), host=host, port=port, open_browser=open_browser)


@app.command()
def mcp() -> None:
    """Run the papercheck MCP server (blocking stdio transport)."""
    from papercheck.mcp_server.server import main as _server_main

    _server_main()


if __name__ == "__main__":
    app()
