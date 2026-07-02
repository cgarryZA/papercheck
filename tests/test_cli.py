"""CLI smoke tests: guard command registration and wiring for all commands.

These do not re-test core logic (covered elsewhere); they assert each command is
registered, dispatches to its core function, and returns sensible exit codes.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from papercheck.cli.main import app

runner = CliRunner()

FIXTURE = Path(__file__).parent / "fixtures" / "toy_clean_paper"


def _copy_fixture(tmp_path: Path) -> Path:
    dst = tmp_path / "paper"
    shutil.copytree(FIXTURE, dst)
    # Drop any pre-existing audit artifacts so each test starts clean.
    audit = dst / "Paper_Audit"
    if audit.exists():
        shutil.rmtree(audit)
    return dst


def test_help_lists_all_commands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in (
        "init",
        "scan",
        "segments",
        "gate",
        "render",
        "verify-quote",
        "prompts",
        "report",
        "compare",
        "profile",
        "packs",
        "mcp",
    ):
        assert cmd in result.output


def test_scan_and_gate(tmp_path: Path) -> None:
    paper = _copy_fixture(tmp_path)
    assert runner.invoke(app, ["scan", str(paper)]).exit_code == 0
    gate = runner.invoke(app, ["gate", str(paper), "--mechanical-only"])
    assert gate.exit_code == 0
    assert "READY" in gate.output


def test_report_writes_html(tmp_path: Path) -> None:
    paper = _copy_fixture(tmp_path)
    runner.invoke(app, ["gate", str(paper), "--mechanical-only"])
    result = runner.invoke(app, ["report", str(paper)])
    assert result.exit_code == 0
    assert (paper / "Paper_Audit" / "report" / "index.html").is_file()


def test_compare_self_is_clean(tmp_path: Path) -> None:
    paper = _copy_fixture(tmp_path)
    result = runner.invoke(app, ["compare", str(paper), str(paper)])
    assert result.exit_code == 0
    assert (paper / "Paper_Audit" / "version_comparison.md").is_file()


def test_profile_list_and_show() -> None:
    listing = runner.invoke(app, ["profile", "list"])
    assert listing.exit_code == 0
    assert "quick" in listing.output and "no-cloud" in listing.output
    show = runner.invoke(app, ["profile", "show", "quick"])
    assert show.exit_code == 0
    assert "scan" in show.output
    assert runner.invoke(app, ["profile", "show", "nope"]).exit_code == 1


def test_packs_list_scaffold_create(tmp_path: Path) -> None:
    paper = _copy_fixture(tmp_path)
    listing = runner.invoke(app, ["packs", "list"])
    assert listing.exit_code == 0
    assert "general" in listing.output
    runner.invoke(app, ["scan", str(paper)])
    scaffold = runner.invoke(app, ["packs", "scaffold", "--paper-root", str(paper)])
    assert scaffold.exit_code == 0
    # Persist the scaffold draft, then create a paper-local pack from it.
    draft = json.loads(scaffold.output.split("# Draft only")[0])
    pack_file = tmp_path / "pack.json"
    pack_file.write_text(json.dumps(draft), encoding="utf-8")
    created = runner.invoke(
        app, ["packs", "create", str(pack_file), "--paper-root", str(paper)]
    )
    assert created.exit_code == 0
    assert (paper / "Paper_Audit" / "domain_pack.json").is_file()
    generated = runner.invoke(app, ["packs", "list", "--paper-root", str(paper)])
    assert "generated" in generated.output
