# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-21166: receipt-gate check-timeout-seconds input and per-check timeout resolution."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)
SHADOW_EXPRESSION = "${{ inputs.shadow == 'true' }}"


def _workflow() -> dict[Any, Any]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert isinstance(data, dict)
    return data


def _steps(job: str) -> list[dict[str, Any]]:
    return _workflow()["jobs"][job]["steps"]


def _step_by_id(step_id: str) -> dict[str, Any]:
    for step in _steps("dod-verify"):
        if step.get("id") == step_id:
            return step
    raise AssertionError(f"step with id {step_id!r} not found in dod-verify")


def _run_check_timeout_script(
    script: str, value: str, github_env: Path
) -> tuple[int, str, str]:
    env = {
        "PATH": "/usr/bin:/bin",
        "GITHUB_ENV": str(github_env),
        "CHECK_TIMEOUT_SECONDS": value,
    }
    proc = subprocess.run(
        ["bash", "-e", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_check_timeout_input_declared() -> None:
    workflow = _workflow()
    # PyYAML reads the bare `on:` key as the boolean True.
    trigger = workflow.get(True, workflow.get("on"))
    inputs = trigger["workflow_call"]["inputs"]
    assert "check-timeout-seconds" in inputs, "check-timeout-seconds input missing"
    spec = inputs["check-timeout-seconds"]
    assert spec.get("type") == "string"
    assert spec.get("required") is False
    assert spec.get("default") == ""


def test_check_timeout_step_position_and_if() -> None:
    steps = _steps("dod-verify")
    ids = [s.get("id") for s in steps]
    assert "check_timeout" in ids, "check_timeout step missing"
    idx = ids.index("check_timeout")
    assert idx + 1 < len(ids)
    assert ids[idx + 1] == "verifier", (
        "check_timeout must be immediately before verifier"
    )

    check_step = steps[idx]
    verifier_step = steps[idx + 1]
    assert check_step.get("if") == verifier_step.get("if"), (
        "check_timeout if must match verifier if"
    )


def test_check_timeout_step_shadow_continue_on_error() -> None:
    step = _step_by_id("check_timeout")
    assert step.get("continue-on-error") == SHADOW_EXPRESSION, (
        f"continue-on-error must be {SHADOW_EXPRESSION!r}, got {step.get('continue-on-error')!r}"
    )


def test_check_timeout_step_env_maps_input() -> None:
    step = _step_by_id("check_timeout")
    env = step.get("env", {})
    assert env.get("CHECK_TIMEOUT_SECONDS") == "${{ inputs.check-timeout-seconds }}"


def test_check_timeout_script_empty_value(tmp_path: Path) -> None:
    step = _step_by_id("check_timeout")
    script = step.get("run", "")
    assert script, "check_timeout step has no run script"

    github_env = tmp_path / "github_env"
    github_env.write_text("")
    rc, _stdout, stderr = _run_check_timeout_script(script, "", github_env)
    assert rc == 0, f"empty value should exit 0, got rc={rc}, stderr={stderr}"
    assert github_env.read_text() == "", "empty value must not write to GITHUB_ENV"


@pytest.mark.parametrize("value", ["1", "30", "300", "900"])
def test_check_timeout_script_accepted_values(value: str, tmp_path: Path) -> None:
    step = _step_by_id("check_timeout")
    script = step.get("run", "")
    assert script, "check_timeout step has no run script"

    github_env = tmp_path / "github_env"
    github_env.write_text("")
    rc, _stdout, stderr = _run_check_timeout_script(script, value, github_env)
    assert rc == 0, f"value {value!r} should exit 0, got rc={rc}, stderr={stderr}"
    expected = f"DOD_VERIFY_CHECK_TIMEOUT_S={value}\n"
    assert github_env.read_text() == expected, (
        f"value {value!r}: GITHUB_ENV content should be {expected!r}, got {github_env.read_text()!r}"
    )


@pytest.mark.parametrize(
    "value",
    ["0", "-5", "901", "1000", "30.5", "abc", " 300", "300s", "0300", "1e3"],
)
def test_check_timeout_script_refused_values(value: str, tmp_path: Path) -> None:
    step = _step_by_id("check_timeout")
    script = step.get("run", "")
    assert script, "check_timeout step has no run script"

    github_env = tmp_path / "github_env"
    github_env.write_text("")
    rc, stdout, _stderr = _run_check_timeout_script(script, value, github_env)
    assert rc == 1, f"value {value!r} should exit 1, got rc={rc}"
    assert "::error::check-timeout-seconds" in stdout, (
        f"value {value!r}: stdout should contain ::error::check-timeout-seconds, got {stdout!r}"
    )
    assert github_env.read_text() == "", (
        f"value {value!r}: GITHUB_ENV must remain empty"
    )


def test_head_verify_if_contains_check_timeout_guard() -> None:
    step = _step_by_id("head_verify")
    step_if = step.get("if", "")
    assert "steps.check_timeout.outcome != 'failure'" in step_if, (
        f"head_verify if must contain check_timeout guard, got {step_if!r}"
    )


def test_base_control_if_contains_check_timeout_guard() -> None:
    step = _step_by_id("base_control")
    step_if = step.get("if", "")
    assert "steps.check_timeout.outcome != 'failure'" in step_if, (
        f"base_control if must contain check_timeout guard, got {step_if!r}"
    )


def test_no_dod_verify_check_timeout_s_in_envs() -> None:
    job = _workflow()["jobs"]["dod-verify"]
    job_env = job.get("env", {})
    assert "DOD_VERIFY_CHECK_TIMEOUT_S" not in job_env, (
        "DOD_VERIFY_CHECK_TIMEOUT_S must not be in dod-verify job env"
    )
    for step in job.get("steps", []):
        step_env = step.get("env", {})
        assert "DOD_VERIFY_CHECK_TIMEOUT_S" not in step_env, (
            f"DOD_VERIFY_CHECK_TIMEOUT_S must not be in step {step.get('id')!r} env"
        )


def test_summarise_loop_order() -> None:
    step = next(s for s in _steps("dod-verify") if s.get("name") == "Summarise")
    script = step.get("run", "")
    assert script, "Summarise step has no run script"

    match = re.search(r"for\s+step_id\s+in\s+(.+)", script)
    assert match, "Summarise script must contain a 'for step_id in ...' loop"
    loop_body = match.group(1)

    install_uv_pos = loop_body.find("install_uv")
    check_timeout_pos = loop_body.find("check_timeout")
    verifier_pos = loop_body.find("verifier")

    assert install_uv_pos != -1, "install_uv missing from Summarise loop"
    assert check_timeout_pos != -1, "check_timeout missing from Summarise loop"
    assert verifier_pos != -1, "verifier missing from Summarise loop"
    assert install_uv_pos < check_timeout_pos < verifier_pos, (
        f"Summarise loop order must be install_uv < check_timeout < verifier, "
        f"got positions install_uv={install_uv_pos}, check_timeout={check_timeout_pos}, verifier={verifier_pos}"
    )
