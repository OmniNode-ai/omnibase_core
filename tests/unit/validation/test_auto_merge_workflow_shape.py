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
        "Enqueue armed PR and verify it entered the queue"
    )


def test_auto_merge_preflight_uses_single_pr_snapshot() -> None:
    script = _step("OCC auto-merge preflight")["run"]

    assert "gh pr view" in script
    assert "--json body,title,headRefName,commits" in script
    assert "omnibase_core.validation.validator_occ_merge_eligibility" in script
    assert "--occ-commit-sha" in script
    assert "--pr-body-file /tmp/pr_body.txt" in script


def test_enable_auto_merge_arms_bare_auto_not_squash() -> None:
    # OMN-13214: dev is queue-controlled; an explicit --squash is rejected and
    # the PR is never enqueued. The actual `gh pr merge` command must arm bare
    # --auto (a comment may still explain why --squash is wrong).
    script = _step("Enable auto-merge")["run"]
    assert isinstance(script, str)

    merge_lines = [
        line
        for line in script.splitlines()
        if "gh pr merge" in line and not line.strip().startswith("#")
    ]
    assert merge_lines, "no `gh pr merge` command found in Enable auto-merge step"
    for line in merge_lines:
        assert "--auto" in line
        assert "--squash" not in line


def test_enqueue_step_classifies_enqueues_and_verifies() -> None:
    # OMN-13214: arming != enqueuing. The enqueue step must classify via the
    # unit-tested helper, explicitly enqueue, and VERIFY the PR entered the queue.
    script = _step("Enqueue armed PR and verify it entered the queue")["run"]

    assert "scripts/ci/merge_queue_enqueue.py classify" in script
    assert "scripts/ci/merge_queue_enqueue.py verify" in script
    assert "enqueuePullRequest" in script
    assert "gh pr update-branch" in script
    # Must fail loudly when a green + armed PR does not enter the queue.
    assert "::error::" in script
