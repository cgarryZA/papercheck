# Agent-eval results

This records an in-session LLM-in-the-loop run of the semantic-fixture eval.
The findings were derived by an LLM agent (Claude) reading each fixture's source
and driving the papercheck harness — no API key, no paid CI. The recorded
findings live in `eval/findings.json` and are replayed deterministically by
`eval/run_eval.py` and `tests/test_agent_eval_replay.py`.

## How to re-run

- Free deterministic replay (in CI): `python -m pytest tests/test_agent_eval_replay.py`
  or `python eval/run_eval.py`.
- Live prompt-regression (re-derive findings from scratch with a model): follow
  `docs/agent_eval.md` in an agent session pointed at the papercheck MCP server.
  This is the only path that regression-tests the audit *prompts* themselves;
  it is intentionally not automated in CI (needs a model, is non-deterministic).

## Run: harness driven with model-derived findings

| Fixture | Planted defect | Outcome | Result |
|---|---|---|---|
| toy_bad_gronwall_constant | constant claimed T-independent but equals C₀·e^{LT} | 1 issue accepted, location matched | DEFECT FOUND ✓ |
| toy_missing_assumption | lemma uses integrability/measurability never assumed | 1 issue accepted, location matched | DEFECT FOUND ✓ |
| toy_overclaimed_abstract | abstract says "all continuous"; theorem only Lipschitz | 1 issue accepted, location matched | DEFECT FOUND ✓ |
| toy_false_positive_trap | correct 2n identity that looks suspicious | plausible objection raised, then rejected on adjudication | TRAP OK ✓ (nothing accepted) |

All four fixtures behaved as intended: the three real defects were found and
survived adjudication with a location match, and the trap's plausible-but-wrong
objection was rejected. No finding failed the `submit_issue` quote-verification
gate, confirming each recorded `exact_quote` still matches its fixture source.

Notes on what this does and does not prove:

- Proves: the intake gate (quote/label/file verification), the stage machine,
  and the accept/reject adjudication wiring carry a realistic audit end-to-end,
  and the shipped fixtures + `expected.json` + scorer agree.
- Does not prove: that a *fresh* model run would re-discover these defects — that
  is the live agent-eval, which must be run in an agent session (see above).
