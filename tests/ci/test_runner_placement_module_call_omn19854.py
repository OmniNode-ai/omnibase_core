# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The placement workflow exposes its handler module to mechanism audits."""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
MODULE = "omnibase_core.handlers.handler_public_runner_placement_cli"


def _workflow_module_argv() -> list[str]:
    workflow: dict[str, Any] = yaml.safe_load(
        (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    )
    (step,) = [
        step
        for step in workflow["jobs"]["lint-imports"]["steps"]
        if step.get("name") == "Run public-repository runner placement check"
    ]
    (command,) = [
        shlex.split(line)
        for line in step["run"].splitlines()
        if line.strip().startswith("uv run ")
    ]
    assert command[:5] == ["uv", "run", "python", "-m", MODULE], (
        "Mechanism audits need the handler module in the workflow command; "
        "they do not resolve console-script aliases"
    )
    assert command[5:] == ["${args[@]}"], "Forward every placement-check argument"
    return command[3:5]


def test_runner_placement_module_is_visible_in_the_workflow() -> None:
    _workflow_module_argv()


@pytest.mark.parametrize(
    ("visibility", "runs_on", "exit_code", "message"),
    [
        ("public", "ubuntu-latest", 0, "OK: probe adds no self-hosted CI job"),
        ("public", "[self-hosted, omnibase-ci]", 1, "not_in_baseline"),
        ("private", "[self-hosted, omnibase-ci]", 0, "private repository"),
    ],
)
def test_workflow_module_enforces_runner_placement(
    tmp_path: Path, visibility: str, runs_on: str, exit_code: int, message: str
) -> None:
    module_argv = _workflow_module_argv()
    workflows = tmp_path / ".github/workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        f"on: [pull_request]\njobs:\n  probe:\n    runs-on: {runs_on}\n"
        "    steps:\n      - run: echo probe\n",
        encoding="utf-8",
    )
    baseline = tmp_path / "baseline.yaml"
    baseline.write_text("repos: {}\n", encoding="utf-8")
    # CI scans tracked workflows, so use a real repository for the subprocess.
    for args in (("init", "--quiet"), ("add", ".github/workflows/ci.yml")):
        subprocess.run(
            ["git", "-C", str(tmp_path), *args],
            env=scrub_git_location_env(),
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    result = subprocess.run(
        [
            sys.executable,
            *module_argv,
            "--root",
            str(tmp_path),
            "--repo",
            "probe",
            "--visibility",
            visibility,
            "--baseline",
            str(baseline),
        ],
        cwd=ROOT,
        env=scrub_git_location_env(),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == exit_code, result.stdout + result.stderr
    assert message in result.stdout
