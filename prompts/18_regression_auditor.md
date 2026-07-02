Audit only the changes made in this patch set.

Compare the current source against the issue ledger and patch reports.

Check whether every accepted issue was actually fixed, and whether any patch introduced a new inconsistency.

Return:
- FIXED
- PARTIALLY FIXED
- NOT FIXED
- NEW PROBLEM INTRODUCED

When recording via the MCP `record_regression_result` tool, the allowed result values are exactly `FIXED`, `PARTIALLY_FIXED`, `NOT_FIXED`, `NEW_PROBLEM` (any other value is rejected).

Check:
1. Did the patch break notation?
2. Did it weaken a theorem without updating later claims?
3. Did it introduce an undefined assumption?
4. Did it create contradiction with abstract/introduction?
5. Does the PDF still build?
6. Are numerical claims still aligned?

Write Paper_Audit/reports/regression_report.md.

If a papercheck MCP server is available, submit this data via the corresponding MCP tool (e.g. submit_issue, adjudicate_issue, save_inventory_record); the Markdown file is a fallback view.
