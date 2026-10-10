# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The node-home ratchet is activated in this repository (OMN-20702)."""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.nodes.node_node_home_check_compute.handler import (
    NODE_HOME_BASELINE,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
RUNTIME_MODULE = (
    "omnibase_core.nodes.node_node_home_check_compute.runtime_node_home_check"
)


def test_baseline_lists_only_existing_node_directories() -> None:
    baseline = REPO_ROOT / NODE_HOME_BASELINE
    assert baseline.is_file()
    entries = [
        line
        for line in baseline.read_text().splitlines()
        if line and not line.startswith("#")
    ]
    assert entries
    assert entries == sorted(set(entries))
    missing = [entry for entry in entries if not (REPO_ROOT / entry).is_dir()]
    assert missing == []


def test_pre_commit_runs_the_check() -> None:
    config = (REPO_ROOT / ".pre-commit-config.yaml").read_text()
    assert "id: check-node-home" in config
    assert RUNTIME_MODULE in config


def test_ci_runs_the_check_against_the_merge_base() -> None:
    workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text()
    assert f"{RUNTIME_MODULE} --base" in workflow
