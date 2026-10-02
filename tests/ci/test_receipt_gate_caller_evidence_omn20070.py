# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Shape guards for caller-contract verification and its must-fail control."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW_PATH = (
    Path(__file__).resolve().parents[2] / ".github" / "workflows" / "receipt-gate.yml"
)
HEAD_STEP = "Verify the contract at the PR head"
BASE_STEP = "Must-fail control at the merge base"


def _workflow() -> dict[Any, Any]:
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert isinstance(data, dict)
    return data


def _job() -> dict[str, Any]:
    return _workflow()["jobs"]["dod-verify"]


def _step(name: str) -> dict[str, Any]:
    return next(step for step in _job()["steps"] if step.get("name") == name)


def test_inputs_preserve_existing_defaults_and_expose_caller_verifier() -> None:
    workflow = _workflow()
    # PyYAML interprets the YAML 1.1 `on` key as True.
    inputs = workflow.get(True, workflow.get("on"))["workflow_call"]["inputs"]
    expected = {
        "contracts-dir": "contracts",
        "receipts-dir": "drift/dod_receipts",
        "branch-policy-mode": "legacy",
        "core-ref": "dev",
        "evidence-source": "occ",
        "verifier-version": "0.4.280",
    }
    for name, default in expected.items():
        assert inputs[name]["default"] == default
        assert inputs[name]["type"] == "string"
        assert inputs[name]["required"] is False


def test_jobs_select_evidence_source_and_preserve_occ_steps() -> None:
    verify = _workflow()["jobs"]["verify"]
    assert verify["if"] == "inputs.evidence-source != 'caller'"
    names = {step.get("name") for step in verify["steps"]}
    assert {
        "Resolve Evidence-Source",
        "Run OCC Eligibility",
        "Run Receipt-Gate",
    } <= names
    caller = _job()
    assert caller["name"] == "dod-verify"
    assert caller["if"] == "inputs.evidence-source == 'caller'"
    # Same routing as verify, with pull_request_target counted as a pull request.
    assert (
        caller["runs-on"].replace(
            "((github.event_name == 'pull_request' || github.event_name == 'pull_request_target') &&",
            "(github.event_name == 'pull_request' &&",
        )
        == verify["runs-on"]
    )
    assert caller["timeout-minutes"] == 40
    assert caller["env"] == {"ACTIONS_CACHE_URL": "", "ACTIONS_RUNTIME_URL": ""}
    assert caller["permissions"] == {"contents": "read", "pull-requests": "read"}


def test_caller_steps_run_in_order_without_an_occ_checkout() -> None:
    steps = _job()["steps"]
    assert [step.get("name") for step in steps] == [
        "Refuse anything but a same-repository pull request",
        "Resolve the cited tickets",
        "Check out the pull request head",
        "Set up Python 3.13",
        "Install uv",
        "Install the pinned verifier",
        HEAD_STEP,
        "Prepare the merge base with the pull request's test side laid over it",
        BASE_STEP,
        "Summarise",
    ]
    for step in steps:
        assert (
            step.get("with", {}).get("repository") != "OmniNode-ai/onex_change_control"
        )
    checkout = _step("Check out the pull request head")
    assert checkout["uses"] == "actions/checkout@v7"
    assert checkout["with"] == {
        "repository": "${{ github.repository }}",
        "ref": "${{ github.event.pull_request.head.sha }}",
        "fetch-depth": 0,
        "persist-credentials": False,
        "path": ".dod-verify/head_home/${{ github.event.repository.name }}",
    }
    assert _step("Set up Python 3.13")["with"]["python-version"] == "3.13"
    assert _step("Install uv")["uses"] == "astral-sh/setup-uv@v7"


def test_caller_scripts_use_env_for_expression_values() -> None:
    for step in _job()["steps"]:
        script = step.get("run", "")
        for expression in (
            "${{ github.event.",
            "${{ github.repository",
            "${{ github.workspace",
            "${{ inputs.",
        ):
            assert expression not in script, step.get("name")
    refusal = _step("Refuse anything but a same-repository pull request")
    assert "pull_request|pull_request_target" in refusal["run"]
    assert '[ "$HEAD_REPOSITORY" != "$CALLER_REPOSITORY" ]' in refusal["run"]
    tickets = _step("Resolve the cited tickets")
    assert tickets["env"]["PR_TITLE"] == "${{ github.event.pull_request.title }}"
    assert "grep -oE 'OMN-[0-9]+'" in tickets["run"]
    assert "^OMN-[0-9]+$" in tickets["run"]


def test_install_validates_and_pins_the_verifier_before_importing() -> None:
    step = _step("Install the pinned verifier")
    assert step["env"]["VERIFIER_VERSION"] == "${{ inputs.verifier-version }}"
    script = step["run"]
    assert r"^[0-9]+\.[0-9]+\.[0-9]+$" in script
    assert script.index(r"^[0-9]+\.[0-9]+\.[0-9]+$") < script.index("uv pip install")
    assert '"omnimarket==${VERIFIER_VERSION}"' in script
    assert "--no-config" in script
    assert (
        'uv venv --clear --python 3.13 "$GITHUB_WORKSPACE/.dod-verify/venv"' in script
    )
    assert '"$GITHUB_ENV"' in script
    assert '"$DOD_VERIFY_PY" -c "import omnimarket.nodes.node_dod_verify"' in script


@pytest.mark.parametrize("name", [HEAD_STEP, BASE_STEP])
def test_both_invocations_use_the_same_node_and_allow_detached_ci_clones(
    name: str,
) -> None:
    step = _step(name)
    assert step["env"]["DOD_VERIFY_ALLOW_STALE_PRODUCT_CLONE"] == "1"
    assert step["env"]["GH_TOKEN"] == "${{ github.token }}"
    script = step["run"]
    assert '"$DOD_VERIFY_PY" -m omnimarket.nodes.node_dod_verify' in script
    assert "--execution-audience hosted" in script
    assert "Receipt written to:" in script


def test_head_failure_keeps_json_diagnostics() -> None:
    script = _step(HEAD_STEP)["run"]
    assert "set -euo pipefail" in script
    assert "|| rc=$?" in script
    assert "status=" in script
    assert "error_message=" in script
    assert "stdout is not JSON" in script
    assert "but carries no contracts/$ticket.yaml" in script


def test_base_overlay_requires_changed_tests_and_cited_contracts() -> None:
    script = _step(
        "Prepare the merge base with the pull request's test side laid over it"
    )["run"]
    assert 'merge-base "$BASE_SHA" "$HEAD_SHA"' in script
    assert 'fetch --no-tags origin "$BASE_SHA"' in script
    assert 'worktree add --detach "$base_tree" "$MB"' in script
    assert "--diff-filter=ACMR" in script
    assert "while IFS= read -r" in script
    assert '"$path" == *..* || "$path" == /*' in script
    assert 'rm -rf "$GITHUB_WORKSPACE/.dod-verify/base_home"' in script
    assert '"contracts/$ticket.yaml"' in script
    assert "no test-side change: the bound tests cannot be shown to fail" in script


def test_control_refuses_always_pass_non_failed_and_missing_bound_checks() -> None:
    script = _step(BASE_STEP)["run"]
    assert "select((.binds_ac | length) > 0)" in script
    assert 'select(.status == "verified")' in script
    assert 'select(.status != "failed" and .status != "verified")' in script
    for message in (
        "zero bound checks",
        "bound test also passes at the merge base: the control did not fail (always-pass)",
        "the control could not run, a control that did not run is not a pass",
        "control stdout is not parseable",
    ):
        assert message in script
    assert ".evidence_id" in script
    assert 'exit "$failed"' in script


def test_summary_always_reports_head_and_base_without_failing() -> None:
    step = _step("Summarise")
    assert step["if"] == "always()"
    script = step["run"]
    for field in (
        "Verifier version:",
        "Head SHA:",
        "Merge base SHA:",
        "acceptance_basis",
    ):
        assert field in script
    assert "base control" in script
    assert '"$GITHUB_STEP_SUMMARY" || true' in script
    assert script.rstrip().endswith("exit 0")
