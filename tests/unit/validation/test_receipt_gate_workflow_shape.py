# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Structural tests for .github/workflows/receipt-gate.yml install logic.

Guards against regressions in the OMN-9198 / OMN-9283 remediation:
- The workflow must never fall back to PyPI for `omnibase-core` (the published
  wheel has a broken transitive `git+https` dep on `omnibase-compat`).
- The workflow must use the build-a-wheel + `--find-links` pattern so the same
  install command works for both self-project (core_path=".") and downstream
  callers (core_path="./.receipt-gate-deps/omnibase_core"). Editable/`-e` +
  `--no-index` fails on subpath callers because uv auto-discovers the cwd's
  pyproject constraint separately from the -e candidate registration.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "receipt-gate.yml"
)


def _install_step_script() -> str:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    steps = data["jobs"]["verify"]["steps"]
    for step in steps:
        if step.get("name") == "Install omnibase_core":
            script: str = step["run"]
            return script
    raise AssertionError("Install omnibase_core step not found in receipt-gate.yml")


def test_install_step_builds_wheel_from_source() -> None:
    """Core install must build a wheel, not install from PyPI."""
    script = _install_step_script()
    assert "uv build --wheel" in script, (
        "receipt-gate must build omnibase-core from source via `uv build --wheel` "
        "(OMN-9283 — editable -e <subpath> is not matched against caller-pyproject "
        "constraint under --no-index)"
    )


def test_install_step_uses_find_links() -> None:
    """Install must resolve omnibase-core from the local wheel dir."""
    script = _install_step_script()
    assert "--find-links" in script, (
        "receipt-gate install must use --find-links pointing at the locally-built "
        "wheel directory so uv's resolver has a source that satisfies the caller's "
        "`omnibase-core>=X` constraint without hitting PyPI"
    )


def test_install_step_uses_no_index_for_core() -> None:
    """Final core install must disable the PyPI index — the whole point of OMN-9198."""
    script = _install_step_script()
    # Join shell line-continuations before matching (the install command is
    # wrapped across multiple lines with trailing backslashes).
    joined = re.sub(r"\\\n\s*", " ", script)
    pattern = re.compile(r"uv pip install\b[^\n]*--no-index[^\n]*omnibase-core")
    assert pattern.search(joined), (
        "the final `uv pip install ... omnibase-core` must include --no-index "
        "so uv cannot fall back to the broken PyPI wheel"
    )


def test_install_step_has_no_bare_pypi_core_install() -> None:
    """Regression guard: no `uv pip install` of bare `omnibase-core` without --no-index."""
    script = _install_step_script()
    # Join shell line-continuations so multi-line `uv pip install ... \\\n  flag` reads as one logical command.
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
            f"bare `uv pip install omnibase-core` without --no-index found: {stripped!r}. "
            f"This would pull the broken PyPI wheel (OMN-9198)."
        )


def test_install_step_seeds_transitive_deps_from_pypi() -> None:
    """Transitive deps (pydantic, etc.) must still be resolvable — seeded before --no-index step."""
    script = _install_step_script()
    assert "pydantic>=" in script, (
        "transitive deps must be pre-seeded from PyPI before the --no-index core install; "
        "otherwise --no-deps + --no-index leaves runtime imports broken"
    )


def test_install_step_locates_core_path_for_both_self_and_subpath() -> None:
    """Core-path detection must handle self-project, sibling checkout, and receipt-gate-deps subpath."""
    script = _install_step_script()
    assert 'core_path="."' in script, "must detect self-project case"
    assert 'core_path="./.receipt-gate-deps/omnibase_core"' in script, (
        "must detect downstream-caller subpath case (was broken in #864)"
    )


def test_workflow_checks_out_omnibase_core_when_missing() -> None:
    """The subpath case requires a `Check out omnibase_core` step for downstream callers."""
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    steps = data["jobs"]["verify"]["steps"]
    names = [s.get("name", "") for s in steps]
    assert any("Check out omnibase_core" in n for n in names), (
        "receipt-gate must check out omnibase_core source for downstream callers "
        "that don't already have it in-tree"
    )
