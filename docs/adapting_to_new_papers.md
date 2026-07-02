# Adapting to New Papers

For each new paper:

1. Copy `audit.config.example.yaml` to the paper repo as `audit.config.yaml`.
2. Fill in title, main tex if known, bibliography if known, and domain.
3. Select or write a domain pack for the field. See `domain_packs/stochastic_analysis.yaml`
   for a worked example of the pack format, and `domain_packs/README.md` for the schema.
   Add high-risk topics under `paper_specific` (or in the domain pack).
4. Add known sensitive claims.
5. Add external literature checks that need human/web verification.
6. Run bootstrap and scan scripts.
7. Start the agent with the master prompt.

Do not edit core prompts for one paper unless the improvement is genuinely reusable. Use overlays for paper-specific danger zones.
