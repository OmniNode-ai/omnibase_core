# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "ci.yml"


def _ci_job(name: str) -> dict[str, object]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    return data["jobs"][name]


def _boundary_validation_step() -> dict[str, object]:
    job = _ci_job("boundary-validation")
    steps = job["steps"]

    assert isinstance(steps, list)
    for step in steps:
        if isinstance(step, dict) and "validate-boundaries" in str(
            step.get("uses", "")
        ):
            return step

    raise AssertionError("boundary-validation job must run validate-boundaries")


def test_parallel_unit_split_timeout_tolerates_self_hosted_runner_pressure() -> None:
    job = _ci_job("test-parallel")

    assert job["timeout-minutes"] >= 35


def test_docs_validation_timeout_tolerates_merge_queue_pressure() -> None:
    job = _ci_job("docs-validation")

    assert job["timeout-minutes"] >= 10


def test_pr_and_merge_queue_use_bounded_xdist_workers() -> None:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    workers = data["env"]["PYTEST_XDIST_WORKERS"]

    assert "github.event_name == 'pull_request'" in workers
    assert "github.event_name == 'merge_group'" in workers
    assert "OMNI_PUBLIC_PR_PYTEST_XDIST_WORKERS || '1'" in workers
    assert "OMNI_MERGE_GROUP_PYTEST_XDIST_WORKERS || '2'" in workers


def test_cross_repo_boundary_validation_job_is_blocking() -> None:
    job = _ci_job("boundary-validation")

    assert "continue-on-error" not in job


def test_cross_repo_boundary_validation_action_is_not_warn_only() -> None:
    step = _boundary_validation_step()

    assert "continue-on-error" not in step
    assert step["with"]["checks"] == "boundary-parity"
    assert step["with"]["warn-only"] == "false"


def test_cross_repo_boundary_validation_clones_all_boundary_repos() -> None:
    step = _boundary_validation_step()

    repos = {repo.strip() for repo in step["with"]["repos"].split(",")}
    assert repos == {
        "omniclaude",
        "omnidash",
        "omniintelligence",
        "omnibase_infra",
        "omnibase_core",
        "omnimemory",
        "onex_change_control",
    }


def test_ci_summary_requires_cross_repo_boundary_validation() -> None:
    job = _ci_job("ci-summary")

    assert "boundary-validation" in job["needs"]
