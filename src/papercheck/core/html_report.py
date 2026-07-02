"""Self-contained HTML audit report generator.

Reads whatever JSON artifacts exist under ``<paper_root>/Paper_Audit`` and
renders a single offline HTML file at ``Paper_Audit/report/index.html``. Missing
artifacts are treated as empty; the generator never raises on absent files.

Only the standard library is used (``json``, ``html``, ``pathlib``) so the
report has no external CSS/JS/CDN dependencies and renders offline.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

from papercheck.core import ledger, paths

_CLAIM_TRUNCATE = 160

_STYLE = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica,
    Arial, sans-serif;
  margin: 0; padding: 2rem; line-height: 1.45; color: #1a1a1a;
  background: #fafafa;
}
h1 { font-size: 1.6rem; margin: 0 0 0.25rem; }
h2 { font-size: 1.2rem; margin: 2rem 0 0.75rem; border-bottom: 2px solid #ddd;
  padding-bottom: 0.25rem; }
.meta { color: #555; font-size: 0.9rem; margin: 0.15rem 0; }
.banner { padding: 1rem 1.25rem; border-radius: 8px; margin: 1.25rem 0;
  color: #fff; }
.banner .verdict { font-size: 1.5rem; font-weight: 700; margin: 0; }
.banner.green { background: #1b7f37; }
.banner.amber { background: #b8860b; }
.banner.red { background: #b02a2a; }
.banner.gray { background: #666; }
table { border-collapse: collapse; width: 100%; font-size: 0.88rem;
  background: #fff; }
th, td { border: 1px solid #ddd; padding: 0.4rem 0.55rem; text-align: left;
  vertical-align: top; }
th { background: #f0f0f0; }
tr[data-status="PROPOSED"] td:first-child { border-left: 4px solid #b8860b; }
tr[data-status="ACCEPTED"] td:first-child { border-left: 4px solid #b02a2a; }
tr[data-status="REJECTED"] td:first-child { border-left: 4px solid #888; }
tr[data-status="NEEDS_MANUAL_CHECK"] td:first-child {
  border-left: 4px solid #2a6db0; }
ul { margin: 0.5rem 0; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.85em; }
.legend span { display: inline-block; margin-right: 1rem; font-size: 0.82rem; }
.swatch { display: inline-block; width: 0.8rem; height: 0.8rem;
  border-radius: 2px; vertical-align: middle; margin-right: 0.3rem; }
.empty { color: #777; font-style: italic; }
footer { margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid #ccc;
  color: #555; font-size: 0.85rem; }
"""


def _esc(value: object) -> str:
    """HTML-escape any value, rendering ``None`` as an empty string."""
    if value is None:
        return ""
    return html.escape(str(value))


def _read_json(path: Path) -> dict | list | None:
    """Return parsed JSON at ``path``, or ``None`` if missing/unreadable."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _truncate(text: str, limit: int = _CLAIM_TRUNCATE) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _banner_class(verdict: str) -> str:
    v = verdict.strip().upper()
    if v == "READY":
        return "green"
    if v == "READY AFTER MECHANICAL FIXES":
        return "amber"
    if v.startswith("NOT READY"):
        return "red"
    return "gray"


def _render_header(paper_root: Path, state: dict | None) -> str:
    stage = (state or {}).get("stage", "unknown")
    version = (state or {}).get("harness_version", "unknown")
    return (
        "<header>"
        "<h1>papercheck audit report</h1>"
        f"<p class='meta'>Paper root: <code>{_esc(paper_root)}</code></p>"
        f"<p class='meta'>Stage: {_esc(stage)}</p>"
        f"<p class='meta'>Harness version: {_esc(version)}</p>"
        "</header>"
    )


def _render_banner(gate: dict | None) -> str:
    if not gate:
        return (
            "<div class='banner gray'>"
            "<p class='verdict'>No verdict available</p>"
            "<p>final_gate.json was not found.</p></div>"
        )
    verdict = str(gate.get("verdict", "UNKNOWN"))
    cls = _banner_class(verdict)
    parts = [
        f"<div class='banner {cls}'>",
        f"<p class='verdict'>{_esc(verdict)}</p>",
    ]

    blockers = gate.get("blockers") or []
    if blockers:
        parts.append("<strong>Blockers</strong><ul>")
        for blocker in blockers:
            parts.append(f"<li>{_esc(blocker)}</li>")
        parts.append("</ul>")
    else:
        parts.append("<p>No blockers.</p>")
    parts.append("</div>")

    signals = gate.get("signals") or {}
    signal_keys = [
        "build_ok",
        "duplicate_labels",
        "unresolved_refs",
        "unresolved_citations",
        "draft_marker_count",
        "blocking_issue_count",
        "blocking_manual_count",
    ]
    parts.append("<table><thead><tr><th>signal</th><th>value</th></tr></thead><tbody>")
    for key in signal_keys:
        parts.append(
            f"<tr><td><code>{_esc(key)}</code></td>"
            f"<td>{_esc(signals.get(key))}</td></tr>"
        )
    parts.append("</tbody></table>")
    return "".join(parts)


def _render_issues(issues: list[dict]) -> str:
    legend = (
        "<div class='legend'>"
        "<span><span class='swatch' style='background:#b8860b'></span>PROPOSED</span>"
        "<span><span class='swatch' style='background:#b02a2a'></span>ACCEPTED</span>"
        "<span><span class='swatch' style='background:#888'></span>REJECTED</span>"
        "<span><span class='swatch' style='background:#2a6db0'></span>"
        "NEEDS_MANUAL_CHECK</span>"
        "</div>"
    )
    if not issues:
        return legend + "<p class='empty'>No issues recorded.</p>"

    rows = []
    for issue in issues:
        status = str(issue.get("status", ""))
        severity = issue.get("severity_final") or issue.get("severity_proposed")
        loc = issue.get("location") or {}
        line_start = loc.get("line_start")
        location = _esc(loc.get("file", ""))
        if line_start is not None:
            location += f":{_esc(line_start)}"
        quote_found = (issue.get("verification") or {}).get("quote_found")
        claim = _truncate(str(issue.get("claim", "")))
        rows.append(
            f"<tr data-status='{_esc(status)}'>"
            f"<td><code>{_esc(issue.get('issue_id'))}</code></td>"
            f"<td>{_esc(status)}</td>"
            f"<td>{_esc(severity)}</td>"
            f"<td>{_esc(issue.get('category'))}</td>"
            f"<td>{location}</td>"
            f"<td>{_esc(claim)}</td>"
            f"<td>{_esc(quote_found)}</td>"
            "</tr>"
        )
    header = (
        "<table><thead><tr>"
        "<th>Issue ID</th><th>status</th><th>severity</th><th>category</th>"
        "<th>location</th><th>claim</th><th>quote_found</th>"
        "</tr></thead><tbody>"
    )
    return legend + header + "".join(rows) + "</tbody></table>"


def _render_segments(segments: list[dict]) -> str:
    if not segments:
        return "<p class='empty'>No segments recorded.</p>"
    rows = []
    for seg in segments:
        rows.append(
            "<tr>"
            f"<td><code>{_esc(seg.get('segment_id'))}</code></td>"
            f"<td>{_esc(seg.get('title'))}</td>"
            f"<td>{_esc(seg.get('budget'))}</td>"
            f"<td>{_esc(seg.get('risk_score'))}</td>"
            f"<td>{_esc(seg.get('reason'))}</td>"
            "</tr>"
        )
    header = (
        "<table><thead><tr>"
        "<th>segment_id</th><th>title</th><th>budget</th><th>risk_score</th>"
        "<th>reason</th>"
        "</tr></thead><tbody>"
    )
    return header + "".join(rows) + "</tbody></table>"


def _render_manual_checks(checks: list[dict]) -> str:
    if not checks:
        return "<p class='empty'>No manual checks recorded.</p>"
    rows = []
    for check in checks:
        rows.append(
            "<tr>"
            f"<td><code>{_esc(check.get('check_id'))}</code></td>"
            f"<td>{_esc(check.get('question'))}</td>"
            f"<td>{_esc(check.get('blocking'))}</td>"
            f"<td>{_esc(check.get('resolved', False))}</td>"
            "</tr>"
        )
    header = (
        "<table><thead><tr>"
        "<th>id</th><th>question</th><th>blocking</th><th>resolved</th>"
        "</tr></thead><tbody>"
    )
    return header + "".join(rows) + "</tbody></table>"


def render_html(paper_root: Path) -> Path:
    """Render a self-contained HTML audit report and return its path."""
    paper_root = Path(paper_root)
    audit = paths.audit_dir(paper_root)

    state = _read_json(paths.state_file(paper_root))
    gate = _read_json(audit / "final_gate.json")
    segments = _read_json(paths.segments_file(paper_root))

    if not isinstance(state, dict):
        state = None
    if not isinstance(gate, dict):
        gate = None
    if not isinstance(segments, list):
        segments = []
    segments = sorted(segments, key=lambda s: str(s.get("segment_id", "")))

    try:
        issues = ledger.list_issues(paper_root)
    except (OSError, ValueError):
        issues = []
    try:
        manual_checks = ledger.list_manual_checks(paper_root)
    except (OSError, ValueError):
        manual_checks = []

    body = "".join(
        [
            _render_header(paper_root, state),
            _render_banner(gate),
            "<h2>Issues</h2>",
            _render_issues(issues),
            "<h2>Segments</h2>",
            _render_segments(segments),
            "<h2>Manual checks</h2>",
            _render_manual_checks(manual_checks),
            "<footer><p>Generated by papercheck.</p>"
            "<p>All findings are heuristic and must be independently verified "
            "before relying on them.</p></footer>",
        ]
    )

    document = (
        "<!DOCTYPE html>"
        "<html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>papercheck audit report</title>"
        f"<style>{_STYLE}</style></head>"
        f"<body>{body}</body></html>"
    )

    report_dir = audit / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / "index.html"
    out_path.write_text(document, encoding="utf-8")
    return out_path
