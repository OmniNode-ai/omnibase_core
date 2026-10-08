# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20074: caller evidence makes verify a reported success no-op, never skipped."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)


def _workflow() -> dict[Any, Any]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert isinstance(data, dict)
    return data


def _steps(job: str) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], _workflow()["jobs"][job]["steps"])


def test_enforcing_caller_mode_verify_runs_as_a_success_noop_with_one_line_reason(
    tmp_path: Path,
) -> None:
    job = _workflow()["jobs"]["verify"]
    # No job-level condition: GitHub never reports verify skipped, whatever the
    # caller passes for evidence-source and shadow.
    assert "if" not in job
    exempt = next(s for s in job["steps"] if s.get("id") == "bot_exempt")
    output = tmp_path / "github_output.txt"
    output.write_text("")
    # No gh on PATH: the no-op must exit before it reads anything.
    env = {
        "PATH": "/usr/bin:/bin",
        "GITHUB_OUTPUT": str(output),
        "CALLER_EVIDENCE_MODE": "true",
    }
    script = exempt["run"].replace("${{ github.repository }}", "o/r")
    result = subprocess.run(
        [shutil.which("bash") or "bash", "-e", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output.read_text().splitlines() == ["exempt=true"]
    notices = [
        line for line in result.stdout.splitlines() if line.startswith("::notice::")
    ]
    assert notices == [
        "::notice::verify does not apply in caller-evidence mode; "
        "repo-evidence / dod-verify carries the verdict."
    ]


def test_every_verify_step_after_the_noop_is_gated_on_the_exemption() -> None:
    steps = _steps("verify")
    exempt_index = next(
        i for i, step in enumerate(steps) if step.get("id") == "bot_exempt"
    )
    before = steps[:exempt_index]
    assert [step["name"] for step in before] == [
        "Check out PR head",
        "Resolve receipt gate branch policy",
        "Check out omnibase_core (for occ_preflight_wait.py)",
    ]
    for step in before:
        assert "inputs.evidence-source != 'caller'" in step["if"], step["name"]
    after = steps[exempt_index + 1 :]
    assert after
    for step in after:
        assert "steps.bot_exempt.outputs.exempt != 'true'" in step["if"], step["name"]


def test_occ_mode_still_runs_the_gate() -> None:
    exempt = next(s for s in _steps("verify") if s.get("id") == "bot_exempt")
    script = cast(str, exempt["run"])
    assert script.index('"${CALLER_EVIDENCE_MODE:-}" = "true"') < script.index(
        "gh pr view"
    )
    assert exempt["env"]["CALLER_EVIDENCE_MODE"] == (
        "${{ inputs.evidence-source == 'caller' }}"
    )
