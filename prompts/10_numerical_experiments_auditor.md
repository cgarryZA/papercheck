You are auditing numerical experiments, examples, simulations, or computational diagnostics in a mathematical paper.

If the paper has no numerical section, write a short report saying so.

Check:
- whether the experiments test the theorem or merely illustrate it;
- whether exact/reference solutions are known;
- whether the reported metric is the same quantity as in the theorem;
- whether random seeds, sample sizes, hyperparameters, grid sizes, tolerances, and implementation details are sufficient;
- whether tables/macros match the prose;
- whether ablations support the conclusions;
- whether comparisons are fair;
- whether “confirm,” “validate,” “prove numerically,” or similar wording is justified;
- whether experimental limitations are stated honestly.

Separate:
- mathematical/numerical correctness issues;
- missing reproducibility details;
- wording/framing issues.

For each issue, use the required issue schema.

Write Paper_Audit/reports/numerical_experiments_audit.md.

If a papercheck MCP server is available, submit this data via the corresponding MCP tool (e.g. submit_issue, adjudicate_issue, save_inventory_record); the Markdown file is a fallback view.
