"""Locate bundled data directories in both installed and source layouts.

The four data directories (``schemas``, ``prompts``, ``templates``,
``domain_packs``) live at the repo root during development but are copied
*inside* the package (via hatchling ``force-include``) when a wheel is built.
This module resolves either layout so runtime code works identically whether
``papercheck`` is an editable checkout or an installed wheel.
"""

from __future__ import annotations

from pathlib import Path


def resource_dir(name: str) -> Path:
    """Return the directory for a bundled data resource.

    Tries, in order:

    (a) package-relative — ``site-packages/papercheck/<name>`` in an installed
        wheel (``.parent.parent`` of this file is ``papercheck/``);
    (b) repo-root fallback — ``<repo>/<name>`` in an editable/source layout
        (``parents[3]`` of this file is the repo root).

    Raises :class:`FileNotFoundError` if neither exists.
    """
    packaged = Path(__file__).resolve().parent.parent / name
    if packaged.is_dir():
        return packaged
    repo_root = Path(__file__).resolve().parents[3] / name
    if repo_root.is_dir():
        return repo_root
    raise FileNotFoundError(name)


def resource_file(name: str, filename: str) -> Path:
    """Return the path to ``filename`` inside the named resource directory."""
    return resource_dir(name) / filename
