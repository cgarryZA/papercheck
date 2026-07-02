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
    """Scan a paper's LaTeX sources into a structured representation."""
    root = Path(paper_root)
    result = texscan.scan(root)

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
    typer.echo(f"structure.json -> {paths.structure_file(root)}")
    raise typer.Exit(0)


@app.command()
def segments(
    paper_root: str = typer.Argument(..., help="Path to the paper's source root."),
) -> None:
    """Propose audit segments for a paper."""
    from papercheck.core import segments as segments_mod

    root = Path(paper_root)
    struct_path = paths.structure_file(root)
    if struct_path.exists():
        structure = json.loads(struct_path.read_text(encoding="utf-8"))
    else:
        structure = texscan.scan(root)

    records = segments_mod.write_segments(root, structure)

    budget_counts: dict[str, int] = {}
    for rec in records:
        budget_counts[rec["budget"]] = budget_counts.get(rec["budget"], 0) + 1
    summary = ", ".join(
        f"{level}={budget_counts.get(level, 0)}" for level in ("HIGH", "MEDIUM", "LOW")
    )
    typer.echo(f"Proposed {len(records)} segment(s): {summary}")
    typer.echo(f"segments.json -> {paths.segments_file(root)}")
    raise typer.Exit(0)


@app.command()
def gate(
    paper_root: str = typer.Argument(..., help="Path to the paper's source root."),
    mechanical_only: bool = typer.Option(
        False, "--mechanical-only", help="Run only the mechanical gate signals."
    ),
) -> None:
    """Run the final gate checks for a paper."""
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

    ready = result["verdict"] in {"READY", "READY AFTER MECHANICAL FIXES"}
    raise typer.Exit(0 if ready else 1)


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
def mcp() -> None:
    """Run the papercheck MCP server (blocking stdio transport)."""
    from papercheck.mcp_server.server import main as _server_main

    _server_main()


if __name__ == "__main__":
    app()
