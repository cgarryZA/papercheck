"""Interactive local web UI for a paper's audit state.

Serves a single self-contained HTML page (inline ``<style>`` + ``<script>``)
built live from the ``Paper_Audit`` JSON artifacts, plus a couple of small JSON
endpoints. Only the standard library is used (``http.server``, ``json``,
``html``, ``pathlib``, ``webbrowser``) so there is no external dependency and
everything binds to localhost.

Routing is factored into a pure :func:`_route` helper so it can be unit-tested
without binding a socket or blocking on ``serve_forever``.
"""

from __future__ import annotations

import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from papercheck.core import ledger, paths

_MAX_WINDOW_LINES = 400
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
tr.issue-row { cursor: pointer; }
tr.issue-row:hover td { background: #f4f8ff; }
tr.detail-row td { background: #fbfbfb; font-size: 0.85rem; }
tr.detail-row dl { margin: 0; display: grid;
  grid-template-columns: max-content 1fr; gap: 0.2rem 0.75rem; }
tr.detail-row dt { font-weight: 600; color: #444; }
tr.detail-row dd { margin: 0; }
.controls { display: flex; flex-wrap: wrap; gap: 0.75rem; margin: 0.75rem 0;
  align-items: center; }
.controls label { font-size: 0.82rem; color: #444; }
.controls select, .controls input {
  font-size: 0.85rem; padding: 0.25rem 0.4rem; }
.legend span { display: inline-block; margin-right: 1rem; font-size: 0.82rem; }
.swatch { display: inline-block; width: 0.8rem; height: 0.8rem;
  border-radius: 2px; vertical-align: middle; margin-right: 0.3rem; }
.empty { color: #777; font-style: italic; }
.count { color: #555; font-size: 0.82rem; }
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


def _json_for_script(payload: object) -> str:
    """Serialize ``payload`` for safe embedding inside a ``<script>`` tag.

    Escapes ``</`` as ``<\\/`` so the JSON cannot terminate the surrounding
    ``<script>`` element, and neutralizes the Unicode line/paragraph separators.
    """
    text = json.dumps(payload, ensure_ascii=False)
    text = text.replace("</", "<\\/")
    text = text.replace(" ", "\\u2028").replace(" ", "\\u2029")
    return text


# -- section renderers ----------------------------------------------------


def _render_header(paper_root: Path, state: dict | None) -> str:
    stage = (state or {}).get("stage", "unknown")
    version = (state or {}).get("harness_version", "unknown")
    return (
        "<header>"
        "<h1>papercheck audit</h1>"
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


def _issue_view(issue: dict) -> dict:
    """Flatten an issue into the shape consumed by the client-side renderer."""
    loc = issue.get("location") or {}
    severity = issue.get("severity_final") or issue.get("severity_proposed") or ""
    return {
        "issue_id": str(issue.get("issue_id", "")),
        "status": str(issue.get("status", "")),
        "severity": str(severity),
        "category": str(issue.get("category", "")),
        "claim": str(issue.get("claim", "")),
        "exact_quote": str(issue.get("exact_quote", "")),
        "concrete_failure_mode": str(issue.get("concrete_failure_mode", "")),
        "required_fix": str(issue.get("required_fix", "")),
        "file": str(loc.get("file", "")),
        "line_start": loc.get("line_start"),
        "line_end": loc.get("line_end"),
    }


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
    views = [_issue_view(i) for i in issues]

    statuses = sorted({v["status"] for v in views if v["status"]})
    severities = sorted({v["severity"] for v in views if v["severity"]})
    categories = sorted({v["category"] for v in views if v["category"]})

    def _opts(values: list[str]) -> str:
        out = ["<option value=''>all</option>"]
        for val in values:
            out.append(f"<option value='{_esc(val)}'>{_esc(val)}</option>")
        return "".join(out)

    controls = (
        "<div class='controls'>"
        f"<label>status <select id='f-status'>{_opts(statuses)}</select></label>"
        f"<label>severity <select id='f-severity'>{_opts(severities)}</select></label>"
        f"<label>category <select id='f-category'>{_opts(categories)}</select></label>"
        "<label>search <input id='f-search' type='search' "
        "placeholder='claim or quote'></label>"
        "<span class='count' id='issue-count'></span>"
        "</div>"
    )

    # Static, no-JS rows so that the issue ids / data-status attributes are
    # present even before the client script runs (and for the XSS assertions).
    static_rows = []
    for v in views:
        loc = _esc(v["file"])
        if v["line_start"] is not None:
            loc += f":{_esc(v['line_start'])}"
        static_rows.append(
            "<tr class='issue-row' "
            f"data-status='{_esc(v['status'])}' "
            f"data-severity='{_esc(v['severity'])}' "
            f"data-category='{_esc(v['category'])}'>"
            f"<td><code>{_esc(v['issue_id'])}</code></td>"
            f"<td>{_esc(v['status'])}</td>"
            f"<td>{_esc(v['severity'])}</td>"
            f"<td>{_esc(v['category'])}</td>"
            f"<td>{loc}</td>"
            f"<td>{_esc(_truncate(v['claim']))}</td>"
            "</tr>"
        )

    header = (
        "<table id='issue-table'><thead><tr>"
        "<th>Issue ID</th><th>status</th><th>severity</th><th>category</th>"
        "<th>location</th><th>claim</th>"
        "</tr></thead><tbody id='issue-body'>"
    )
    if not views:
        body = "<tr><td colspan='6' class='empty'>No issues recorded.</td></tr>"
    else:
        body = "".join(static_rows)
    table = header + body + "</tbody></table>"

    blob = (
        "<script id='issues-data' type='application/json'>"
        + _json_for_script(views)
        + "</script>"
    )
    return legend + controls + table + blob


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


_SCRIPT = """
(function () {
  var el = document.getElementById('issues-data');
  var issues = [];
  try { issues = JSON.parse(el.textContent || '[]'); } catch (e) { issues = []; }
  var body = document.getElementById('issue-body');
  var fStatus = document.getElementById('f-status');
  var fSeverity = document.getElementById('f-severity');
  var fCategory = document.getElementById('f-category');
  var fSearch = document.getElementById('f-search');
  var countEl = document.getElementById('issue-count');
  if (!body) { return; }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function locStr(v) {
    var s = esc(v.file || '');
    if (v.line_start != null) { s += ':' + esc(v.line_start); }
    return s;
  }

  function detailHtml(v) {
    var span = (v.line_start != null)
      ? '?file=' + encodeURIComponent(v.file) +
        '&start=' + encodeURIComponent(v.line_start) +
        '&end=' + encodeURIComponent(v.line_end != null ? v.line_end : v.line_start)
      : null;
    var loc = esc(v.file || '');
    if (v.line_start != null) { loc += ':' + esc(v.line_start); }
    if (span) { loc = '<a href="/api/source' + span + '">' + loc + '</a>'; }
    return '<dl>' +
      '<dt>exact_quote</dt><dd><code>' + esc(v.exact_quote) + '</code></dd>' +
      '<dt>failure_mode</dt><dd>' + esc(v.concrete_failure_mode) + '</dd>' +
      '<dt>required_fix</dt><dd>' + esc(v.required_fix) + '</dd>' +
      '<dt>location</dt><dd>' + loc + '</dd>' +
      '</dl>';
  }

  function passes(v) {
    if (fStatus.value && v.status !== fStatus.value) { return false; }
    if (fSeverity.value && v.severity !== fSeverity.value) { return false; }
    if (fCategory.value && v.category !== fCategory.value) { return false; }
    var q = (fSearch.value || '').toLowerCase().trim();
    if (q) {
      var hay = ((v.claim || '') + ' ' + (v.exact_quote || '')).toLowerCase();
      if (hay.indexOf(q) === -1) { return false; }
    }
    return true;
  }

  function render() {
    body.innerHTML = '';
    var shown = 0;
    issues.forEach(function (v, i) {
      if (!passes(v)) { return; }
      shown++;
      var tr = document.createElement('tr');
      tr.className = 'issue-row';
      tr.setAttribute('data-status', v.status || '');
      tr.setAttribute('data-severity', v.severity || '');
      tr.setAttribute('data-category', v.category || '');
      tr.innerHTML =
        '<td><code>' + esc(v.issue_id) + '</code></td>' +
        '<td>' + esc(v.status) + '</td>' +
        '<td>' + esc(v.severity) + '</td>' +
        '<td>' + esc(v.category) + '</td>' +
        '<td>' + locStr(v) + '</td>' +
        '<td>' + esc(v.claim) + '</td>';
      var detail = null;
      tr.addEventListener('click', function () {
        if (detail && detail.parentNode) {
          detail.parentNode.removeChild(detail);
          detail = null;
          return;
        }
        detail = document.createElement('tr');
        detail.className = 'detail-row';
        var td = document.createElement('td');
        td.colSpan = 6;
        td.innerHTML = detailHtml(v);
        detail.appendChild(td);
        tr.parentNode.insertBefore(detail, tr.nextSibling);
      });
      body.appendChild(tr);
    });
    if (shown === 0) {
      var tr = document.createElement('tr');
      tr.innerHTML = "<td colspan='6' class='empty'>No matching issues.</td>";
      body.appendChild(tr);
    }
    if (countEl) {
      countEl.textContent = shown + ' / ' + issues.length + ' shown';
    }
  }

  [fStatus, fSeverity, fCategory].forEach(function (c) {
    if (c) { c.addEventListener('change', render); }
  });
  if (fSearch) { fSearch.addEventListener('input', render); }
  render();
})();
"""


def build_page(paper_root: Path) -> str:
    """Return a full self-contained interactive HTML page for the audit state.

    All artifacts are read live from ``<paper_root>/Paper_Audit``. Missing
    artifacts are rendered as placeholders; the function never raises on absent
    files.
    """
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
            "<footer><p>Served by papercheck (interactive UI).</p>"
            "<p>All findings are heuristic and must be independently verified "
            "before relying on them.</p></footer>",
        ]
    )

    return (
        "<!DOCTYPE html>"
        "<html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>papercheck audit</title>"
        f"<style>{_STYLE}</style></head>"
        f"<body>{body}"
        f"<script>{_SCRIPT}</script>"
        "</body></html>"
    )


def read_source_window(
    paper_root: Path,
    rel_file: str,
    line_start: int,
    line_end: int,
) -> dict:
    """Return a 1-based line window from a source file inside the paper root.

    The resolved target path must stay within ``paper_root``; anything that
    escapes (``..`` traversal, absolute paths) raises :class:`ValueError`. The
    returned span is capped at :data:`_MAX_WINDOW_LINES` lines.
    """
    root = Path(paper_root).resolve()
    target = (root / rel_file).resolve()
    if target != root and not target.is_relative_to(root):
        raise ValueError("path escapes paper root")

    text = target.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    start = max(1, int(line_start))
    end = min(len(lines), int(line_end))
    if end < start:
        end = start
    end = min(end, start + _MAX_WINDOW_LINES - 1)

    window = lines[start - 1 : end]
    return {
        "file": rel_file,
        "line_start": start,
        "line_end": end,
        "text": "\n".join(window),
    }


# -- routing (pure, socket-free) ------------------------------------------


def _route(paper_root: Path, path_and_query: str) -> tuple[int, str, bytes]:
    """Resolve a GET request path to ``(status, content_type, body_bytes)``.

    Pure and side-effect free (apart from reading audit artifacts) so it can be
    unit-tested without binding a socket.
    """
    parts = urlsplit(path_and_query)
    path = parts.path
    query = parse_qs(parts.query)

    if path in ("/", "/index.html"):
        page = build_page(Path(paper_root))
        return 200, "text/html; charset=utf-8", page.encode("utf-8")

    if path == "/api/state":
        state = _read_json(paths.state_file(Path(paper_root)))
        if state is None:
            state = {}
        body = json.dumps(state).encode("utf-8")
        return 200, "application/json; charset=utf-8", body

    if path == "/api/source":
        rel = (query.get("file") or [None])[0]
        start_raw = (query.get("start") or [None])[0]
        end_raw = (query.get("end") or [None])[0]
        if rel is None or start_raw is None or end_raw is None:
            return _json_error(400, "missing file/start/end")
        try:
            start = int(start_raw)
            end = int(end_raw)
        except (TypeError, ValueError):
            return _json_error(400, "start/end must be integers")
        try:
            result = read_source_window(Path(paper_root), rel, start, end)
        except ValueError:
            return _json_error(403, "path escapes paper root")
        except (OSError, FileNotFoundError):
            return _json_error(404, "file not found")
        body = json.dumps(result).encode("utf-8")
        return 200, "application/json; charset=utf-8", body

    return _json_error(404, "not found")


def _json_error(status: int, message: str) -> tuple[int, str, bytes]:
    body = json.dumps({"error": message}).encode("utf-8")
    return status, "application/json; charset=utf-8", body


def make_handler(paper_root: Path) -> type[BaseHTTPRequestHandler]:
    """Return a ``BaseHTTPRequestHandler`` subclass bound to ``paper_root``."""
    root = Path(paper_root)

    class _Handler(BaseHTTPRequestHandler):
        server_version = "papercheck-webserve"

        def do_GET(self) -> None:  # noqa: N802  (http.server API name)
            status, content_type, body = _route(root, self.path)
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:  # noqa: A002
            """Silence the default stderr request logging."""

    return _Handler


def serve(
    paper_root: Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = False,
) -> None:
    """Serve the interactive audit UI on ``host:port`` (blocking)."""
    import webbrowser

    handler = make_handler(Path(paper_root))
    httpd = HTTPServer((host, port), handler)
    url = f"http://{host}:{port}/"
    print(f"papercheck serving audit UI at {url}  (Ctrl-C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
