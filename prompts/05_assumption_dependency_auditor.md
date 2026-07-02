You are building an assumption dependency graph for a mathematical paper.

Do not patch the paper.

Create Paper_Audit/05_assumption_dependency_graph.md and Paper_Audit/reports/assumption_dependency_audit.md.

If a papercheck MCP server is available, submit this data via the corresponding MCP tool (e.g. submit_issue, adjudicate_issue, save_inventory_record); the Markdown file is a fallback view.

For each assumption, record:
- exact statement;
- where it is introduced;
- every theorem/lemma/proof where it is used;
- whether the proof explicitly invokes it;
- whether the assumption appears stronger than needed;
- whether it appears insufficient;
- whether it risks circularity;
- constants or parameters controlled by the assumption;
- places where the paper uses the assumption before stating it.

Flag suspected hidden assumptions separately from confirmed missing assumptions.
