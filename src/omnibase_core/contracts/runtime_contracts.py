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
    3. Repository-relative path (works in dev and worktrees)
"""

from __future__ import annotations

import os
from pathlib import Path


def get_runtime_contracts_dir() -> Path:
    """Return the path to runtime contract YAML files.

    Resolution order:
        1. ``ONEX_RUNTIME_CONTRACTS_DIR`` env var (explicit override)
        2. ``importlib.resources`` (works in PyPI installs)
        3. Repository-relative: ``<repo_root>/contracts/runtime/``

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

    # 3. Repository-relative path (4 levels up from this file to repo root)
    # this file: src/omnibase_core/contracts/runtime_contracts.py
    # repo root: ../../../../contracts/runtime/
    repo_root = Path(__file__).parent.parent.parent.parent
    pkg_dir = repo_root / "contracts" / "runtime"
    if pkg_dir.is_dir():
        return pkg_dir

    raise FileNotFoundError(  # error-ok: FileNotFoundError is correct for file lookup
        "Runtime contracts not found. Set ONEX_RUNTIME_CONTRACTS_DIR or "
        "ensure contracts/runtime/ is packaged in the wheel."
    )
