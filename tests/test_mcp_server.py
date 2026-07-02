"""Lightweight, transport-free checks on the FastMCP server build."""

from __future__ import annotations

from papercheck.mcp_server import handlers
from papercheck.mcp_server.server import build_server

# Handler functions the server is expected to expose as tools.
_EXPECTED_HANDLERS = [
    "get_state",
    "get_structure",
    "get_segments",
    "get_theorem_inventory",
    "get_issue",
    "list_issues",
    "get_manual_checks",
    "read_source_window",
    "verify_quote",
    "init_audit",
    "run_scan",
    "propose_segments",
    "save_inventory_record",
    "advance_stage",
    "submit_issue",
    "adjudicate_issue",
    "add_manual_check",
    "resolve_manual_check",
    "plan_patch",
    "record_patch",
    "record_regression_result",
    "run_gate",
    "list_prompts",
    "get_prompt",
]


def test_build_server_succeeds() -> None:
    server = build_server()
    assert type(server).__name__ == "FastMCP"


def test_expected_handlers_exist() -> None:
    for name in _EXPECTED_HANDLERS:
        assert hasattr(handlers, name), f"missing handler {name}"
    # render is exposed via handlers.render_reports (avoids shadowing the module).
    assert hasattr(handlers, "render_reports")
