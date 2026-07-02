# How papercheck compares

papercheck occupies a specific niche. It is easy to mistake it for tools it does
not replace.

## papercheck is NOT

- **A prover (Lean / Coq / Isabelle).** Interactive theorem provers check that a
  formalized proof is *valid*. papercheck does not formalize anything and makes
  no correctness guarantee about the mathematics.
- **A LaTeX linter (chktex / lacheck).** Linters flag typesetting and markup
  issues. papercheck does read structure from the LaTeX, but its purpose is to
  organize a *content* audit, not to police markup style.
- **A replacement for peer review.** It does not assess novelty, significance,
  or fit. Human reviewers remain necessary.

## papercheck IS

- **A stage-gated review harness** — it drives an audit through fixed stages
  (scan → segment → inventory → audit → synthesize → adjudicate → patch → gate)
  and refuses out-of-order steps.
- **A reproducibility layer** — deterministic structure extraction plus
  JSON-Schema-validated ledgers mean the same inputs and decisions yield the
  same artifacts, and every artifact is machine-checkable.
- **A traceability layer** — it structures an **LLM-or-human** audit and makes
  every finding traceable to an *exact* source location, because quotes, labels,
  and files are mechanically verified before an issue can enter the ledger.

## Where it sits alongside those tools

papercheck is complementary, not competitive. You might still run `chktex` for
markup, still ask reviewers to judge significance, and (if you formalize) still
use a prover for the mathematics. papercheck's contribution is the scaffolding
in between: a disciplined, reproducible, location-anchored record of an audit
that an LLM agent or a human can drive but cannot fudge.
