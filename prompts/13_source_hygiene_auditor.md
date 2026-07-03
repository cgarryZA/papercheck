You are doing final source hygiene for a LaTeX mathematics paper.

Search source files for:
- TODO;
- FIXME;
- TBD;
- XXX;
- placeholder;
- draft;
- LLM-generator names;
- ??;
- commented-out private or embarrassing text;
- duplicated labels;
- undefined references;
- undefined citations;
- missing bibliography fields;
- unused or stale generated files;
- wrong author metadata;
- wrong affiliation;
- acknowledgement placeholders;
- obvious arXiv source-bundle risks.

Distinguish blocking issues from harmless build artefacts.

Draft markers a line silences with an inline `% papercheck: ignore` (or `% papercheck: ignore draft-marker`) pragma are deliberate and unreachable (e.g. an `\IfFileExists` fallback that never renders when the file is present). The scanner records these under `suppressed_draft_markers`, not `draft_markers`; do not re-raise them as issues.

For each issue, use the required issue schema.

Write Paper_Audit/reports/source_hygiene_audit.md.

If a papercheck MCP server is available, submit this data via the corresponding MCP tool (e.g. submit_issue, adjudicate_issue, save_inventory_record); the Markdown file is a fallback view.
