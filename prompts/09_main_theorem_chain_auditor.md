You are auditing the main theorem chain of a mathematical paper.

Identify the theorem or theorem cluster that supports the main contribution claimed in the abstract.

Verify the complete chain:

assumptions
-> definitions
-> candidate/admissible object
-> residual/error/energy/defect/key quantity
-> identity or decomposition
-> stability/coercivity/compactness/estimate
-> main theorem
-> interpretation in introduction/experiments

Check:
1. The main quantity is defined in the correct space/norm.
2. The admissible class is explicit.
3. Every term in the theorem appears in the proof.
4. There are no missing terminal/boundary/initial terms.
5. Signs and constants are consistent.
6. No term is double-counted or silently dropped.
7. The theorem proves the direction claimed: reliability, efficiency, equivalence, convergence, stability, uniqueness, etc.
8. The abstract and introduction do not claim more than the theorem proves.

For each issue, use the required issue schema.

Write Paper_Audit/reports/main_theorem_chain_audit.md.

If a papercheck MCP server is available, submit this data via the corresponding MCP tool (e.g. submit_issue, adjudicate_issue, save_inventory_record); the Markdown file is a fallback view.
