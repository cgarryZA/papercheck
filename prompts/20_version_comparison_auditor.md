You are comparing two versions of a mathematical paper after patches.

Your job is not to re-review the whole paper. Your job is to determine whether the diff fixed accepted issues and whether the diff introduced new problems.

Use:
- git diff or source comparison;
- Paper_Audit/08_issue_ledger.adjudicated.md;
- Paper_Audit/09_patch_plan.md;
- Paper_Audit/patches/records.

For each changed theorem, proof, assumption, experiment claim, or related-work claim, check downstream consistency.

Output:
- accepted issues fixed;
- accepted issues not fixed;
- new issues introduced by the diff;
- final recommendation.

If a papercheck MCP server is available, submit this data via the corresponding MCP tool (e.g. submit_issue, adjudicate_issue, save_inventory_record); the Markdown file is a fallback view.
