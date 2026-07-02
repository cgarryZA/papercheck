"""Tests for domain-pack generation (scaffold / create / list / load)."""

from __future__ import annotations

import pytest
from jsonschema import ValidationError

from papercheck.core import domainpack, schemas
from papercheck.mcp_server import handlers
from papercheck.mcp_server.server import build_server


def test_scaffold_from_structure_is_valid():
    structure = {
        "theorem_envs": [{"kind": "theorem"}, {"kind": "lemma"}],
        "claim_triggers": [{"word": "sharp"}, {"word": "optimal"}],
        "paper_root": "/x",
    }
    pack = domainpack.scaffold_pack(structure)
    schemas.validate(pack, "domain_pack")  # must not raise
    assert pack["high_risk_topics"]
    assert "sharp" in pack["claim_triggers"]
    assert "optimal" in pack["claim_triggers"]
    assert pack["generated_from"] == "/x"


def test_scaffold_empty_structure_uses_defaults():
    pack = domainpack.scaffold_pack({})
    schemas.validate(pack, "domain_pack")  # defaults keep it valid
    assert pack["high_risk_topics"]
    assert pack["claim_triggers"]  # default trigger set kicks in
    assert pack["auditors"]


def test_create_and_roundtrip(tmp_path):
    pack = domainpack.scaffold_pack({})
    path = domainpack.create_pack(tmp_path, pack)
    assert path == domainpack.GENERATED_PATH(tmp_path)
    assert path.is_file()

    assert "generated" in domainpack.list_packs(tmp_path)
    loaded = domainpack.load_pack("generated", tmp_path)
    assert loaded == pack


def test_validate_rejects_missing_domain():
    bad = {
        "high_risk_topics": ["x"],
        "claim_triggers": [],
        "auditors": ["formalist"],
    }
    with pytest.raises(ValidationError):
        schemas.validate(bad, "domain_pack")


def test_handlers_scaffold_and_create(tmp_path):
    scaffolded = handlers.scaffold_domain_pack(str(tmp_path))
    assert isinstance(scaffolded, dict)

    out = handlers.create_domain_pack(str(tmp_path), scaffolded)
    assert isinstance(out, str)
    from pathlib import Path

    assert Path(out).exists()

    names = handlers.list_domain_packs(str(tmp_path))
    assert isinstance(names, list)
    shipped = {"general", "stochastic_analysis"}
    assert shipped & set(names)


def test_build_server_registers_new_tools():
    build_server()  # must succeed
    for name in (
        "list_domain_packs",
        "get_domain_pack",
        "scaffold_domain_pack",
        "create_domain_pack",
    ):
        assert hasattr(handlers, name)
