# Contributing to papercheck

Thanks for your interest. papercheck is small, deterministic, and deliberately
scoped. Please read the discipline notes below before opening a PR — they are
not negotiable for the v0.1 line.

## Setup

```bash
python -m pip install -e ".[dev]"
```

This installs papercheck in editable mode with the dev extras (`pytest`,
`ruff`).

## Run the tests

```bash
pytest -q
```

The suite is fully mechanical — no LLM calls, no network. It must stay green on
both Linux and Windows.

## Lint

```bash
ruff check .
```

CI runs the same command; keep it clean.

## Privacy check (required)

```bash
python scripts/privacy_check.py
```

This must exit 0. It scans the repository for forbidden identifiers tied to a
specific unpublished paper. **Never add paper-specific unpublished content** —
manuscripts, real author names, private quotes, or anything that identifies a
non-public paper — to this repository. Toy fixtures under `tests/fixtures/` are
synthetic and self-contained by design; keep them that way.

## Phase / spec discipline (v0.1)

The architecture is fixed for the v0.1 line. PRs that change these will be
declined:

- **No LLM provider code.** papercheck never calls a model API. The reasoning
  lives in the driving agent (Claude Code or any MCP client) or in a human. Do
  not add provider adapters, API clients, or keys.
- **JSON is the source of truth.** Issues, patches, segments, manual checks, and
  state are JSON validated against the schemas in `schemas/`. Markdown reports
  are *rendered from* JSON, never authored directly.
- **Gates are enforced in code.** Stage ordering and the final gate live in the
  Python core, not in prompts. Do not move enforcement into agent instructions.

If you have a change that needs one of these, open an issue to discuss it as a
future major-version direction first (see the deferred list in `PROGRESS.md`).

## How prompts are tested

Prompts and the audit workflow are validated in two tiers:

- **Tier 1 — mechanical fixtures.** The pytest suite exercises the deterministic
  core against the toy fixtures in `tests/fixtures/` (e.g. the label/ref fixture
  is mechanically detectable). This runs in CI.
- **Tier 2 — agent-eval.** A human or MCP agent runs the full audit workflow
  against the *semantic* fixtures and checks that planted defects are found and
  survive adjudication, and that the false-positive trap is correctly rejected.
  This is **not** run in CI (it requires an LLM). See
  [`docs/agent_eval.md`](docs/agent_eval.md) for the exact procedure, and use
  `scripts/agent_eval_report.py` to summarize a completed audit.

When you change a prompt, describe in your PR which fixtures you re-ran under
Tier 2 and what you observed.
