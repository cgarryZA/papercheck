"""papercheck command-line interface.

Defines the Typer ``app`` and command stubs. Command bodies are filled in later
phases; for now they echo a placeholder so ``papercheck --help`` lists them all.
"""

from __future__ import annotations

import typer

app = typer.Typer(help="papercheck — audit harness for mathematical LaTeX papers")


@app.command()
def init() -> None:
    """Initialize a paper's audit workspace."""
    typer.echo("not implemented")


@app.command()
def scan() -> None:
    """Scan a paper's LaTeX sources into a structured representation."""
    typer.echo("not implemented")


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
def verify_quote() -> None:
    """Verify that a quote appears in a paper's source."""
    typer.echo("not implemented")


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
