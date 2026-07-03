"""P4.7 — the CLI and the MCP server drive one shared state machine.

Before this, CLI ``scan``/``segments`` were stateless, so an agent that started
at the CLI and switched to MCP ``submit_issue`` found the state still at INIT.
Now the stateful CLI verbs auto-initialize and advance the shared state.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from typer.testing import CliRunner

from papercheck.cli.main import app
from papercheck.core.state import AuditState, StateError
from papercheck.mcp_server import handlers

runner = CliRunner()
FIXTURE = Path(__file__).parent / "fixtures" / "toy_clean_paper"


def _fresh(tmp_path: Path) -> Path:
    dst = tmp_path / "paper"
    shutil.copytree(FIXTURE, dst)
    audit = dst / "Paper_Audit"
    if audit.exists():
        shutil.rmtree(audit)
    return dst


def test_ensure_at_least_walks_forward_and_is_idempotent(tmp_path: Path) -> None:
    st = AuditState.init(tmp_path, run_id="t", harness_version="x", git_commit=None)
    st.ensure_at_least("SEGMENTED")
    assert st.stage == "SEGMENTED"
    for s in ("INIT", "SCANNED", "SEGMENTED"):
        assert s in st.completed_stages
    # Already at/after target -> no-op, no backward transition.
    st.ensure_at_least("SCANNED")
    assert st.stage == "SEGMENTED"


def test_bare_scan_autoinits_and_advances(tmp_path: Path) -> None:
    paper = _fresh(tmp_path)
    # No `init` first — scan must auto-initialize and reach SCANNED.
    assert runner.invoke(app, ["scan", str(paper)]).exit_code == 0
    assert handlers.get_state(str(paper))["stage"] == "SCANNED"


def test_cli_then_mcp_share_one_machine(tmp_path: Path) -> None:
    paper = _fresh(tmp_path)
    runner.invoke(app, ["scan", str(paper)])
    runner.invoke(app, ["segments", str(paper)])
    # The CLI advanced the persisted state the MCP server reads.
    assert handlers.get_state(str(paper))["stage"] == "SEGMENTED"
    # Two more genuine workflow stages and MCP submit_issue is reachable.
    handlers.advance_stage(str(paper), "INVENTORIED")
    handlers.advance_stage(str(paper), "AUDITING")
    assert handlers.get_state(str(paper))["stage"] == "AUDITING"


def test_rerun_scan_after_auditing_does_not_crash(tmp_path: Path) -> None:
    paper = _fresh(tmp_path)
    runner.invoke(app, ["scan", str(paper)])
    runner.invoke(app, ["segments", str(paper)])
    handlers.advance_stage(str(paper), "INVENTORIED")
    handlers.advance_stage(str(paper), "AUDITING")
    # Re-scanning at a later stage must be a no-op on state, not a backward move.
    handlers.run_scan(str(paper))
    assert handlers.get_state(str(paper))["stage"] == "AUDITING"


def test_segments_before_scan_still_guarded(tmp_path: Path) -> None:
    # propose_segments keeps its require_at_least("SCANNED") guard for MCP callers.
    paper = _fresh(tmp_path)
    handlers.init_audit(str(paper), run_id="t")
    try:
        handlers.propose_segments(str(paper))
    except StateError:
        pass
    else:  # pragma: no cover - guard must hold
        raise AssertionError("propose_segments should require SCANNED")
