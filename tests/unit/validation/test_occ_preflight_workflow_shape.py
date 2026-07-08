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


def test_install_step_builds_wheel_from_source() -> None:
    script = _install_step_script()
    assert "uv build --wheel" in script
    assert '"$core_wheel"' in script


def test_install_step_uses_no_index_for_core_wheel() -> None:
    script = _install_step_script()
    joined = re.sub(r"\\\n\s*", " ", script)
    pattern = re.compile(r"uv pip install\b[^\n]*--no-index[^\n]*\"\$core_wheel\"")
    assert pattern.search(joined), (
        'the final `uv pip install ... "$core_wheel"` must include --no-index '
        "so uv cannot fall back to a stale published omnibase-core wheel"
    )


def test_install_step_disables_caller_config_for_core_wheel() -> None:
    script = _install_step_script()
    joined = re.sub(r"\\\n\s*", " ", script)
    pattern = re.compile(r"uv pip install\b[^\n]*--no-config[^\n]*\"\$core_wheel\"")
    assert pattern.search(joined), (
        "the final occ-preflight core install must ignore the caller repo config; "
        "downstream repos may pin an older omnibase-core version"
    )


def test_install_step_avoids_package_name_reinstall_for_core_wheel() -> None:
    script = _install_step_script()
    joined = re.sub(r"\\\n\s*", " ", script)
    install_lines = [
        line.strip()
        for line in joined.splitlines()
        if line.strip().startswith("uv pip install") and '"$core_wheel"' in line
    ]
    assert install_lines, "final omnibase_core wheel install command not found"
    for line in install_lines:
        assert "--reinstall-package omnibase-core" not in line, (
            "occ-preflight must install only the exact wheel path; naming "
            "omnibase-core as a reinstall target has pulled stale published "
            "distributions on self-hosted runners"
        )


def test_install_step_bypasses_uv_cache_for_core_wheel() -> None:
    script = _install_step_script()
    joined = re.sub(r"\\\n\s*", " ", script)
    pattern = re.compile(r"uv pip install\b[^\n]*--no-cache[^\n]*\"\$core_wheel\"")
    assert pattern.search(joined), (
        "the final occ-preflight core install must bypass uv cache so runner "
        "state cannot substitute a stale published omnibase-core wheel"
    )


def test_install_step_proves_installed_distribution() -> None:
    script = _install_step_script()
    assert 'metadata.version("omnibase-core")' in script
    assert "omnibase_core import path:" in script


def test_install_step_has_no_bare_pypi_core_install() -> None:
    script = _install_step_script()
    joined = re.sub(r"\\\n\s*", " ", script)
    for line in joined.splitlines():
        stripped = line.strip()
        if not stripped.startswith("uv pip install"):
            continue
        if "omnibase-core" not in stripped:
            continue
        if "--no-index" in stripped:
            continue
        pytest.fail(
            f"bare `uv pip install omnibase-core` without --no-index found: {stripped!r}"
        )


def test_install_step_seeds_transitive_deps_before_no_index() -> None:
    script = _install_step_script()
    assert "pydantic>=" in script
    assert "pyyaml>=" in script
