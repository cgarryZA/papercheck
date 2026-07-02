"""Domain-pack generation and loading.

A *domain pack* declares the danger zones a paper's auditors should watch for:
its ``high_risk_topics``, the rhetorical ``claim_triggers`` that flag
over-strong claims, and the ``auditors`` to run. Shipped packs are static YAML
files written from textbook knowledge of a field; *generated* packs are drafted
per-paper from its scanned structure and stored as JSON inside the paper's
audit dir (JSON keeps generation free of any PyYAML dependency).

This module provides the deterministic *mechanism*: :func:`scaffold_pack`
drafts candidate fields from a structure dict, :func:`create_pack` validates
and persists a finished pack, and :func:`list_packs` / :func:`load_pack` expose
both shipped and generated packs. The driving agent supplies the intelligence
(reading the paper, refining the scaffold); papercheck never calls an LLM.
"""

from __future__ import annotations

import json
from pathlib import Path

from papercheck.core import paths, schemas
from papercheck.core._resources import resource_dir

# Danger zones common to essentially any mathematical paper. Always included in
# a scaffold so the required ``high_risk_topics`` list is never empty.
_GENERIC_TOPICS: list[str] = [
    "objects used before definition",
    "hidden regularity/measurability/integrability assumptions",
    "constant dependence on parameters",
    "unjustified exchange of limits/sums/integrals",
]

# Fallback claim-trigger words when the paper's structure surfaced none.
_DEFAULT_TRIGGERS: list[str] = ["sharp", "optimal", "novel", "first", "exact"]

# The standard auditor roster for a generated pack.
_DEFAULT_AUDITORS: list[str] = [
    "formalist",
    "domain_specialist",
    "notation",
    "related_work",
]


def GENERATED_PATH(paper_root: Path) -> Path:
    """Return the path to the paper's generated domain pack (JSON)."""
    return paths.audit_dir(paper_root) / "domain_pack.json"


def scaffold_pack(structure: dict) -> dict:
    """Draft a candidate domain pack from a scanned structure dict.

    Deterministic: the same structure always yields the same scaffold. The
    result is schema-valid (required lists are guaranteed non-empty) so the
    driving agent can persist it verbatim or refine it first.
    """
    theorem_kinds = sorted(
        {
            env.get("kind", "")
            for env in structure.get("theorem_envs", [])
            if env.get("kind")
        }
    )
    high_risk_topics = [
        f"correctness of each {kind}" for kind in theorem_kinds
    ] + list(_GENERIC_TOPICS)

    triggers = sorted(
        {
            w.get("word", "")
            for w in structure.get("claim_triggers", [])
            if w.get("word")
        }
    )
    claim_triggers = triggers if triggers else list(_DEFAULT_TRIGGERS)

    pack = {
        "domain": "unknown — edit after reading the paper",
        "high_risk_topics": high_risk_topics,
        "claim_triggers": claim_triggers,
        "auditors": list(_DEFAULT_AUDITORS),
        "notes": (
            "Scaffold generated from paper structure. Review and refine each "
            "field before auditing."
        ),
        "generated_from": structure.get("paper_root", ""),
    }
    schemas.validate(pack, "domain_pack")
    return pack


def create_pack(paper_root: Path, pack: dict) -> Path:
    """Validate ``pack`` and persist it as the paper's generated domain pack.

    Raises ``jsonschema.ValidationError`` if the pack is invalid. Returns the
    path written.
    """
    schemas.validate(pack, "domain_pack")
    out_path = GENERATED_PATH(paper_root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(pack, indent=2) + "\n", encoding="utf-8")
    return out_path


def list_packs(paper_root: Path | None = None) -> list[str]:
    """List available domain-pack names.

    Shipped packs are the sorted stems of ``*.yaml`` files in the bundled
    ``domain_packs`` directory (the README is skipped). If ``paper_root`` is
    given and a generated pack exists for it, ``"generated"`` is appended.
    """
    packs_dir = resource_dir("domain_packs")
    names = sorted(
        p.stem for p in packs_dir.glob("*.yaml") if p.stem.lower() != "readme"
    )
    if paper_root is not None and GENERATED_PATH(paper_root).is_file():
        names.append("generated")
    return names


def load_pack(name: str, paper_root: Path | None = None) -> dict:
    """Load a domain pack by name.

    ``"generated"`` (or any name when a generated pack exists for
    ``paper_root``) loads the paper's JSON pack. Otherwise the shipped YAML
    pack ``<name>.yaml`` is parsed. Raises ``KeyError(name)`` if no such pack
    exists, and ``RuntimeError`` if a YAML pack is requested but PyYAML is not
    installed.
    """
    if paper_root is not None:
        generated = GENERATED_PATH(paper_root)
        if generated.is_file() and (name == "generated" or generated.stem == name):
            return json.loads(generated.read_text(encoding="utf-8"))
    if name == "generated":
        raise KeyError(name)

    path = resource_dir("domain_packs") / f"{name}.yaml"
    if not path.is_file():
        raise KeyError(name)
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - depends on env
        raise RuntimeError(
            "PyYAML required to load YAML domain packs; generated packs are "
            "JSON and always loadable"
        ) from exc
    return yaml.safe_load(path.read_text(encoding="utf-8"))
