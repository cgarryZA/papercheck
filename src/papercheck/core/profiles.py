"""Advisory audit profiles.

A *profile* is an advisory, ordered list of stages/checks that a human or a
driving agent should run for a given use-case. papercheck does not
self-orchestrate; profiles simply describe a recommended sequence.

Profiles are shipped as ``profiles/profiles.json`` and resolved via the shared
data-resource resolver so they load identically in an editable checkout and an
installed wheel.
"""

from __future__ import annotations

import json

from papercheck.core._resources import resource_dir

_CACHE: dict | None = None


def _load() -> dict:
    """Load and cache the profiles mapping from ``profiles/profiles.json``.

    Raises :class:`FileNotFoundError` if the profiles directory is missing.
    """
    global _CACHE
    if _CACHE is None:
        path = resource_dir("profiles") / "profiles.json"
        _CACHE = json.loads(path.read_text(encoding="utf-8"))
    return _CACHE


def list_profiles() -> list[str]:
    """Return the sorted list of profile names."""
    return sorted(_load())


def get_profile(name: str) -> dict:
    """Return the profile dict for ``name``.

    Raises :class:`KeyError` if no such profile exists.
    """
    profiles = _load()
    if name not in profiles:
        raise KeyError(name)
    return profiles[name]


def profile_steps(name: str) -> list[str]:
    """Return the ordered list of steps for the named profile."""
    return get_profile(name)["steps"]
