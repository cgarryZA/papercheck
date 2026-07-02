# Limitations

papercheck is a harness that *structures and gates* an audit. It is not a proof
checker. Read this before relying on its output.

## What papercheck is NOT

- **Not a theorem prover.** It never verifies that a lemma is true or that a
  proof is valid. It has no notion of mathematical correctness of its own.
- **Not a replacement for peer review.** It cannot judge novelty, significance,
  or whether a result matters. A `READY` verdict means "no mechanical blockers
  and no open accepted issues" — not "this paper is correct."
- **Not a semantic error detector on its own.** Detection of a wrong constant,
  a missing hypothesis, or an overclaimed abstract depends **entirely on the
  driving LLM or human auditor**. papercheck records and verifies their
  findings; it does not produce them.

## Where the mechanics can miss things

- **The scanner is regex-based.** It extracts structure — theorem environments,
  labels, `\ref`/`\eqref`, `\cite`, draft markers — by pattern matching. It can
  miss structure hidden behind custom macros, unusual environment definitions,
  or heavy `\input`/`\include` indirection it does not follow. Treat
  `structure.json` as a best-effort index, not a complete parse.
- **The final gate only checks mechanical signals.** It looks at build status,
  duplicate labels, unresolved refs/citations, draft-marker count, and the count
  of open blocking issues/manual checks. It does not read prose or evaluate
  mathematics. A paper can be badly wrong and still pass the mechanical gate.
- **The quote verifier uses whitespace-normalized substring matching.** An
  issue's `exact_quote` must appear (up to whitespace) as a literal substring of
  the cited source. This will **not** match a paraphrase, a re-typeset formula,
  or text reconstructed from memory — by design, so that findings stay anchored
  to real source locations.

## What IS reliable

These are deterministic and covered by the mechanical test suite:

- **Structure extraction** — the same sources always yield the same
  `structure.json`.
- **Quote / label / ref / cite verification** — an issue that quotes text not
  present in the source, or names a label/file that does not exist, is rejected
  at intake (`REJECTED_SOURCE_TARGET_INVALID`).
- **Stage gating** — operations are refused unless the audit is at the required
  stage; you cannot skip ahead (e.g. plan a patch before adjudication).
- **Schema validation** — every issue, patch, segment, and manual-check record
  is validated against a JSON Schema before it is written.

## Practical guidance

- Every accepted issue is a **proposal to be independently checked**, especially
  when produced by an LLM.
- A clean mechanical gate is a *floor*, not a *ceiling*: it confirms the paper
  builds and is internally consistent at the label/ref level, nothing more.
- Use the semantic fixtures and the agent-eval procedure
  (see [`agent_eval.md`](agent_eval.md)) to sanity-check how well your driving
  agent actually finds planted defects — the mechanical suite cannot do that.
