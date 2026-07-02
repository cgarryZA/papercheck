"""Tests for advisory audit profiles."""

from __future__ import annotations

import pytest

from papercheck.core._resources import resource_dir
from papercheck.core.profiles import get_profile, list_profiles


def test_list_profiles_contains_expected() -> None:
    names = list_profiles()
    assert isinstance(names, list)
    for expected in ("quick", "arxiv", "full", "journal", "no-cloud"):
        assert expected in names


def test_quick_profile() -> None:
    quick = get_profile("quick")
    assert quick["steps"] == ["scan", "segments", "gate"]
    assert quick["mechanical_only"] is True


def test_no_cloud_is_mechanical_only() -> None:
    assert get_profile("no-cloud")["mechanical_only"] is True


def test_missing_profile_raises_keyerror() -> None:
    with pytest.raises(KeyError):
        get_profile("nonexistent")


def test_resource_dir_has_profiles_json() -> None:
    profiles_dir = resource_dir("profiles")
    assert profiles_dir.is_dir()
    assert (profiles_dir / "profiles.json").is_file()
