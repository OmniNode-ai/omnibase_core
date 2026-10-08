# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""OMN-20073: shadow mode makes every receipt-gate caller job a success and records the verdict."""

from __future__ import annotations

import json
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
SHADOW_EXPRESSION = "${{ inputs.shadow == 'true' }}"
HEAD_SHA = "c" * 40


def _workflow() -> dict[Any, Any]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert isinstance(data, dict)
    return data


def _steps(job: str) -> list[dict[str, Any]]:
    return _workflow()["jobs"][job]["steps"]


def _summarise_script() -> str:
    step = next(s for s in _steps("dod-verify") if s.get("name") == "Summarise")
    return step["run"]


def test_shadow_input_defaults_to_false() -> None:
    workflow = _workflow()
    trigger = workflow.get(True, workflow.get("on"))
    shadow = trigger["workflow_call"]["inputs"]["shadow"]
    assert shadow["default"] == "false"
    assert shadow["type"] == "string"
    assert shadow["required"] is False


def test_verify_runs_as_a_reported_noop_in_shadow_caller_mode() -> None:
    job = _workflow()["jobs"]["verify"]
    assert job["if"] == "inputs.evidence-source != 'caller' || inputs.shadow == 'true'"
    by_name = {step["name"]: step for step in job["steps"]}
    # The three steps before the exemption probe touch the pull request or a
    # checkout, so each must be off in caller mode.
    for name in (
        "Check out PR head",
        "Resolve receipt gate branch policy",
        "Check out omnibase_core (for occ_preflight_wait.py)",
    ):
        assert "inputs.evidence-source != 'caller'" in by_name[name]["if"], name
    exempt = by_name["Detect dependency-bot author (receipt-gate exemption)"]
    assert exempt["env"]["CALLER_EVIDENCE_MODE"] == (
        "${{ inputs.evidence-source == 'caller' }}"
    )
    assert exempt["run"].index('"${CALLER_EVIDENCE_MODE:-}" = "true"') < exempt[
        "run"
    ].index("gh pr view")
    # Every step after the probe is gated on the exemption, so they all skip.
    names = list(by_name)
    after = names[names.index(exempt["name"]) + 1 :]
    assert after
    for name in after:
        assert "steps.bot_exempt.outputs.exempt != 'true'" in by_name[name]["if"], name


def test_every_dod_verify_step_but_the_summary_absorbs_a_refusal_in_shadow() -> None:
    steps = _steps("dod-verify")
    for step in steps:
        if step["name"] == "Summarise":
            assert "continue-on-error" not in step
            continue
        assert step["continue-on-error"] == SHADOW_EXPRESSION, step["name"]
    # A job-level continue-on-error would leave the check-run red; the step
    # level is the one that concludes the job success.
    assert "continue-on-error" not in _workflow()["jobs"]["dod-verify"]


def test_a_refusal_stops_the_steps_that_depend_on_it() -> None:
    """Shadow mode must not let a refused fork head be checked out and run.

    continue-on-error leaves the job going after the same-repository refusal,
    so each later step carries the refusal as its own condition.
    """
    steps = _steps("dod-verify")
    names = [step["name"] for step in steps]
    by_id = {step["id"]: step for step in steps if "id" in step}
    after_same_repo = names[names.index(by_id["same_repo"]["name"]) + 1 :]
    guarded = [
        step
        for step in steps
        if step["name"] in after_same_repo
        and step["name"] not in {"Difference against OCC's verdict for the same head"}
        and step["name"] != "Summarise"
    ]
    assert len(guarded) >= 10
    for step in guarded:
        assert "steps.same_repo.outcome != 'failure'" in step["if"], step["name"]
    after_tickets = names[names.index(by_id["tickets"]["name"]) + 1 :]
    for step in guarded:
        if step["name"] in after_tickets:
            assert "steps.tickets.outcome != 'failure'" in step["if"], step["name"]
    assert "steps.same_repo.outcome" not in by_id["same_repo"]["if"]
    assert "steps.tickets.outcome" not in by_id["tickets"]["if"]
    # The checkout of the pull request head is the one that must never run
    # after a fork refusal.
    assert "steps.same_repo.outcome != 'failure'" in by_id["head_checkout"]["if"]


def _run_summary(
    tmp_path: Path, *, shadow: str, steps: dict[str, Any], occ: dict[str, Any] | None
) -> tuple[subprocess.CompletedProcess[str], str]:
    runner_temp = tmp_path / "runner"
    (runner_temp / "dod").mkdir(parents=True)
    (runner_temp / "dod" / "merge-base.txt").write_text("mergebase\n")
    if occ is not None:
        (runner_temp / "dod" / "occ-difference.json").write_text(json.dumps(occ))
    summary = tmp_path / "summary.md"
    summary.write_text("")
    env = {
        "PATH": "/usr/bin:/bin",
        "RUNNER_TEMP": str(runner_temp),
        "GITHUB_STEP_SUMMARY": str(summary),
        "VERIFIER_VERSION": "0.4.294",
        "HEAD_SHA": HEAD_SHA,
        "SHADOW": shadow,
        "STEPS_JSON": json.dumps(steps),
    }
    result = subprocess.run(
        [shutil.which("bash") or "bash", "-e", "-c", _summarise_script()],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return result, summary.read_text()


needs_jq = pytest.mark.skipif(shutil.which("jq") is None, reason="jq is required")


@needs_jq
def test_a_planted_disagreement_is_recorded_and_the_job_still_passes(
    tmp_path: Path,
) -> None:
    steps = {
        "bot_exempt": {"outcome": "success", "outputs": {"exempt": "false"}},
        "tickets": {"outcome": "success"},
        "head_verify": {"outcome": "success"},
        "base_control": {"outcome": "success"},
        # The difference step failed: the classifier disagreed with OCC.
        "occ_difference": {"outcome": "failure"},
    }
    occ = {
        "passed": False,
        "outcome": "unclassified_difference",
        "reason_code": None,
        "old_admitted": False,
        "new_admitted": True,
        "message": "OCC refused and the new path admitted",
    }
    result, summary = _run_summary(tmp_path, shadow="true", steps=steps, occ=occ)
    assert result.returncode == 0, result.stderr
    line = (
        f"Shadow verdict: head={HEAD_SHA} new_path=verified refused_step=none "
        "occ_difference=unclassified_difference/none"
    )
    assert line in summary
    assert f"::notice title=repo-evidence shadow verdict::{line}" in result.stdout


@needs_jq
def test_a_refusal_names_the_first_refused_step_and_still_passes(
    tmp_path: Path,
) -> None:
    steps = {
        "bot_exempt": {"outcome": "success", "outputs": {"exempt": "false"}},
        "same_repo": {"outcome": "success"},
        "tickets": {"outcome": "failure"},
        "head_verify": {"outcome": "failure"},
        "occ_difference": {"outcome": "failure"},
    }
    result, summary = _run_summary(tmp_path, shadow="true", steps=steps, occ=None)
    assert result.returncode == 0, result.stderr
    assert (
        f"Shadow verdict: head={HEAD_SHA} new_path=refused refused_step=tickets "
        "occ_difference=not_compared/unavailable"
    ) in summary


@needs_jq
def test_a_clean_agreement_is_recorded(tmp_path: Path) -> None:
    steps = {
        "bot_exempt": {"outcome": "success", "outputs": {"exempt": "false"}},
        "head_verify": {"outcome": "success"},
        "occ_difference": {"outcome": "success"},
    }
    occ = {"passed": True, "outcome": "agree", "reason_code": None}
    result, summary = _run_summary(tmp_path, shadow="true", steps=steps, occ=occ)
    assert result.returncode == 0, result.stderr
    assert "new_path=verified refused_step=none occ_difference=agree/none" in summary


@needs_jq
def test_a_dependency_bot_is_recorded_as_exempt(tmp_path: Path) -> None:
    steps = {"bot_exempt": {"outcome": "success", "outputs": {"exempt": "true"}}}
    result, summary = _run_summary(tmp_path, shadow="true", steps=steps, occ=None)
    assert result.returncode == 0, result.stderr
    assert "new_path=exempt refused_step=none occ_difference=not_run" in summary


@needs_jq
def test_enforcing_mode_records_no_shadow_verdict(tmp_path: Path) -> None:
    steps = {"bot_exempt": {"outcome": "success", "outputs": {"exempt": "false"}}}
    result, summary = _run_summary(tmp_path, shadow="false", steps=steps, occ=None)
    assert result.returncode == 0, result.stderr
    assert "Shadow verdict" not in summary
    assert "Shadow verdict" not in result.stdout


def test_verify_noop_exempts_without_reading_the_pull_request(tmp_path: Path) -> None:
    exempt = next(s for s in _steps("verify") if s.get("id") == "bot_exempt")
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
    assert "does not apply in caller-evidence mode" in result.stdout
