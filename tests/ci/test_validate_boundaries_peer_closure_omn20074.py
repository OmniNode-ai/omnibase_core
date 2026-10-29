# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The action must clone every endpoint of its packaged boundary manifest."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.nodes.node_cross_repo_boundary_check_effect.handler_boundary_parity import (
    load_boundary_manifest,
    load_manifest_yaml,
)

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
ACTION = ROOT / ".github/actions/validate-boundaries/action.yml"


def _steps() -> list[dict[str, Any]]:
    return yaml.safe_load(ACTION.read_text(encoding="utf-8"))["runs"]["steps"]


def _resolve(repos: str, checks: str = "boundary-parity") -> list[str]:
    step = next(s for s in _steps() if s.get("id") == "required_repos")
    script = step["run"].partition("\n")[2].rsplit("\nPY", 1)[0]
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env={"INPUT_REPOS": repos, "INPUT_CHECKS": checks},
        text=True,
        capture_output=True,
        check=True,
    )
    assert result.stdout.startswith("repos=")
    return result.stdout.strip().removeprefix("repos=").split(",")


def test_omitted_producer_is_added_from_the_packaged_manifest() -> None:
    repos = _resolve("omniclaude,omnimarket")
    entries = load_boundary_manifest(load_manifest_yaml())
    assert len(entries) == 5
    assert "omniintelligence" in repos
    assert {r for b in entries for r in (b.producer_repo, b.consumer_repo)} <= set(
        repos
    )


def test_caller_extras_are_preserved_and_endpoints_are_deduplicated() -> None:
    repos = _resolve(" omnidash,omniclaude,omniclaude,omnimarket, ")
    assert repos[0] == "omnidash"
    assert "omniclaude" in repos
    assert "omnimarket" in repos
    assert len(repos) == len(set(repos))
    assert "" not in repos


def test_empty_input_still_resolves_all_boundary_endpoints() -> None:
    repos = _resolve("")
    assert set(repos) == {
        r
        for b in load_boundary_manifest(load_manifest_yaml())
        for r in (b.producer_repo, b.consumer_repo)
    }


def test_migration_only_does_not_add_boundary_endpoints() -> None:
    assert _resolve("omniclaude,omnibase_infra", "migration-conflicts") == [
        "omniclaude",
        "omnibase_infra",
    ]


def test_combined_checks_with_whitespace_resolve_boundary_endpoints() -> None:
    assert "omniintelligence" in _resolve(
        "omniclaude", "migration-conflicts, boundary-parity "
    )


def test_clone_step_consumes_resolved_repos_from_the_actions_own_checkout() -> None:
    steps = _steps()
    resolver = next(s for s in steps if s.get("id") == "required_repos")
    clone = next(s for s in steps if s.get("id") == "clone")
    assert steps.index(resolver) < steps.index(clone)
    assert resolver["env"] == {
        "CORE_ROOT": "${{ steps.core.outputs.root }}",
        "INPUT_REPOS": "${{ inputs.repos }}",
        "INPUT_CHECKS": "${{ inputs.checks }}",
    }
    assert (
        'uv run --project "${CORE_ROOT}" --frozen --no-dev --no-sync' in resolver["run"]
    )
    assert "${{ steps.required_repos.outputs.repos }}" in clone["run"]
    assert "${{ inputs.repos }}" not in clone["run"]
    assert 'DEGRADED="${DEGRADED}${repo},"' in clone["run"]
