"""FastMCP server for papercheck.

:func:`build_server` constructs a :class:`FastMCP` instance and registers each
handler from :mod:`papercheck.mcp_server.handlers` as a thin tool wrapper.
Importing this module has no side effects; the blocking ``run()`` happens only
inside :func:`main` (or when the module is executed directly).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from papercheck.mcp_server import handlers


def build_server() -> FastMCP:
    """Build and return the papercheck FastMCP server with all tools registered."""
    mcp = FastMCP("papercheck")

    # -- read-only --------------------------------------------------------

    @mcp.tool()
    def get_state(paper_root: str) -> dict:
        """Return the paper's audit state."""
        return handlers.get_state(paper_root)

    @mcp.tool()
    def get_structure(paper_root: str) -> dict:
        """Return the parsed document structure."""
        return handlers.get_structure(paper_root)

    @mcp.tool()
    def get_segments(paper_root: str) -> list:
        """Return the proposed audit segments."""
        return handlers.get_segments(paper_root)

    @mcp.tool()
    def get_theorem_inventory(paper_root: str) -> list:
        """Return the theorem-like environments in the paper."""
        return handlers.get_theorem_inventory(paper_root)

    @mcp.tool()
    def get_issue(paper_root: str, issue_id: str) -> dict:
        """Return a single issue by id."""
        return handlers.get_issue(paper_root, issue_id)

    @mcp.tool()
    def list_issues(paper_root: str, status: str | None = None) -> list:
        """List all issues, optionally filtered by status."""
        return handlers.list_issues(paper_root, status)

    @mcp.tool()
    def get_manual_checks(paper_root: str) -> list:
        """Return all manual checks for the paper."""
        return handlers.get_manual_checks(paper_root)

    @mcp.tool()
    def read_source_window(
        paper_root: str, file: str, line_start: int, line_end: int
    ) -> dict:
        """Read a line window from a source file inside the paper root."""
        return handlers.read_source_window(paper_root, file, line_start, line_end)

    @mcp.tool()
    def verify_quote(
        paper_root: str,
        file: str,
        quote: str,
        line_start: int | None = None,
        line_end: int | None = None,
        slack: int = 0,
    ) -> dict:
        """Verify that a quote appears in a source file."""
        return handlers.verify_quote(
            paper_root, file, quote, line_start, line_end, slack
        )

    # -- mutating ---------------------------------------------------------

    @mcp.tool()
    def init_audit(
        paper_root: str, run_id: str, git_commit: str | None = None
    ) -> dict:
        """Initialize the audit workspace and scaffold its directories."""
        return handlers.init_audit(paper_root, run_id, git_commit)

    @mcp.tool()
    def run_scan(paper_root: str) -> dict:
        """Scan the paper's sources and advance to SCANNED."""
        return handlers.run_scan(paper_root)

    @mcp.tool()
    def propose_segments(paper_root: str) -> list:
        """Propose audit segments and advance to SEGMENTED."""
        return handlers.propose_segments(paper_root)

    @mcp.tool()
    def save_inventory_record(paper_root: str, record: dict) -> dict:
        """Append an inventory record and advance to INVENTORIED."""
        return handlers.save_inventory_record(paper_root, record)

    @mcp.tool()
    def advance_stage(paper_root: str, target: str) -> dict:
        """Advance the audit state to a target stage."""
        return handlers.advance_stage(paper_root, target)

    @mcp.tool()
    def submit_issue(paper_root: str, issue: dict) -> dict:
        """Submit an issue through the intake gate."""
        return handlers.submit_issue(paper_root, issue)

    @mcp.tool()
    def adjudicate_issue(
        paper_root: str,
        issue_id: str,
        decision: str,
        rationale: str,
        adjudicator: str,
        severity_final: str | None = None,
    ) -> dict:
        """Adjudicate an issue (ACCEPT / REJECT / NEEDS_MANUAL_CHECK)."""
        return handlers.adjudicate_issue(
            paper_root, issue_id, decision, rationale, adjudicator, severity_final
        )

    @mcp.tool()
    def add_manual_check(
        paper_root: str,
        question: str,
        needed_source: str | None = None,
        blocking: bool = True,
        owner: str = "human",
    ) -> dict:
        """Create a manual check for the human auditor."""
        return handlers.add_manual_check(
            paper_root, question, needed_source, blocking, owner
        )

    @mcp.tool()
    def resolve_manual_check(
        paper_root: str, check_id: str, resolution: str
    ) -> dict:
        """Resolve a manual check with a resolution."""
        return handlers.resolve_manual_check(paper_root, check_id, resolution)

    @mcp.tool()
    def plan_patch(paper_root: str, patch: dict) -> dict:
        """Record a planned patch over accepted issues."""
        return handlers.plan_patch(paper_root, patch)

    @mcp.tool()
    def record_patch(paper_root: str, patch: dict) -> dict:
        """Record an applied patch over accepted issues."""
        return handlers.record_patch(paper_root, patch)

    @mcp.tool()
    def record_regression_result(
        paper_root: str, issue_id: str, result: str
    ) -> dict:
        """Record a regression outcome for an issue."""
        return handlers.record_regression_result(paper_root, issue_id, result)

    @mcp.tool()
    def run_gate(paper_root: str, mechanical_only: bool = True) -> dict:
        """Run the final mechanical gate."""
        return handlers.run_gate(paper_root, mechanical_only)

    @mcp.tool()
    def render(paper_root: str) -> dict:
        """Render all audit reports."""
        return handlers.render_reports(paper_root)

    # -- prompts ----------------------------------------------------------

    @mcp.tool()
    def list_prompts() -> list:
        """List available prompt files."""
        return handlers.list_prompts()

    @mcp.tool()
    def get_prompt(name: str) -> str:
        """Return the text of a named prompt."""
        return handlers.get_prompt(name)

    return mcp


def main() -> None:
    """Build the papercheck FastMCP server and run it (blocking, stdio)."""
    build_server().run()


if __name__ == "__main__":
    main()
