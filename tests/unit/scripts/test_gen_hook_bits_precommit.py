# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pre-commit wiring test: hook-bits-drift must be registered in both repos."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve_omni_home() -> Path | None:
    env = os.environ.get("OMNI_HOME")
    if env:
        return Path(env)
    for candidate in (REPO_ROOT.parent.parent.parent, REPO_ROOT.parent):
        if (candidate / "omniclaude").is_dir():
            return candidate
    return None


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
    candidates = [REPO_ROOT.parent / "omniclaude" / ".pre-commit-config.yaml"]
    if omni_home := _resolve_omni_home():
        candidates.append(omni_home / "omniclaude" / ".pre-commit-config.yaml")

    existing = [p for p in candidates if p.exists()]
    if not existing:
        pytest.skip("omniclaude checkout not available")

    for p in existing:
        ids = _ids(p)
        if "hook-bits-drift" in ids:
            return
    raise AssertionError(
        "hook-bits-drift not found in any omniclaude .pre-commit-config.yaml"
    )
