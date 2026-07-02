"""Checks on the vendored prompt / template / domain-pack content.

These assert the pack is present and complete, that the generic domain pack is
well-formed, and (belt-and-suspenders, beyond ``scripts/privacy_check.py``) that
no forbidden paper-specific identifiers leaked into the vendored content.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = REPO_ROOT / "prompts"
TEMPLATES_DIR = REPO_ROOT / "templates"
DOCS_DIR = REPO_ROOT / "docs"
DOMAIN_PACKS_DIR = REPO_ROOT / "domain_packs"

EXPECTED_PROMPTS = [f"{i:02d}" for i in range(21)]  # 00 .. 20

EXPECTED_TEMPLATES = {
    "assumption_record.md",
    "equation_record.md",
    "final_gate.md",
    "issue.md",
    "patch_record.md",
    "report_header.md",
    "segment_record.md",
    "theorem_record.md",
}

# Built from fragments so the literal forbidden tokens never appear in this
# source file (otherwise scripts/privacy_check.py would flag this very test).
_FORBIDDEN = re.compile("|".join(["fbsde" + "j", "mc" + "kean"]), re.IGNORECASE)


def test_prompts_pack_has_21_files() -> None:
    md_files = sorted(p.name for p in PROMPTS_DIR.glob("*.md"))
    assert len(md_files) == 21, f"expected 21 prompts, found {len(md_files)}: {md_files}"
    # Every 00..20 numeric prefix is present.
    prefixes = sorted(name[:2] for name in md_files)
    assert prefixes == EXPECTED_PROMPTS


def test_templates_pack_has_8_files() -> None:
    md_files = {p.name for p in TEMPLATES_DIR.glob("*.md")}
    assert md_files == EXPECTED_TEMPLATES, (
        f"template set mismatch: {sorted(md_files)}"
    )


def test_stochastic_analysis_pack_exists_and_parses() -> None:
    pack = DOMAIN_PACKS_DIR / "stochastic_analysis.yaml"
    assert pack.is_file(), "domain_packs/stochastic_analysis.yaml is missing"
    text = pack.read_text(encoding="utf-8")

    try:
        import yaml  # type: ignore
    except ImportError:
        # PyYAML not installed: fall back to a plain-text structural check.
        assert "high_risk_topics" in text
        assert "domain:" in text
        return

    data = yaml.safe_load(text)
    assert isinstance(data, dict)
    assert data.get("domain")
    assert isinstance(data.get("high_risk_topics"), list) and data["high_risk_topics"]
    assert isinstance(data.get("claim_triggers"), list) and data["claim_triggers"]
    assert isinstance(data.get("auditors"), list) and data["auditors"]


def test_no_forbidden_identifiers_in_vendored_content() -> None:
    offenders: list[str] = []
    for base in (PROMPTS_DIR, DOCS_DIR, DOMAIN_PACKS_DIR):
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if _FORBIDDEN.search(text):
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, f"forbidden identifiers found in: {offenders}"
