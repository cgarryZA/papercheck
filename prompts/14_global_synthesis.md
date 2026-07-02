You are consolidating audit reports into a proposed issue ledger.

Read all reports in Paper_Audit/reports.

Create Paper_Audit/07_issue_ledger.proposed.md.

If a papercheck MCP server is available, submit this data via the corresponding MCP tool (e.g. submit_issue, adjudicate_issue, save_inventory_record); the Markdown file is a fallback view.

Merge duplicates. Preserve minority reports where a disagreement matters.

Every issue must have:
- unique Issue ID;
- source auditors;
- severity proposed;
- location;
- exact quote;
- claim being made;
- concrete failure mode;
- required fix;
- confidence;
- patch locality.

Do not adjudicate yet. Do not patch.

If an auditor raised a vague concern without quote or failure mode, move it to “rejected before adjudication / insufficiently specified”.
