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


def _job() -> dict[str, object]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    return data["jobs"]["auto-merge"]


def test_auto_merge_job_requires_occ_preflight_success() -> None:
    # OMN-16288: the auto-merge job trusts the already-required
    # "occ-preflight / eligibility" check's conclusion (resolved from the PR
    # body's Evidence-Source pin by the shared occ-preflight.yml reusable --
    # the same pattern omnibase_infra/omnimarket use) instead of re-resolving
    # OCC eligibility itself. It must not run any step before that gate is
    # satisfied.
    job = _job()

    assert "occ-preflight" in job["needs"]
    assert "needs.occ-preflight.result == 'success'" in job["if"]


def test_auto_merge_does_not_re_resolve_occ_against_heads_main() -> None:
    # Regression guard for OMN-16288: this job previously re-resolved OCC
    # eligibility by fetching onex_change_control@heads/main and re-running
    # validator_occ_merge_eligibility against that checkout. Nothing promotes
    # OCC's own contracts dev->main (OMN-15067), so OCC main is thousands of
    # commits stale and that duplicate check failed permanently
    # (eligible:false/missing_contract, e.g. OMN-16280 / run 32359138410) --
    # it never gated arming (the job-level needs/if above already did), it
    # only ever broke it. It must not come back.
    names = [step.get("name") for step in _steps()]

    assert "Resolve OCC main SHA" not in names
    assert "Check out OCC evidence snapshot" not in names
    assert "OCC auto-merge preflight" not in names
    assert "Set up Python 3.13" not in names

    for step in _steps():
        run = step.get("run", "")
        if isinstance(run, str):
            assert "onex_change_control/git/ref/heads/main" not in run
            assert "validator_occ_merge_eligibility" not in run


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
