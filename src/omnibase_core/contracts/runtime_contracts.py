# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Accessor for runtime contract YAML files.

Runtime contracts define the ONEX runtime's own configuration as a node graph.
They live at ``contracts/runtime/`` in the omnibase_core repository and are
the single source of truth for timeout, retry, circuit-breaker, and FSM
configuration.

Resolution order:
    1. ``ONEX_RUNTIME_CONTRACTS_DIR`` env var (development/deployment override)
    2. ``importlib.resources`` (works in PyPI installs)
    3. Package-relative path (works when pip-installed, e.g. Docker)
    4. Repository-relative path (works in dev and worktrees)
    5. ``importlib.resources`` package data from ``runtime_data`` subpackage
"""

from __future__ import annotations

import importlib.resources
import os
from pathlib import Path


def get_runtime_contracts_dir() -> Path:
    """Return the path to runtime contract YAML files.

    Resolution order:
        1. ``ONEX_RUNTIME_CONTRACTS_DIR`` env var (explicit override)
        2. ``importlib.resources`` (works in PyPI installs)
        3. Package-relative: ``<package>/contracts/runtime/``
        4. Repository-relative: ``<repo_root>/contracts/runtime/``
        5. Package data via ``importlib.resources`` from ``runtime_data``

    Returns:
        Path to the directory containing the 5 runtime contract YAMLs.

    Raises:
        FileNotFoundError: If no valid contracts directory can be found.
    """
    # 1. Explicit override
    env_override = os.environ.get("ONEX_RUNTIME_CONTRACTS_DIR")
    if env_override:
        p = Path(env_override)
        if p.is_dir():
            return p

    # 2. importlib.resources (works in PyPI installs)
    try:
        import importlib.resources as resources

        contracts_ref = resources.files("omnibase_core") / "contracts" / "runtime"
        contracts_path = Path(str(contracts_ref))
        if contracts_path.is_dir():
            return contracts_path
    except (ImportError, TypeError, FileNotFoundError):
        pass

    # 3. Package-relative path (contracts installed alongside this module)
    # this file: omnibase_core/contracts/runtime_contracts.py
    # contracts:  omnibase_core/contracts/runtime/
    pkg_dir = Path(__file__).parent / "runtime"
    if pkg_dir.is_dir():
        return pkg_dir

    # 4. Repository-relative path (4 levels up from this file to repo root)
    # this file: src/omnibase_core/contracts/runtime_contracts.py
    # repo root: ../../../../contracts/runtime/
    repo_root = Path(__file__).parent.parent.parent.parent
    repo_dir = repo_root / "contracts" / "runtime"
    if repo_dir.is_dir():
        return repo_dir

    # 4. Package data (PyPI install) — contracts are bundled inside the
    # package at omnibase_core/contracts/runtime_data/.
    try:
        ref = importlib.resources.files("omnibase_core.contracts.runtime_data")
        # importlib.resources.files() returns a Traversable.  For on-disk
        # packages this is already a Path; for zipped packages as_file()
        # would be needed, but we only support on-disk installs.
        pkg_data_dir = Path(str(ref))
        if pkg_data_dir.is_dir() and any(pkg_data_dir.glob("*.yaml")):
            return pkg_data_dir
    except (ModuleNotFoundError, TypeError):
        pass

    raise FileNotFoundError(  # error-ok: FileNotFoundError is correct for file lookup
        "Runtime contracts not found. Set ONEX_RUNTIME_CONTRACTS_DIR, "
        "ensure contracts/runtime/ exists in the omnibase_core repository, "
        "or install omnibase_core from PyPI (which bundles contracts)."
    )
