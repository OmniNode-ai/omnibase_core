# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pre-commit wiring test: hook-bits-drift must be registered in both repos."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve_omni_home() -> Path:
    env = os.environ.get("OMNI_HOME")
    if env:
        return Path(env)
    for candidate in (REPO_ROOT.parent.parent.parent, REPO_ROOT.parent):
        if (candidate / "omniclaude").is_dir():
            return candidate
    msg = f"Cannot resolve OMNI_HOME from REPO_ROOT={REPO_ROOT}"
    raise RuntimeError(msg)


OMNI_HOME = _resolve_omni_home()


def _ids(cfg_path: Path) -> set[str]:
    data = yaml.safe_load(cfg_path.read_text())
    ids: set[str] = set()
    for repo in data.get("repos", []):
        for hook in repo.get("hooks", []):
            ids.add(hook["id"])
    return ids


def test_hook_bits_drift_registered_in_omnibase_core() -> None:
    ids = _ids(REPO_ROOT / ".pre-commit-config.yaml")
    assert "hook-bits-drift" in ids


def test_hook_bits_drift_registered_in_omniclaude() -> None:
    ids = _ids(OMNI_HOME / "omniclaude" / ".pre-commit-config.yaml")
    assert "hook-bits-drift" in ids
