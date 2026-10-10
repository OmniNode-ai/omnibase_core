# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-20074: the validate-boundaries composite action moved into omnibase_core.

A caller that repoints its ``uses:`` line to this action keeps its own job, so
its context name does not change; the inputs must be the moved action's
(``checks``, ``warn-only``, ``repos`` with the same defaults). The checks run
omnibase_core's handlers from the action's own checkout and never check out
or name the change-control repository.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
ACTION_PATH = REPO_ROOT / ".github" / "actions" / "validate-boundaries" / "action.yml"

_FORBIDDEN_REFERENCE = "onex_change_control"
_FULL_SHA_USES = re.compile(r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$")
# Defaults of the moved action, verbatim.
_INPUT_DEFAULTS = {
    "checks": "boundary-parity,migration-conflicts",
    "warn-only": "true",
    "repos": "omniclaude,omnidash,omniintelligence,omnibase_infra,omnibase_core,omnimemory,omnimarket",
}
_PARITY_CALL = (
    "python -m omnibase_core.handlers.handler_boundary_parity"
    " --repos-root /tmp/omni_repos;"
)
_MIGRATION_CALL = (
    "python -m omnibase_core.handlers.handler_migration_conflicts"
    " --repos-root /tmp/omni_repos --check-columns --warn-only;"
)


def _load() -> dict[str, Any]:
    data = yaml.safe_load(ACTION_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _steps() -> list[dict[str, Any]]:
    steps = _load()["runs"]["steps"]
    assert isinstance(steps, list)
    return steps


def _step(name: str) -> dict[str, Any]:
    matches = [s for s in _steps() if s.get("name") == name]
    assert len(matches) == 1, name
    return matches[0]


def test_is_a_composite_action_with_the_moved_inputs() -> None:
    data = _load()
    assert data["runs"]["using"] == "composite"
    inputs = data["inputs"]
    assert set(inputs) == set(_INPUT_DEFAULTS)
    for name, default in _INPUT_DEFAULTS.items():
        assert inputs[name]["default"] == default, name
        assert inputs[name]["required"] is False, name


def test_runs_the_core_handlers_with_the_moved_flags() -> None:
    script = _step("Run boundary checks")["run"]
    assert _PARITY_CALL in script
    assert _MIGRATION_CALL in script
    assert 'exit "$FAILURE_COUNT"' in script
    assert '"${{ inputs.warn-only }}" == "true"' in script


def test_handlers_run_from_the_actions_own_checkout() -> None:
    install = _step("Install omnibase_core boundary handlers")["run"]
    assert 'CORE_ROOT="$(cd "${GITHUB_ACTION_PATH}/../../.." && pwd)"' in install
    assert 'uv sync --project "${CORE_ROOT}" --frozen --no-dev' in install
    run = _step("Run boundary checks")
    assert run["env"]["CORE_ROOT"] == "${{ steps.core.outputs.root }}"


def test_never_references_the_change_control_repository() -> None:
    text = ACTION_PATH.read_text(encoding="utf-8")
    assert _FORBIDDEN_REFERENCE not in text
    # Positive control: the scan finds the name when it is present.
    assert (
        _FORBIDDEN_REFERENCE in text + "\n# repository: OmniNode-ai/onex_change_control"
    )
    checkouts = [
        s for s in _steps() if str(s.get("uses", "")).startswith("actions/checkout@")
    ]
    assert len(checkouts) == 1
    assert "repository" not in checkouts[0].get("with", {})


def test_every_action_is_pinned_by_full_sha() -> None:
    uses = [s["uses"] for s in _steps() if "uses" in s]
    assert uses
    for ref in uses:
        assert _FULL_SHA_USES.match(ref), ref


def test_handler_modules_expose_main() -> None:
    from omnibase_core.handlers import (
        handler_boundary_parity,
        handler_migration_conflicts,
    )

    assert callable(handler_boundary_parity.main)
    assert callable(handler_migration_conflicts.main)
