"""Path and configuration constants for the :mod:`tier` package.

Datasets and configs live outside the importable package (in the repo root)
to keep the source distribution compact and to avoid packaging multi-hundred
megabyte JSON files.  This module resolves those paths at import time so the
rest of the code can reference them via a single helper.
"""

from __future__ import annotations

import os
from pathlib import Path


def _detect_repo_root() -> Path:
    """Locate the repository root.

    Order of resolution:
        1. ``TIER_REPO_ROOT`` environment variable (explicit override).
        2. Walk upwards from this file looking for a directory that contains
           both ``pyproject.toml`` and a ``data`` directory.  This works for
           editable installs (``pip install -e .``) where the package is
           still inside the cloned repo.
        3. Fall back to the current working directory.
    """
    override = os.environ.get("TIER_REPO_ROOT")
    if override:
        return Path(override).expanduser().resolve()

    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").exists() and (candidate / "data").is_dir():
            return candidate

    return Path.cwd().resolve()


REPO_ROOT: Path = _detect_repo_root()
DATA_DIR: Path = REPO_ROOT / "data"
CONFIGS_DIR: Path = REPO_ROOT / "configs"
OUTPUTS_DIR: Path = REPO_ROOT / "outputs"


def data_path(*parts: str) -> Path:
    """Return ``DATA_DIR / parts...`` as a :class:`pathlib.Path`."""
    return DATA_DIR.joinpath(*parts)


def outputs_path(*parts: str) -> Path:
    """Return ``OUTPUTS_DIR / parts...`` as a :class:`pathlib.Path`."""
    return OUTPUTS_DIR.joinpath(*parts)
