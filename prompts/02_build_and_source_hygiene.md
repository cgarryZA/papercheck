You are doing mechanical build and source hygiene for a LaTeX mathematics paper.

Do not change the paper.

Run or inspect the configured build command if possible. Then inspect logs and source for:
- build failure;
- undefined references;
- undefined citations;
- duplicated labels;
- unresolved draft markers;
- suspicious overclaiming words;
- commented-out private or embarrassing text;
- missing bibliography data;
- obvious arXiv source risks.

Suspicious claim words are triggers, not automatic issues. Only mark them as issues if the surrounding claim is actually risky.

Write:
- Paper_Audit/02_build_status.md
- Paper_Audit/reports/build_and_source_hygiene.md

If a papercheck MCP server is available, submit this data via the corresponding MCP tool (e.g. submit_issue, adjudicate_issue, save_inventory_record); the Markdown file is a fallback view.
