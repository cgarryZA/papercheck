# Agent evaluation

papercheck is validated in two tiers. Tier 1 proves the *mechanics* are
deterministic. Tier 2 proves the *audit workflow* — driven by a real LLM agent —
actually finds semantic defects and does not invent them.

## Tier 1 — mechanical pytest (in CI)

```bash
pytest -q
```

This is the deterministic suite: scanner, state machine, verifiers, ledgers,
gate, renderer, schema validation. It uses the toy fixtures, including
`toy_bad_label_refs`, whose planted defects (duplicate label, unresolved ref,
unresolved citation, draft marker) are **mechanically** detectable and asserted
directly. Tier 1 makes **no LLM calls** and runs in CI on Linux and Windows.

## Tier 2 — agent-eval (NOT in CI)

Semantic defects — a wrong Grönwall-style constant, a silently missing
hypothesis, an overclaimed abstract — cannot be caught by regex. Catching them
depends entirely on the driving LLM. Tier 2 measures that.

Because it requires an LLM, **Tier 2 is not run in CI.** Run it manually.

### Fixtures under test

| fixture | expected outcome |
| ------- | ---------------- |
| `toy_bad_gronwall_constant` | planted defect **found** and **survives adjudication** (ACCEPTED) |
| `toy_missing_assumption`    | planted defect **found** and **survives adjudication** (ACCEPTED) |
| `toy_overclaimed_abstract`  | planted defect **found** and **survives adjudication** (ACCEPTED) |
| `toy_false_positive_trap`   | **nothing accepted** — the adjudicator REJECTs any issue raised here |

Each fixture's `expected.json` describes the planted defect (or, for the trap,
that there is none). Read it before scoring — it gives `defect_type`,
`location_hint`, `severity`, and for the trap `expected_adjudication: "REJECT"`.

### Procedure

Do this once per fixture. Use a scratch copy so you don't leave audit output in
the repo working tree.

1. **Point an MCP client at the server.** In Claude Code:

   ```bash
   claude mcp add papercheck -- papercheck-mcp
   ```

2. **Copy the fixture to a scratch directory** (keeps `tests/fixtures/` clean):

   ```bash
   cp -r tests/fixtures/toy_bad_gronwall_constant /tmp/pc_eval/toy_bad_gronwall_constant
   ```

3. **Ask the agent to audit it**, e.g. "audit the paper in
   `/tmp/pc_eval/toy_bad_gronwall_constant` with papercheck". The agent should
   walk the workflow via the MCP tools:

   ```
   init -> scan -> segment -> audit -> synthesize -> adjudicate -> gate
   ```

   Do **not** tell the agent what the planted defect is — that defeats the eval.

4. **Summarize the result** with the non-LLM helper:

   ```bash
   python scripts/agent_eval_report.py /tmp/pc_eval/toy_bad_gronwall_constant
   ```

   The helper reads `Paper_Audit/issues/*/*.json` and the fixture's
   `expected.json` and prints proposed/accepted/rejected counts and whether an
   accepted issue matches the expected `location_hint` / `defect_type`.

### What "pass" means, per fixture

For the three defect fixtures (`toy_bad_gronwall_constant`,
`toy_missing_assumption`, `toy_overclaimed_abstract`):

- At least one issue is **ACCEPTED** by the adjudicator, and
- an accepted issue's location plausibly matches the fixture's
  `location_hint` (e.g. "proof of Theorem 1", "abstract vs statement of
  Theorem 1"), and its subject matches the `defect_type`.

For `toy_false_positive_trap`:

- **No issue is accepted.** The "by symmetry" step and the `2n` constant in this
  fixture are *correct* (see the `note` field of its `expected.json`). A correct
  audit either raises nothing or raises issues that the adjudicator **REJECTs**.
  Any ACCEPTED issue here is a failure of the eval.

Because the agent's reasoning is non-deterministic, treat Tier 2 as a
qualitative gate over a few runs, not a single pass/fail number. The location
matching in the helper is a heuristic aid — always read the accepted issues
yourself against `expected.json` before declaring a pass.

## Free deterministic replay (in CI)

The live Tier 2 run above re-derives findings with a model. Once derived, the
findings are recorded in `eval/findings.json` and replayed for free — no API
key, no model — by `eval/run_eval.py` and `tests/test_agent_eval_replay.py`:

```bash
python eval/run_eval.py            # audits tests/fixtures/* and prints scores
pytest tests/test_agent_eval_replay.py
```

This replay drives the SAME harness path (init -> scan -> submit_issue intake
gate -> adjudicate) and asserts the three real defects are accepted with a
location match and the trap is rejected. It regression-tests the gate +
adjudication wiring and catches fixture-source drift (a recorded `exact_quote`
that no longer matches its source fails `submit_issue` verification). It does
NOT re-test the prompts — only a fresh live run does that. The latest recorded
run is in `eval/RESULTS.md`.
