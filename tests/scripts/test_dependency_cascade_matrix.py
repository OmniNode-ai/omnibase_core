# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for .github/workflows/dependency-cascade.yml downstream matrix.

OMN-9425: the cascade workflow opens dependency-bump PRs in downstream repos
when a foundation package (omnibase_core / omnibase_spi / omnibase_infra) is
released. The downstream set is hardcoded in a shell ``case`` statement inside
the workflow and has silently drifted from the actual consumer list in the past
(ccc was missing even though onex_change_control depends on omnibase-core).

This test parses the workflow YAML, extracts the ``case`` block, and asserts
that each foundation package's downstream list contains every repo that
actually consumes it — guarding against future omissions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "dependency-cascade.yml"


def _extract_case_mapping() -> dict[str, list[str]]:
    """Parse the ``case "$PACKAGE" in ... esac`` block in the workflow.

    Returns a dict mapping each foundation package name to its list of
    downstream repos, exactly as the workflow will emit them at runtime.
    """
    content = WORKFLOW_PATH.read_text()
    case_re = re.compile(
        r"(?P<pkg>[a-z_]+)\)\s*\n\s*REPOS=\'(?P<repos>\[[^\]]*\])\'",
        re.MULTILINE,
    )
    mapping: dict[str, list[str]] = {}
    for match in case_re.finditer(content):
        pkg = match.group("pkg")
        repos = json.loads(match.group("repos"))
        mapping[pkg] = repos
    return mapping


@pytest.mark.unit
def test_workflow_yaml_parses() -> None:
    """The workflow file must be valid YAML."""
    with WORKFLOW_PATH.open() as fh:
        doc = yaml.safe_load(fh)
    assert doc["name"] == "Dependency Cascade"


@pytest.mark.unit
def test_omnibase_core_cascades_to_onex_change_control() -> None:
    """OMN-9425: ccc's uv.lock must be auto-bumped on omnibase_core release.

    onex_change_control depends on omnibase-core (see ccc/pyproject.toml).
    Without this entry, ccc PRs block on stale lockfiles when new core
    modules ship, as happened with ccc#301 pre-OMN-9425.
    """
    mapping = _extract_case_mapping()
    assert "omnibase_core" in mapping, (
        "omnibase_core case missing from dependency-cascade.yml"
    )
    assert "onex_change_control" in mapping["omnibase_core"], (
        "onex_change_control must be in the omnibase_core downstream matrix; "
        "without it, ccc's uv.lock won't auto-bump on core releases "
        "(see OMN-9425 and the ccc#301 regression)."
    )


@pytest.mark.unit
def test_all_foundation_packages_have_downstream_lists() -> None:
    """Each foundation package in the docstring must have a case branch."""
    mapping = _extract_case_mapping()
    expected = {"omnibase_core", "omnibase_spi", "omnibase_infra"}
    assert expected.issubset(mapping.keys()), (
        f"Missing case branches for: {expected - mapping.keys()}"
    )


@pytest.mark.unit
def test_downstream_lists_are_non_empty_and_unique() -> None:
    """Sanity: every case emits at least one repo and no duplicates."""
    mapping = _extract_case_mapping()
    for pkg, repos in mapping.items():
        assert repos, f"{pkg}: downstream list is empty"
        assert len(repos) == len(set(repos)), (
            f"{pkg}: downstream list has duplicates: {repos}"
        )


@pytest.mark.unit
def test_omnibase_spi_and_infra_exclude_ccc() -> None:
    """ccc does not hard-depend on spi or infra; keep them out.

    Guard against over-eager additions. If ccc's pyproject.toml ever gains a
    spi or infra dependency, update the workflow case AND this test together.
    """
    mapping = _extract_case_mapping()
    assert "onex_change_control" not in mapping.get("omnibase_spi", []), (
        "ccc does not depend on omnibase-spi; see onex_change_control/pyproject.toml"
    )
    assert "onex_change_control" not in mapping.get("omnibase_infra", []), (
        "ccc does not depend on omnibase-infra; see onex_change_control/pyproject.toml"
    )
