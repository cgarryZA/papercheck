You are inspecting a LaTeX mathematics paper repository for an adversarial audit harness.

Do not modify the manuscript.

Identify:
1. likely main .tex file;
2. all included .tex files;
3. macro/style/class files;
4. bibliography files;
5. generated PDFs;
6. figures and tables;
7. numerical experiment files;
8. build commands suggested by the repository;
9. files that should be excluded from audit output.

Write:
- Paper_Audit/00_manifest.md
- Paper_Audit/01_repository_inventory.md
- Paper_Audit/reports/repository_inspection.md

If a papercheck MCP server is available, submit this data via the corresponding MCP tool (e.g. submit_issue, adjudicate_issue, save_inventory_record); the Markdown file is a fallback view.

If the main file is ambiguous, rank candidates and explain why. Do not ask the user unless the repo truly cannot be inspected.
