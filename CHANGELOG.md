# Changelog

All notable changes to papercheck are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] — 2026-07-02

### Fixed

- README now uses absolute URLs for the logo and internal doc links so it
  renders correctly on PyPI (relative paths produced a broken image there).
- Corrected the `project.urls` metadata (Homepage/Repository) that still
  pointed at a placeholder owner; added Issues and Changelog links.

## [0.3.0] — 2026-07-02

### Added

- **LaTeX-AST scanner** — `texscan.scan` now builds a real LaTeX node tree
  (via `pylatexenc`) instead of regex/line matching, with a graceful regex
  fallback on malformed input. Output schema is unchanged.
- **Interactive web UI** — `papercheck serve <paper_root>` starts a local
  stdlib HTTP server with a filterable issue table (by status/severity/category)
  and click-to-source; jailed source reader, XSS-safe rendering.

### Fixed

- Single-line `\begin{theorem}\label{...}...\end{theorem}` now attributes the
  label to the theorem environment; macro-defined (`\newtheorem`) and nested
  environments are handled.

## [0.2.0] — 2026-07-02

### Added

- **HTML audit report** — `papercheck report <paper_root>` writes a
  self-contained HTML report to `Paper_Audit/report/index.html` with verdict
  banner, issue table, segments, and manual checks.
- **Version-compare command** — `papercheck compare <old_root> <new_root>`
  produces a structural diff of two paper versions (theorems by label,
  abstract, labels, citations, equations) and writes `Paper_Audit/version_comparison.md`.
- **Audit profiles** — `papercheck profile [list|show <name>]` exposes advisory
  audit profiles (quick, arxiv, full, journal, no-cloud), each with an ordered
  sequence of recommended steps and a mechanical_only flag. Profiles are
  advisory only; papercheck does not execute them automatically.
- **Domain pack generator and CLI** — `papercheck packs [list|show <name>|scaffold
  --paper-root <root>|create <file.json> --paper-root <root>]` enables building
  paper-specific domain packs. Scaffold deterministically extracts structure;
  create validates and persists a filled-in pack to `Paper_Audit/domain_pack.json`.
- **Four new MCP tools** — `list_domain_packs`, `get_domain_pack`,
  `scaffold_domain_pack`, `create_domain_pack`. Agents fill in domain knowledge;
  papercheck validates and stores it.
- **New shipped domain packs** — `pde`, `optimization`, `machine_learning`,
  `general` (fully generic) join existing `stochastic_analysis`, `numerical_analysis`.
- **End-user GitHub Action** — composite action in `action.yml` + example
  workflow (`.github/workflows/example-paper-audit.yml`) + documentation
  (`docs/ci.md`) for running mechanical-only checks (scan, segments, gate
  --mechanical-only) in CI without sending the manuscript to external services.
- **29 MCP tools** (up from 25) — all new tools wired to the stdio MCP server.
- **118 mechanical tests** — all passing; includes 31 new tests for v0.2 features.

## [0.1.0] — 2026-06-01

### Added

- **Deterministic LaTeX scanner** — regex-based structure extraction producing
  `structure.json` (theorems, labels, refs, citations, draft markers) with no
  guessing and no network calls.
- **Stage-gated state machine** — fixed workflow stages (INIT → SCANNED →
  SEGMENTED → INVENTORIED → AUDITING → SYNTHESIZED → ADJUDICATED →
  PATCH_PLANNED → PATCHING → REGRESSED → GATED) enforced in code.
- **Schema-validated ledgers** — JSON Schemas for issues, patches, segments,
  manual checks, and state; unverifiable findings rejected as
  `REJECTED_SOURCE_TARGET_INVALID` before entering the ledger.
- **Verified issue intake** — exact quote verification, label/ref/cite/file
  checking, with unverifiable issues rejected mechanically.
- **Mechanical final gate** — code-enforced verdict (READY / NOT READY) based on
  build status, label/ref/cite counts, draft markers, and open blockers.
- **Markdown report rendering** — JSON-to-Markdown for all workflow stages
  (e.g., `10_final_acceptance_gate.md`).
- **Typer CLI** — 7 commands (scan, segments, render, init, submit-issue,
  adjudicate, gate) with full help text.
- **FastMCP stdio server** — 25 tools exposing the deterministic core to any
  MCP-capable agent (e.g., Claude Code).
- **Vendored prompt pack** — domain-agnostic auditing prompt in `prompts/`.
- **Shipped domain packs** — `stochastic_analysis`, `numerical_analysis` in
  `domain_packs/` with categorized theorem types and technique keywords.
- **Evaluation fixtures** — toy papers (clean, draft-marked, unresolved refs)
  for testing and agent-eval workflows.
- **CI + packaging** — green `ruff` lint, 87 mechanical tests, privacy check,
  wheel with bundled data dirs (schemas, prompts, templates, domain_packs).
