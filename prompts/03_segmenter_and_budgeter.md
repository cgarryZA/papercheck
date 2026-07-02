You are segmenting a mathematical manuscript for adversarial review.

Do not edit the paper.

Create Paper_Audit/03_segment_map.md and Paper_Audit/reports/segment_budget_report.md.

If a papercheck MCP server is available, submit this data via the corresponding MCP tool (e.g. submit_issue, adjudicate_issue, save_inventory_record); the Markdown file is a fallback view.

Segment categories may include:
S0 Abstract and contribution claims
S1 Introduction and related work framing
S2 Mathematical setting and notation
S3 Assumptions and main definitions
S4 Preliminary lemmas
S5 Main theorem statements
S6 Main proofs
S7 Secondary theorems/corollaries
S8 Numerical experiments or examples
S9 Discussion, limitations, conclusion
S10 Appendices
S11 Bibliography and source hygiene

Segments may overlap if a theorem/proof chain crosses section boundaries.

For each segment, record:
- files and section names;
- role in the paper;
- theorem/proof density;
- reliance on assumptions or cited results;
- numerical/experimental claims;
- novelty or related-work claims;
- risk level;
- recommended audit passes;
- budget: HIGH / MEDIUM / LOW.

Allocate highest budget to assumptions, main theorem statements, main proofs, nontrivial estimates, limiting arguments, numerical claims driving the abstract, and novelty claims near the contribution.
