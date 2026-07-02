# papercheck

*A reproducible audit harness for mathematical LaTeX papers.*

papercheck turns a mathematical paper into a stage-gated adversarial audit —
deterministic structure extraction, schema-validated issue ledgers with
mechanical quote verification, and a final gate that any MCP-capable agent can
drive but cannot skip.

## What it does in 10 seconds

- **Deterministic scanner** — parses your LaTeX sources into a structured
  `structure.json` (theorems, labels, refs, citations, draft markers) with no
  guessing and no network calls.
- **Stage-gated state machine** — the audit advances through fixed stages and
  refuses out-of-order operations (you cannot plan a patch before an issue is
  adjudicated).
- **Verified issues** — every finding must quote the source exactly; quotes,
  labels, and files are mechanically checked at intake, and unverifiable issues
  are rejected (`REJECTED_SOURCE_TARGET_INVALID`) before they can enter the
  ledger.
- **Mechanical final gate** — a code-enforced gate reports build status and
  blocking signals and emits a `READY` / `NOT READY` verdict.
- **MCP + CLI** — drive it from a Typer CLI or from any MCP client (e.g. Claude
  Code) via a FastMCP server exposing 25 tools plus a vendored prompt pack.

## Quickstart (CLI)

```bash
pipx install papercheck        # or: pip install papercheck
papercheck scan     path/to/paper
papercheck segments path/to/paper
papercheck gate     path/to/paper --mechanical-only
```

Run it on the bundled example:

```bash
papercheck gate tests/fixtures/toy_clean_paper --mechanical-only
# -> prints READY
```

## CLI commands

- `scan <paper_root>` — deterministic structure extraction to `structure.json`.
- `segments <paper_root>` — partition the paper into proof segments.
- `gate <paper_root> [--mechanical-only]` — run the final acceptance gate (mechanical signals only or with LLM audit findings).
- `render <paper_root>` — render a Markdown report from the ledger.
- `report <paper_root>` — write a self-contained HTML audit report to `Paper_Audit/report/index.html`.
- `compare <old_root> <new_root>` — structural diff of two paper versions (theorems, abstract, labels, citations, equations).
- `profile [list|show <name>]` — list and inspect advisory audit profiles (quick, arxiv, full, journal, no-cloud).
- `packs [list|show <name>|scaffold --paper-root <root>|create <file.json> --paper-root <root>]` — manage domain packs.

## Domain packs

papercheck ships generic domain packs (`pde`, `optimization`, `machine_learning`, `general`, `stochastic_analysis`, `numerical_analysis`) that define domain-specific fields (e.g. theorem categories, technique keywords). You can scaffold a paper-specific pack deterministically using `papercheck packs scaffold --paper-root <root>`, or fill one in and create it with `papercheck packs create <file.json> --paper-root <root>`. The driving agent (e.g. Claude Code) supplies domain knowledge; papercheck validates and stores the result to `Paper_Audit/domain_pack.json`. Four MCP tools expose domain-pack operations to agents.

A rendered `10_final_acceptance_gate.md` for a clean paper looks like:

```markdown
Final verdict: READY

| signal                  | value |
| ----------------------- | ----- |
| build_ok                | true  |
| duplicate_labels        | 0     |
| unresolved_refs         | 0     |
| unresolved_citations    | 0     |
| draft_marker_count      | 0     |
| blocking_issue_count    | 0     |
| blocking_manual_count   | 0     |

Final rationale: no mechanical blockers; no accepted issues open.
```

## Quickstart (MCP / Claude Code)

Register the stdio server with Claude Code:

```bash
claude mcp add papercheck -- papercheck-mcp
```

Both `papercheck-mcp` and `papercheck mcp` start the same stdio MCP server.

Then just ask the agent to **"audit this paper with papercheck"**. The agent
walks the workflow — init → scan → segment → audit → adjudicate → gate — by
calling the MCP tools, while the harness enforces stage order and quote
verification in code.

> **Note:** papercheck does not call any LLM itself. The reasoning lives in the
> driving agent (Claude Code or any MCP client), or a human runs the CLI. There
> are no provider adapters. LLM-produced findings must be independently checked.

## How it prevents the failure modes

- **Quotes that don't match the source are rejected** before entering the
  ledger — an issue whose `exact_quote`, label, or file cannot be verified is
  stored as `REJECTED_SOURCE_TARGET_INVALID`, never as a live finding.
- **Patches are refused before adjudication** — the state machine will not let
  you plan or apply a patch for an issue that has not been accepted.
- **The gate is enforced in code** — the `READY` verdict comes from mechanical
  signals (build, labels, refs, citations, draft markers, open blockers), not
  from an agent's say-so.

## Workflow

The audit advances through these stages, in order:

```
INIT -> SCANNED -> SEGMENTED -> INVENTORIED -> AUDITING -> SYNTHESIZED
     -> ADJUDICATED -> PATCH_PLANNED -> PATCHING -> REGRESSED -> GATED
```

See [`docs/workflow.md`](docs/workflow.md) for what each stage produces.

## Limitations

See [`docs/limitations.md`](docs/limitations.md) for the full scope. In short:

- **Not a theorem prover** — it does not verify mathematics; it structures and
  gates an audit.
- **Not a replacement for peer review.**
- **May miss semantic errors** — semantic detection depends entirely on the
  driving LLM (or human); the regex scanner can miss macro-hidden structure.
- **Findings must be independently checked** — LLM-produced issues are
  proposals, not proofs.

## Privacy

**papercheck sends nothing over the network; however, the LLM agent you use to
drive it may transmit your manuscript to its model provider. Review your
agent/provider's data terms before auditing unpublished work.**

See [`docs/privacy.md`](docs/privacy.md).

## GitHub Action (mechanical-only checks)

A composite GitHub Action runs the deterministic scanner and gate on every push, producing a `Paper_Audit/` artifact without any LLM calls. See [`docs/ci.md`](docs/ci.md) for setup and configuration.

## License

MIT — see [`LICENSE`](LICENSE).

Prompt pack and domain packs live in `prompts/` and `domain_packs/`.
