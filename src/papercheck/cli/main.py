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
def init() -> None:
    """Initialize a paper's audit workspace."""
    typer.echo("not implemented")


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
def segments() -> None:
    """Propose audit segments for a paper."""
    typer.echo("not implemented")


@app.command()
def gate() -> None:
    """Run the final gate checks for a paper."""
    typer.echo("not implemented")


@app.command()
def render() -> None:
    """Render audit reports for a paper."""
    typer.echo("not implemented")


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
def prompts() -> None:
    """Show the audit prompt pack."""
    typer.echo("not implemented")


@app.command()
def mcp() -> None:
    """Run the papercheck MCP server."""
    typer.echo("not implemented")


if __name__ == "__main__":
    app()
