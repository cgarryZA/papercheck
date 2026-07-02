"""Drive the papercheck harness through the semantic eval fixtures.

This replays the model-derived findings in ``eval/findings.json`` through the
REAL harness path — init -> scan -> advance to AUDITING -> submit_issue (which
runs the quote/label/file verification gate) -> adjudicate_issue -> gate — then
scores each fixture with ``scripts/agent_eval_report.py``.

It calls no model: the findings were produced once by an LLM agent driving the
harness in-session (see ``docs/agent_eval.md``). Replaying them for free
regression-tests the intake gate + adjudication wiring: if a fixture's source
drifts so a recorded ``exact_quote`` no longer matches, ``submit_issue`` will
route the issue to ``REJECTED_SOURCE_TARGET_INVALID`` and the score will flip.

Run as::

    python eval/run_eval.py                     # audits tests/fixtures/* in place
    python eval/run_eval.py --fixtures-root DIR  # audit copies elsewhere
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))
if str(_REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from papercheck.mcp_server import handlers  # noqa: E402

FINDINGS_PATH = Path(__file__).resolve().parent / "findings.json"


def _load_findings() -> dict:
    return json.loads(FINDINGS_PATH.read_text(encoding="utf-8"))["fixtures"]


def audit_fixture(paper_root: Path, findings: list[dict]) -> dict:
    """Drive one fixture through the full harness path and return a summary.

    Returns ``{"accepted": [...ids], "rejected": [...ids], "invalid": [...ids]}``.
    """
    root = str(paper_root)
    handlers.init_audit(root, run_id="eval-run")
    handlers.run_scan(root)
    handlers.propose_segments(root)
    handlers.save_inventory_record(root, {"note": "eval inventory placeholder"})
    handlers.advance_stage(root, "AUDITING")

    accepted: list[str] = []
    rejected: list[str] = []
    invalid: list[str] = []

    for finding in findings:
        submitted = handlers.submit_issue(root, dict(finding["issue"]))
        issue_id = submitted["issue_id"]
        if submitted["status"] == "REJECTED_SOURCE_TARGET_INVALID":
            invalid.append(issue_id)
            continue
        handlers.adjudicate_issue(
            root,
            issue_id,
            decision=finding["decision"],
            rationale=finding["rationale"],
            adjudicator="eval-agent",
            severity_final=finding.get("severity_final"),
        )
        if finding["decision"] == "ACCEPT":
            accepted.append(issue_id)
        else:
            rejected.append(issue_id)

    handlers.advance_stage(root, "SYNTHESIZED")
    handlers.advance_stage(root, "ADJUDICATED")
    return {"accepted": accepted, "rejected": rejected, "invalid": invalid}


def run(fixtures_root: Path) -> int:
    from agent_eval_report import report  # from scripts/, on sys.path

    all_findings = _load_findings()
    exit_code = 0
    for name, findings in all_findings.items():
        paper_root = fixtures_root / name
        if not (paper_root / "main.tex").is_file():
            print(f"SKIP {name}: no main.tex under {paper_root}")
            continue
        result = audit_fixture(paper_root, findings)
        if result["invalid"]:
            print(
                f"!! {name}: {len(result['invalid'])} finding(s) failed "
                f"quote verification: {result['invalid']}"
            )
            exit_code = 1
        print("=" * 60)
        report(paper_root)
    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay eval findings through the harness.")
    parser.add_argument(
        "--fixtures-root",
        type=Path,
        default=_REPO_ROOT / "tests" / "fixtures",
        help="Directory containing the fixture subdirs (default: tests/fixtures).",
    )
    args = parser.parse_args(argv)
    return run(args.fixtures_root)


if __name__ == "__main__":
    sys.exit(main())
