# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Structural tests for .github/workflows/occ-preflight.yml install logic."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "occ-preflight.yml"
)


def _install_step_script() -> str:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    steps = data["jobs"]["eligibility"]["steps"]
    for step in steps:
        if step.get("name") == "Install omnibase_core":
            script: str = step["run"]
            return script
    raise AssertionError("Install omnibase_core step not found in occ-preflight.yml")


def test_install_step_uses_per_run_wheel_directory() -> None:
    """The built wheel must not be selected from a stale shared /tmp directory."""
    script = _install_step_script()

    assert 'wheel_dir="$(mktemp -d ' in script
    assert 'uv build --wheel --out-dir "$wheel_dir"' in script
    assert 'find "$wheel_dir"' in script
    assert "mkdir -p /tmp/occ-preflight-wheels" not in script
    assert "find /tmp/occ-preflight-wheels" not in script


def test_install_step_installs_exact_local_core_wheel() -> None:
    """Final core install must use the freshly built wheel path only."""
    script = _install_step_script()
    joined = re.sub(r"\\\n\s*", " ", script)
    pattern = re.compile(
        r"uv pip install\b[^\n]*--no-config[^\n]*--no-index[^\n]*\"\$core_wheel\""
    )

    assert pattern.search(joined), (
        "occ-preflight must install the exact freshly built omnibase_core wheel "
        "without resolving omnibase-core from PyPI or caller uv config"
    )
