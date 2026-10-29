# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Handler and runtime tests for the PR-workflow ratchet node (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.models.nodes.pull_request_workflow_ratchet_check.model_pull_request_workflow_ratchet_check_input import (
    ModelPullRequestWorkflowRatchetCheckInput,
)
from omnibase_core.nodes.node_pull_request_workflow_ratchet_check_compute.handler import (
    NodePullRequestWorkflowRatchetCheckCompute,
)
from omnibase_core.nodes.node_pull_request_workflow_ratchet_check_compute.runtime_pull_request_workflow_ratchet_check import (
    main,
)

pytestmark = pytest.mark.unit

_REGISTRY = Path("architecture-handshakes/pull-request-workflow-budget.yaml")


def _make_repo(root: Path, *, allowlisted: list[str]) -> None:
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        yaml.safe_dump({"name": "ci", "on": {"pull_request": {}}, "jobs": {}}),
        encoding="utf-8",
    )
    registry = root / _REGISTRY
    registry.parent.mkdir(parents=True)
    registry.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "budget": len(allowlisted),
                "allowlisted_workflows": allowlisted,
                "waivers": [],
            }
        ),
        encoding="utf-8",
    )


def test_handle_enumerated_workflow_passes(tmp_path: Path) -> None:
    _make_repo(tmp_path, allowlisted=["ci.yml"])
    output = NodePullRequestWorkflowRatchetCheckCompute().handle(
        ModelPullRequestWorkflowRatchetCheckInput(
            repo_root=str(tmp_path), registry_path=str(tmp_path / _REGISTRY)
        )
    )
    assert output.passed is True
    assert output.gaps == []


def test_handle_unregistered_workflow_fails(tmp_path: Path) -> None:
    _make_repo(tmp_path, allowlisted=[])
    output = NodePullRequestWorkflowRatchetCheckCompute().handle(
        ModelPullRequestWorkflowRatchetCheckInput(
            repo_root=str(tmp_path), registry_path=str(tmp_path / _REGISTRY)
        )
    )
    assert output.passed is False
    assert [(g.workflow_file, g.code) for g in output.gaps] == [
        ("ci.yml", "UNREGISTERED")
    ]


def test_main_enumerated_workflow_exits_zero(tmp_path: Path) -> None:
    _make_repo(tmp_path, allowlisted=["ci.yml"])
    assert main(["--repo-root", str(tmp_path)]) == 0


def test_main_unregistered_workflow_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _make_repo(tmp_path, allowlisted=[])
    assert main(["--repo-root", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "the count-locked ratchet over pull_request-triggered workflows" in err
    assert "ci.yml [UNREGISTERED]" in err


def test_main_missing_registry_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--repo-root", str(tmp_path)]) == 1
    assert "pull-request-workflow-ratchet: registry error:" in capsys.readouterr().err
