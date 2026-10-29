# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The node-home ratchet is activated in this repository (OMN-20702)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.nodes.node_canonical_file_shape_check_compute.matcher_node_home import (
    NODE_HOME_BASELINE,
)

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[4]
RUNTIME_MODULE = (
    "omnibase_core.nodes.node_canonical_file_shape_check_compute."
    "runtime_canonical_file_shape_check"
)

RUNTIME_COMMAND = f"{RUNTIME_MODULE} --rules node-home"


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
    hooks = [
        hook
        for repo in yaml.safe_load(config)["repos"]
        for hook in repo.get("hooks", [])
        if hook["id"] == "check-node-home"
    ]
    assert len(hooks) == 1
    assert hooks[0]["entry"] == f"uv run python -m {RUNTIME_COMMAND}"


def test_ci_runs_the_check_against_the_merge_base() -> None:
    workflow = (REPO_ROOT / ".github/workflows/ci.yml").read_text()
    assert f'{RUNTIME_COMMAND} --base "$base"' in workflow
    assert 'base="$(git merge-base "$base" HEAD)"' in workflow
