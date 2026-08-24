# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Repo-root pytest configuration.

A conftest.py at the repo root (next to pyproject.toml) is loaded by pytest
for EVERY invocation in this rootdir -- unlike tests/conftest.py, which only
loads for collections that descend into tests/. That property is exactly what
OMN-15977 Hole 1 needs: the .200-default host guard must fire for a bare
`uv run pytest tests/` (or any other direct full-suite invocation) the same
way it fires for the git-push path (scripts/hooks/prepush_smart_tests.sh).
"""

from __future__ import annotations

# pyproject.toml's `pythonpath = ["src", "."]` puts the repo root on
# sys.path for every pytest run, which is what makes this dotted import
# resolve the same way scripts/ci/detect_test_paths.py already does via
# `python -m scripts.ci.detect_test_paths` in prepush_smart_tests.sh.
from scripts.hooks.pytest_full_suite_host_guard import enforce

# Single source of truth for "what the heavy run is" here: matches
# FULL_SUITE_TARGET in scripts/hooks/prepush_smart_tests.sh exactly (core's
# fail-closed escalation runs the whole tests/ tree, unlike infra's
# tests/unit/-scoped escalation -- see that script's OMN-15408 SEAM comment).
_FULL_SUITE_TARGET = "tests"


def pytest_configure(config: object) -> None:
    enforce(config, _FULL_SUITE_TARGET)
