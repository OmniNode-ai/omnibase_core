# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20074: verify always reports a success no-op with one notice."""

from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)
NOTICE = "::notice::caller evidence is verified by the dod-verify job (OMN-20074)"


def _workflow() -> dict[Any, Any]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert isinstance(data, dict)
    return data


def test_enforcing_caller_mode_verify_runs_as_a_success_noop_with_one_line_reason(
    tmp_path: Path,
) -> None:
    job = _workflow()["jobs"]["verify"]
    assert "if" not in job
    assert len(job["steps"]) == 1
    step = job["steps"][0]
    assert set(step) == {"name", "run"}
    assert step["name"] == "Caller evidence runs in dod-verify"
    assert step["run"].splitlines() == [f'echo "{NOTICE}"']
    assert shlex.split(step["run"]) == ["echo", NOTICE]
    result = subprocess.run(
        [shutil.which("bash") or "bash", "-e", "-c", step["run"]],
        env={"PATH": str(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [NOTICE]
    assert result.stderr == ""


def test_verify_has_no_other_steps_or_side_effects() -> None:
    steps = _workflow()["jobs"]["verify"]["steps"]
    assert steps == [
        {"name": "Caller evidence runs in dod-verify", "run": f'echo "{NOTICE}"'}
    ]
    assert all("env" not in s and "uses" not in s and "if" not in s for s in steps)
