# Privacy

## The harness sends nothing

papercheck's Python core — the scanner, state machine, verifiers, ledgers,
renderer, CLI, and MCP server — makes **no network calls**. It reads your LaTeX
sources from disk and writes audit artifacts back to disk under
`Paper_Audit/`. Nothing about your manuscript leaves your machine because of
papercheck itself.

## The agent driving it might

**papercheck sends nothing over the network; however, the LLM agent you use to
drive it may transmit your manuscript to its model provider. Review your
agent/provider's data terms before auditing unpublished work.**

When you drive papercheck from an MCP client (e.g. Claude Code), that client
sends prompts — which can include quoted passages of your paper — to its model
provider so the model can reason about the mathematics. That transmission is a
property of *your agent and its provider*, not of papercheck. papercheck has no
provider adapters and no API keys.

If you are auditing an unpublished paper, this is the part to scrutinize:

- Read your agent's and provider's data-retention and training-use terms.
- Prefer providers/plans that do not retain or train on submitted content when
  the manuscript is confidential.
- If in doubt, run the deterministic parts via the CLI (`scan`, `segments`,
  `gate`, `render`, `verify-quote`), which never involve a model.

## Audit artifacts stay local and out of version control

Audit output is written under `Paper_Audit/` in the paper's directory. That
directory is **gitignored by default** (see the repository `.gitignore`), so
issue ledgers and reports are not accidentally committed. If you keep audits in
their own repository, replicate that ignore rule.
