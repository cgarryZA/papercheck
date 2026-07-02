# Domain Packs

A *domain pack* tells the domain-specialist auditor (prompt `08`) what to look
for in a particular mathematical field. It is deliberately small and generic:
it encodes reusable, textbook-level danger zones for a whole field, **not** the
specific danger zones of any one paper. Paper-specific hot spots belong in that
paper's `audit.config.yaml` (`paper_specific` block), never in a shared pack.

Each pack is a small YAML file living in this directory (`domain_packs/*.yaml`).

## Format

A pack is a YAML mapping with the following fields:

| Field              | Type            | Meaning |
|--------------------|-----------------|---------|
| `domain`           | string          | Human-readable name of the field the pack covers (e.g. `stochastic analysis`). |
| `high_risk_topics` | list of strings | Field-level topics where proofs commonly break. Each entry is a short phrase the auditor should treat as a red flag when it appears in a proof. |
| `claim_triggers`   | list of strings | Words whose presence signals an over-claim worth checking (e.g. `sharp`, `optimal`). These are *triggers*, not automatic issues. |
| `auditors`         | list of strings | Which auditor roles are most relevant for this domain (e.g. `formalist`, `domain_specialist`, `notation`, `related_work`). Used to prioritise passes. |

### Minimal example

```yaml
domain: example field
high_risk_topics:
  - some commonly-mishandled hypothesis
  - some easily-dropped boundary term
claim_triggers: [sharp, optimal, first]
auditors: [formalist, domain_specialist]
```

## Usage

The domain-specialist auditor reads the configured pack, then audits the paper
for field-specific correctness driven by `high_risk_topics` and
`claim_triggers`. `high_risk_topics` are cues, not a checklist to force onto the
paper — only raise an issue when the paper actually mishandles one of them.

## Adding a pack

1. Copy the minimal example above into `domain_packs/<field>.yaml`.
2. Fill `high_risk_topics` from *generic* graduate-textbook knowledge of the
   field — the mistakes any paper in the field can make. Do not transcribe the
   specific weaknesses of a paper you are currently auditing.
3. Keep `claim_triggers` short; over-long lists produce noise.
4. List the auditor roles worth emphasising in `auditors`.
