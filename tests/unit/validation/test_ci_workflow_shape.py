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
