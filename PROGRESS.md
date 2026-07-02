# Build progress

A concise log of how papercheck v0.1 was built, phase by phase, with the test
count at the end of each phase.

## Phases

- **P0 — Repo bootstrap.** Package skeleton, `pyproject.toml` (hatchling),
  license, canonical `Paper_Audit/` path helpers, first smoke tests.
  *(tests: 4)*
- **P1 — Schemas + state machine.** JSON Schemas for issue / patch / segment /
  manual-check / state; the stage-gated `AuditState` with `require_at_least`.
  *(tests: 30)*
- **P2 — Scanner.** Deterministic regex TeX scanner producing `structure.json`
  (theorem envs, labels, refs, citations, draft markers). *(tests: 50, with P3)*
- **P3 — Verifiers.** Whitespace-normalized quote verifier, label/ref/cite/file
  verification, and issue intake that rejects unverifiable findings as
  `REJECTED_SOURCE_TARGET_INVALID`. *(tests: 50, with P2)*
- **P4 — Segments + gate + rendering.** Segment proposal, the mechanical final
  gate (build + label/ref/cite + draft-marker + open-blocker signals), and
  JSON→Markdown report rendering (e.g. `10_final_acceptance_gate.md`).
  *(tests: 61)*
- **P5 — MCP server.** FastMCP stdio server exposing 25 tools as thin wrappers
  over the deterministic core; `papercheck-mcp` entry point. *(tests: 73)*
- **P6 — Prompt pack + domain pack + fixtures.** Vendored prompt pack
  (`prompts/`), domain packs (`domain_packs/`), and the toy fixtures — including
  the semantic fixtures used for agent-eval. *(tests: 85)*
- **P7 — Docs + release polish.** README, `docs/` (limitations, comparison,
  privacy, agent-eval), `CITATION.cff`, `CONTRIBUTING.md`, this log, the
  non-LLM `scripts/agent_eval_report.py` helper, and `pyproject.toml` metadata
  (urls / keywords / classifiers). Packaging work brought the wheel data dirs
  and CI matrix to green. *(tests: 87, incl. packaging)*

Test-count progression: **P0: 4 → P1: 30 → P2/P3: 50 → P4: 61 → P5: 73 →
P6: 85 → packaging: 87.**

## Current status

- **v0.1 feature-complete.** 87 mechanical tests passing.
- **Wheel ships the data dirs** (`schemas/`, `prompts/`, `templates/`,
  `domain_packs/`) via hatch force-include.
- **CI is green** — lint (`ruff`) + `pytest` + privacy check, on Ubuntu and
  Windows.

## Explicitly deferred (out of scope for v0.1)

These are intentionally not built. See `CONTRIBUTING.md` for the discipline
notes.

- LLM **provider adapters** — papercheck never calls a model itself.
- **HTML report** output (Markdown only for now).
- **Version-compare** auditing across manuscript revisions.
- **Audit profiles** (preset severity / scope bundles).
- **LLM-in-CI** — Tier 2 agent-eval stays manual; CI runs no model.
- **More domain packs** beyond the two shipped.

## Deviations from spec

Small, deliberate departures worth recording:

- **Handler `render` → `render_reports`.** The MCP/handler entry point is named
  `render_reports` (the CLI command stays `render`) to avoid colliding with the
  core `render` module name.
- **Id-assign before schema-validate in `issues.py`.** `submit_issue` assigns a
  missing/blank `issue_id` *before* JSON-Schema validation, because a blank id
  fails the schema's id pattern; validation then runs on the completed record.
- **`amsthm` added to the clean fixture.** `tests/fixtures/toy_clean_paper`
  loads `amsthm` so theorem environments are well-formed and the fixture builds
  cleanly under the gate's latexmk build.
