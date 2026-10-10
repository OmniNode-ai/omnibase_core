# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Centralized ONEX state directory path resolver.

All ONEX runtime artifacts (logs, pipeline state, session state, handoff
files, worktree metadata) live under a single root configured via the
``ONEX_STATE_DIR`` environment variable.
"""

from __future__ import annotations

import os
from pathlib import Path

_ENV_VAR = "ONEX_STATE_DIR"


def state_root() -> Path:
    """Return the ONEX state root directory.

    Reads ``ONEX_STATE_DIR`` from the environment, expands ``~``, and
    returns an absolute :class:`~pathlib.Path`.

    Raises:
        RuntimeError: If the variable is unset or blank.
    """
    raw = os.environ.get(_ENV_VAR, "")
    if not raw.strip():
        msg = (
            f"{_ENV_VAR} is not set or is blank. "
            "Set it in ~/.omnibase/.env or export it before running ONEX."
        )
        raise RuntimeError(msg)
    return Path(raw).expanduser().resolve()


def state_path(*parts: str) -> Path:
    """Join *parts* under :func:`state_root` without creating anything."""
    return state_root().joinpath(*parts)


def ensure_state_path(*parts: str) -> Path:
    """Join *parts* under :func:`state_root` and create the **parent** directory.

    Use this for files: the parent directory is created so the caller can
    immediately open the file for writing.
    """
    p = state_root().joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def ensure_state_dir(*parts: str) -> Path:
    """Join *parts* under :func:`state_root` and create the directory itself.

    Use this for directories that must exist before the caller writes into
    them.
    """
    p = state_root().joinpath(*parts)
    p.mkdir(parents=True, exist_ok=True)
    return p


def log_path(name: str) -> Path:
    """Shorthand for ``ensure_state_path("logs", name)``."""
    return ensure_state_path("logs", name)
