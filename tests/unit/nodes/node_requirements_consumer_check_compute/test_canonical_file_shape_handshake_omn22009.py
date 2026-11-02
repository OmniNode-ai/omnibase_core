# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Canonical file-shape handshake refusals through the node runtime (OMN-22009)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.nodes.node_requirements_consumer_check_compute.runtime_requirements_consumer_check import (
    main,
)

pytestmark = pytest.mark.unit

SPEC_PATH = (
    Path(__file__).resolve().parents[4]
    / "architecture-handshakes"
    / "validator-requirements.yaml"
)
FIXTURE_REPO = "fixture-shape-consumer"


@pytest.fixture
def shape_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Use the real requirement in an isolated spec modeling universal rollout."""
    entry = yaml.safe_load(SPEC_PATH.read_text())["required_validators"][
        "canonical-file-shape"
    ]
    spec = tmp_path / "requirements.yaml"
    spec.write_text(
        yaml.safe_dump(
            {
                "known_repos": [FIXTURE_REPO],
                "required_validators": {
                    "canonical-file-shape": {**entry, "applies_to_repos": "all"}
                },
            }
        )
    )
    root = tmp_path / FIXTURE_REPO
    root.mkdir()
    (root / ".pre-commit-config.yaml").write_text("repos: []\n")
    _write_ci(root)
    return root, spec


def _write_hook(root: Path) -> None:
    (root / ".pre-commit-config.yaml").write_text(
        yaml.safe_dump(
            {
                "repos": [
                    {
                        "repo": "local",
                        "hooks": [
                            {
                                "id": "canonical-file-shape",
                                "name": "canonical-file-shape",
                                "language": "system",
                                "entry": (
                                    "python -m omnibase_core.nodes."
                                    "node_canonical_file_shape_check_compute."
                                    "runtime_canonical_file_shape_check"
                                ),
                            }
                        ],
                    }
                ]
            }
        )
    )


def _write_ci(root: Path) -> None:
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    (workflows / "shape.yml").write_text(
        yaml.safe_dump(
            {
                "name": "canonical-file-shape",
                "on": "pull_request",
                "jobs": {
                    "shape": {
                        "runs-on": "ubuntu-latest",
                        "steps": [
                            {
                                "run": (
                                    "python -m omnibase_core.nodes."
                                    "node_canonical_file_shape_check_compute."
                                    "runtime_canonical_file_shape_check"
                                )
                            }
                        ],
                    }
                },
            }
        )
    )


def _run(root: Path, spec: Path) -> int:
    return main(["--repo", FIXTURE_REPO, "--repo-root", str(root), "--spec", str(spec)])


def test_missing_canonical_file_shape_hook_refuses_named_repository(
    shape_repo: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """AC1: a missing hook refuses the named repo even when CI is wired."""
    root, spec = shape_repo
    assert _run(root, spec) == 2
    refusal = capsys.readouterr().err
    assert "1 validator-requirement gap(s):" in refusal
    assert f"[MISSING_PRE_COMMIT] {FIXTURE_REPO} :: canonical-file-shape" in refusal

    _write_hook(root)
    assert _run(root, spec) == 0
    assert f"validator-requirements: OK ({FIXTURE_REPO} @" in capsys.readouterr().err


def test_missing_canonical_file_shape_ci_refuses_named_repository(
    shape_repo: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """A wired hook alone does not satisfy the CI half of the handshake."""
    root, spec = shape_repo
    _write_hook(root)
    (root / ".github" / "workflows" / "shape.yml").unlink()
    assert _run(root, spec) == 2
    refusal = capsys.readouterr().err
    assert "1 validator-requirement gap(s):" in refusal
    assert f"[MISSING_CI_WORKFLOW] {FIXTURE_REPO} :: canonical-file-shape" in refusal

    _write_ci(root)
    assert _run(root, spec) == 0
    assert f"validator-requirements: OK ({FIXTURE_REPO} @" in capsys.readouterr().err
