# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Handler and runtime tests for the rollup-coverage check node (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.models.nodes.rollup_coverage_check.model_rollup_coverage_check_input import (
    ModelRollupCoverageCheckInput,
)
from omnibase_core.nodes.node_rollup_coverage_check_compute.handler import (
    NodeRollupCoverageCheckCompute,
)
from omnibase_core.nodes.node_rollup_coverage_check_compute.runtime_rollup_coverage_check import (
    main,
)

pytestmark = pytest.mark.unit


def _spec(tmp_path: Path) -> Path:
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        yaml.safe_dump(
            {
                "required_validators": {},
                "model_b_rollup_enforcement": {
                    "repos": {
                        "r": {
                            "rollup_workflow": "ci.yml",
                            "rollup_job": "gate",
                            "required_rollup_context": "Gate",
                            "validator_jobs": {"my-validator": ["lint"]},
                        }
                    }
                },
            }
        )
    )
    return spec


def _repo(tmp_path: Path, *, covered: bool) -> Path:
    root = tmp_path / "repo"
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True)
    gate: dict[str, object] = {"name": "Gate", "runs-on": "ubuntu-latest"}
    if covered:
        gate["needs"] = ["lint"]
    (workflows / "ci.yml").write_text(
        yaml.safe_dump({"jobs": {"lint": {"runs-on": "ubuntu-latest"}, "gate": gate}})
    )
    return root


def test_handle_airtight_rollup(tmp_path: Path) -> None:
    result = NodeRollupCoverageCheckCompute().handle(
        ModelRollupCoverageCheckInput(
            repo="r",
            repo_root=str(_repo(tmp_path, covered=True)),
            spec_path=str(_spec(tmp_path)),
        )
    )
    assert result.opted_in is True
    assert result.gaps == ()


def test_handle_reports_uncovered_validator(tmp_path: Path) -> None:
    result = NodeRollupCoverageCheckCompute().handle(
        ModelRollupCoverageCheckInput(
            repo="r",
            repo_root=str(_repo(tmp_path, covered=False)),
            spec_path=str(_spec(tmp_path)),
        )
    )
    assert [g.validator for g in result.gaps] == ["my-validator"]


def test_handle_not_opted_in(tmp_path: Path) -> None:
    result = NodeRollupCoverageCheckCompute().handle(
        ModelRollupCoverageCheckInput(
            repo="other",
            repo_root=str(_repo(tmp_path, covered=True)),
            spec_path=str(_spec(tmp_path)),
        )
    )
    assert result.opted_in is False
    assert result.gaps == ()


def test_main_exit_zero_when_airtight(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path, covered=True)
    rc = main(["--repo", "r", "--repo-root", str(root), "--spec", str(_spec(tmp_path))])
    assert rc == 0
    assert "rollup-coverage: AIRTIGHT (r @" in capsys.readouterr().err


def test_main_exit_two_on_gap(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path, covered=False)
    rc = main(["--repo", "r", "--repo-root", str(root), "--spec", str(_spec(tmp_path))])
    assert rc == 2
    assert "1 rollup-coverage gap(s):" in capsys.readouterr().err
