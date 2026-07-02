# GitHub CI Integration for papercheck

## Overview

The GitHub Actions integration for papercheck provides automated **mechanical safety checks** for LaTeX papers in CI/CD pipelines. This is a lightweight, cost-free check that runs on every pull request or manual trigger, catching common structural issues before they reach deeper review.

## What the CI Integration Does

The mechanical audit runs three commands in sequence:

1. **`papercheck scan`** — Validates LaTeX structure, checks for missing files, and identifies encoding issues
2. **`papercheck segments`** — Verifies logical structure and proper labeling of paper sections
3. **`papercheck gate --mechanical-only`** — Issues a verdict based on the above checks:
   - **READY**: Paper passes all mechanical checks
   - **READY AFTER MECHANICAL FIXES**: Minor issues found, but fixable
   - **NEEDS REVIEW**: Issues that require human or deep-audit attention

The exit code from the gate step determines CI success (0) or failure (1).

## What the CI Integration Does NOT Do

- **No LLM audits**: The mechanical checks use only rule-based analysis, no language models
- **No network calls to model providers**: No data is sent to OpenAI, Anthropic, or other AI services
- **No manuscript transmission**: Your paper never leaves your repository or the GitHub runner
- **No deep verification**: The integration does not check mathematical correctness, claim validity, or experimental rigor (those require the full agent-based audit)

## Adding CI to Your Paper Repository

### Step 1: Copy the Example Workflow

Copy `.github/workflows/example-paper-audit.yml` from the papercheck repo into your paper repository:

```bash
mkdir -p .github/workflows
cp example-paper-audit.yml .github/workflows/audit.yml
```

### Step 2: Adjust the Paper Root (if needed)

By default, the workflow assumes your paper sources are at the repository root (`.`). If your paper is in a subdirectory, update the `paper-root` input in the workflow:

```yaml
- name: Run papercheck mechanical audit
  uses: OWNER/papercheck@v0.2.0
  with:
    paper-root: "paper/"  # or wherever your LaTeX files are
```

### Step 3: Push and Verify

Commit the workflow file and push to GitHub. On your next pull request, the mechanical audit will run automatically.

## Understanding Gate Exit Codes

The `papercheck gate` command exits with:

- **0 (success)**: Paper is READY or READY AFTER MECHANICAL FIXES
- **1 (failure)**: Paper needs review before merging

By default, a non-zero exit code fails the CI job, blocking the PR merge. You can override this behavior with the `fail-on-gate` input:

```yaml
- name: Run papercheck mechanical audit
  uses: OWNER/papercheck@v0.2.0
  with:
    paper-root: "."
    fail-on-gate: "false"  # Don't block merge, just report verdict
```

## Deep Audits (Full Review)

The mechanical CI check is a safety net, not a complete audit. For thorough adversarial verification of mathematical claims, experimental correctness, and methodology, use the **papercheck agent** or **MCP server** to run a deep audit:

```bash
# Via CLI (requires ANTHROPIC_API_KEY)
python -m papercheck.agent.deep_audit --paper-root . --output-dir ./audit

# Via MCP (in a long-lived agent session)
# The agent calls papercheck over MCP and produces a comprehensive report
```

Deep audits are run separately by humans or automated agents, not in CI, because they require LLM access and can incur API costs.

## Configuration Options

The papercheck GitHub Action accepts:

| Input | Default | Description |
|-------|---------|-------------|
| `paper-root` | `.` | Path to paper root (change to `paper/` if sources are in a subdirectory) |
| `python-version` | `3.12` | Python version for the runner |
| `fail-on-gate` | `true` | If `true`, non-zero gate exit fails the job; if `false`, always report but don't block |

Example with custom settings:

```yaml
- name: Run papercheck mechanical audit
  uses: OWNER/papercheck@v0.2.0
  with:
    paper-root: "content/"
    python-version: "3.11"
    fail-on-gate: "false"
```

## Troubleshooting

### "pip install papercheck" fails

If you see an error installing papercheck, it may not yet be published to PyPI. Use the git install form instead:

In `action.yml`, replace:
```bash
pip install papercheck
```

with:
```bash
pip install git+https://github.com/OWNER/papercheck
```

### Gate verdict doesn't match local runs

Ensure your local environment matches the runner's Python version (check the `python-version` input in the workflow).

### I want to allow warnings but fail on errors

The `fail-on-gate` input controls only the exit code behavior. For finer-grained verdict control, run the gate step separately and parse the output manually:

```yaml
- name: Check gate verdict
  id: gate
  run: papercheck gate "." --mechanical-only || true
  # (the "|| true" prevents step failure)
- name: Decide whether to fail
  run: |
    if grep -q "NEEDS REVIEW" ${{ steps.gate.outputs.verdict }}; then
      exit 1
    fi
```

## Next Steps

- **For authors**: Add the mechanical audit to your paper repo to catch issues early.
- **For reviewers**: Use `papercheck scan` and `papercheck segments` locally to preview what CI will check.
- **For deep audits**: Contact a papercheck agent or set up an MCP server session for full verification.
