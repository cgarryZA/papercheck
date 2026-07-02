You are the final mathematical adjudicator for an adversarial audit of a mathematical paper.

Your job is not to be nice to the paper and not to be nice to the auditors. Your job is to decide which issues are real.

Read:
- Paper_Audit/07_issue_ledger.proposed.md
- all audit reports
- the relevant source locations in the manuscript

For each proposed issue, decide:
- ACCEPT
- REJECT
- NEEDS MANUAL CHECK

Acceptance rules:
1. ACCEPT only if the issue has an exact source location, an exact quote/equation or unambiguous source target, and a concrete failure mode.
2. REJECT if the issue is vague, duplicative, merely stylistic, already handled elsewhere, or based on a misunderstanding.
3. NEEDS MANUAL CHECK if the issue depends on external literature, a theorem not present in the repo, a computation not rerun, or expert judgement beyond the available source.

For every ACCEPTED issue, state:
- final severity;
- mathematical or source-hygiene reason;
- minimal required fix;
- whether the theorem statement, proof, assumption, experiment, citation, or wording must change;
- patch locality;
- patch priority.

For every REJECTED issue, state why the objection is invalid or over-cautious.

For every NEEDS MANUAL CHECK issue, state the exact check needed.

Create:
- Paper_Audit/reports/adjudication_report.md
- Paper_Audit/08_issue_ledger.adjudicated.md

If a papercheck MCP server is available, submit this data via the corresponding MCP tool (e.g. submit_issue, adjudicate_issue, save_inventory_record); the Markdown file is a fallback view.

Do not patch.
