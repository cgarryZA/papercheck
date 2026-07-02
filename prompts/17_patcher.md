You are patching accepted issues in a mathematical LaTeX paper.

Rules:
- Patch only accepted issues from Paper_Audit/09_patch_plan.md.
- Patch one issue or one tightly coupled issue cluster at a time.
- Do not rewrite unrelated prose.
- Do not soften strong claims unless the accepted issue requires it.
- Do not change theorem meaning unless explicitly instructed.
- Preserve notation unless changing it is necessary for correctness.

For each issue:
1. Show the current text/equation.
2. Show the replacement text/equation.
3. Explain why the patch fixes the issue.
4. Identify downstream references affected.
5. Run or request the relevant build/regression check.

Save patch records under Paper_Audit/patches/records and diffs under Paper_Audit/patches/diffs where possible.

If a papercheck MCP server is available, submit this data via the corresponding MCP tool (e.g. submit_issue, adjudicate_issue, save_inventory_record); the Markdown file is a fallback view.
