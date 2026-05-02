# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "auto-merge.yml"
)


def _steps() -> list[dict[str, object]]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    return data["jobs"]["auto-merge"]["steps"]


def _step(name: str) -> dict[str, object]:
    for step in _steps():
        if step.get("name") == name:
            return step
    raise AssertionError(f"{name!r} step not found in auto-merge.yml")


def test_auto_merge_uses_python_313() -> None:
    step = _step("Set up Python 3.13")
    assert step["with"]["python-version"] == "3.13"


def test_auto_merge_pins_occ_before_preflight() -> None:
    resolve_step = _step("Resolve OCC main SHA")
    checkout_step = _step("Check out OCC evidence snapshot")

    assert "git/ref/heads/main" in resolve_step["run"]
    assert checkout_step["with"]["ref"] == "${{ steps.occ_ref.outputs.sha }}"


def test_auto_merge_runs_occ_preflight_before_mutating_pr() -> None:
    names = [step.get("name") for step in _steps()]

    assert names.index("OCC auto-merge preflight") < names.index("Enable auto-merge")
    assert names.index("OCC auto-merge preflight") < names.index(
        "Force enqueue to merge queue"
    )


def test_auto_merge_preflight_uses_single_pr_snapshot() -> None:
    script = _step("OCC auto-merge preflight")["run"]

    assert "gh pr view" in script
    assert "--json body,title,headRefName,commits" in script
    assert "omnibase_core.validation.occ_merge_eligibility" in script
    assert "--occ-commit-sha" in script
    assert "--pr-body-file /tmp/pr_body.txt" in script
