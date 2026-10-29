# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Handler and runtime tests for the requirements-consumer check node (OMN-21520)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.enums.enum_validator_requirement_gap_kind import (
    EnumValidatorRequirementGapKind,
)
from omnibase_core.models.nodes.requirements_consumer_check.model_requirements_consumer_check_input import (
    ModelRequirementsConsumerCheckInput,
)
from omnibase_core.nodes.node_requirements_consumer_check_compute.handler import (
    NodeRequirementsConsumerCheckCompute,
)
from omnibase_core.nodes.node_requirements_consumer_check_compute.runtime_requirements_consumer_check import (
    main,
)

pytestmark = pytest.mark.unit


def _spec(tmp_path: Path) -> Path:
    spec = tmp_path / "spec.yaml"
    spec.write_text(
        yaml.safe_dump(
            {
                "schema_version": {"major": 1, "minor": 1, "patch": 0},
                "required_validators": {
                    "my-validator": {
                        "description": "x",
                        "central_source": "x",
                        "pre_commit": "required",
                        "ci_workflow": "optional",
                        "required_check_on_main": None,
                        "silent_skip_allowed": False,
                        "excludes": {"allowed": [], "forbidden": []},
                        "applies_to_repos": "all",
                        "pre_commit_hook_ids": ["my-validator"],
                    }
                },
                "metadata": {},
                "known_repos": [],
            }
        )
    )
    return spec


def _repo(tmp_path: Path, *, wired: bool) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    hooks = (
        [{"id": "my-validator", "name": "mv", "entry": "run-mv", "language": "system"}]
        if wired
        else []
    )
    (root / ".pre-commit-config.yaml").write_text(
        yaml.safe_dump({"repos": [{"repo": "local", "hooks": hooks}]})
    )
    return root


def test_handle_returns_no_gaps_when_wired(tmp_path: Path) -> None:
    result = NodeRequirementsConsumerCheckCompute().handle(
        ModelRequirementsConsumerCheckInput(
            repo="r",
            repo_root=str(_repo(tmp_path, wired=True)),
            spec_path=str(_spec(tmp_path)),
        )
    )
    assert result.gaps == ()


def test_handle_returns_missing_pre_commit_gap(tmp_path: Path) -> None:
    result = NodeRequirementsConsumerCheckCompute().handle(
        ModelRequirementsConsumerCheckInput(
            repo="r",
            repo_root=str(_repo(tmp_path, wired=False)),
            spec_path=str(_spec(tmp_path)),
        )
    )
    assert [(g.validator, g.kind) for g in result.gaps] == [
        ("my-validator", EnumValidatorRequirementGapKind.MISSING_PRE_COMMIT)
    ]


def test_main_exit_zero_when_wired(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path, wired=True)
    rc = main(["--repo", "r", "--repo-root", str(root), "--spec", str(_spec(tmp_path))])
    assert rc == 0
    assert "validator-requirements: OK (r @" in capsys.readouterr().err


def test_main_exit_two_on_gap(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path, wired=False)
    rc = main(["--repo", "r", "--repo-root", str(root), "--spec", str(_spec(tmp_path))])
    assert rc == 2
    assert "1 validator-requirement gap(s):" in capsys.readouterr().err
