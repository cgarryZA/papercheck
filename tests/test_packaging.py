"""Guard the data-resource resolver used for both editable and wheel layouts."""

from __future__ import annotations

from papercheck.core._resources import resource_dir, resource_file


def test_resource_dirs_exist() -> None:
    for name in ("schemas", "prompts", "templates", "domain_packs"):
        assert resource_dir(name).is_dir()


def test_resource_file() -> None:
    assert resource_file("schemas", "issue.schema.json").is_file()
