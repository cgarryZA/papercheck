"""Tests for domain pack YAML files.

Asserts that each domain pack file exists, is valid YAML, and contains all required
fields with non-empty lists. Also checks that no forbidden identifiers appear in
any pack file.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOMAIN_PACKS_DIR = REPO_ROOT / "domain_packs"

EXPECTED_PACKS = {
    "stochastic_analysis",
    "numerical_analysis",
    "pde",
    "optimization",
    "machine_learning",
    "general",
}

# Built from fragments so the literal forbidden tokens never appear in this
# source file (otherwise scripts/privacy_check.py would flag this very test).
_FORBIDDEN = re.compile("|".join(["fbsde" + "j", "mc" + "kean"]), re.IGNORECASE)


def _validate_pack_file(pack_path: Path) -> None:
    """Validate that a pack file is well-formed YAML with all required fields."""
    assert pack_path.is_file(), f"{pack_path.name} is missing"
    text = pack_path.read_text(encoding="utf-8")

    # Check for forbidden identifiers.
    assert not _FORBIDDEN.search(text), (
        f"forbidden identifiers found in {pack_path.name}"
    )

    try:
        import yaml  # type: ignore
    except ImportError:
        # PyYAML not installed: fall back to plain-text structural check.
        assert "domain:" in text, f"{pack_path.name} missing 'domain:' field"
        assert "high_risk_topics:" in text, (
            f"{pack_path.name} missing 'high_risk_topics:' field"
        )
        assert "claim_triggers:" in text, (
            f"{pack_path.name} missing 'claim_triggers:' field"
        )
        assert "auditors:" in text, f"{pack_path.name} missing 'auditors:' field"
        return

    # Full YAML validation.
    data = yaml.safe_load(text)
    assert isinstance(data, dict), f"{pack_path.name} did not parse to a dict"

    # Check all required fields.
    assert "domain" in data and data["domain"], (
        f"{pack_path.name} missing or empty 'domain' field"
    )
    assert isinstance(data.get("domain"), str), (
        f"{pack_path.name} 'domain' is not a string"
    )

    assert "high_risk_topics" in data, (
        f"{pack_path.name} missing 'high_risk_topics' field"
    )
    assert isinstance(data["high_risk_topics"], list), (
        f"{pack_path.name} 'high_risk_topics' is not a list"
    )
    assert data["high_risk_topics"], (
        f"{pack_path.name} 'high_risk_topics' is empty"
    )

    assert "claim_triggers" in data, (
        f"{pack_path.name} missing 'claim_triggers' field"
    )
    assert isinstance(data["claim_triggers"], list), (
        f"{pack_path.name} 'claim_triggers' is not a list"
    )
    assert data["claim_triggers"], f"{pack_path.name} 'claim_triggers' is empty"

    assert "auditors" in data, f"{pack_path.name} missing 'auditors' field"
    assert isinstance(data["auditors"], list), (
        f"{pack_path.name} 'auditors' is not a list"
    )
    assert data["auditors"], f"{pack_path.name} 'auditors' is empty"


def test_stochastic_analysis_pack() -> None:
    """Test stochastic_analysis.yaml is present and valid."""
    pack = DOMAIN_PACKS_DIR / "stochastic_analysis.yaml"
    _validate_pack_file(pack)


def test_numerical_analysis_pack() -> None:
    """Test numerical_analysis.yaml is present and valid."""
    pack = DOMAIN_PACKS_DIR / "numerical_analysis.yaml"
    _validate_pack_file(pack)


def test_pde_pack() -> None:
    """Test pde.yaml is present and valid."""
    pack = DOMAIN_PACKS_DIR / "pde.yaml"
    _validate_pack_file(pack)


def test_optimization_pack() -> None:
    """Test optimization.yaml is present and valid."""
    pack = DOMAIN_PACKS_DIR / "optimization.yaml"
    _validate_pack_file(pack)


def test_machine_learning_pack() -> None:
    """Test machine_learning.yaml is present and valid."""
    pack = DOMAIN_PACKS_DIR / "machine_learning.yaml"
    _validate_pack_file(pack)


def test_general_pack() -> None:
    """Test general.yaml is present and valid."""
    pack = DOMAIN_PACKS_DIR / "general.yaml"
    _validate_pack_file(pack)


def test_all_expected_packs_present() -> None:
    """Verify that all expected domain packs are present."""
    yaml_files = {p.stem for p in DOMAIN_PACKS_DIR.glob("*.yaml")}
    assert yaml_files == EXPECTED_PACKS, (
        f"pack mismatch: found {sorted(yaml_files)}, expected {sorted(EXPECTED_PACKS)}"
    )
