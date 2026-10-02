# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Shape guards for caller verification, its control, and the OCC pilot difference."""

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
DIFFERENCE_STEP = "Difference against OCC's verdict for the same head"


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
        "compare-with-occ": "false",
        "occ-context": "occ-preflight / eligibility",
        "occ-wait-seconds": "1500",
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
        DIFFERENCE_STEP,
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
    assert refusal["env"]["COMPARE_WITH_OCC"] == "${{ inputs.compare-with-occ }}"
    assert 'case "$COMPARE_WITH_OCC" in' in refusal["run"]
    assert "true|false) ;;" in refusal["run"]
    assert "::error::compare-with-occ must be exactly true or false" in refusal["run"]
    assert (
        "exit 1"
        in refusal["run"].split('case "$COMPARE_WITH_OCC" in')[1].split("esac")[0]
    )
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


def test_occ_difference_runs_after_refusal_with_only_the_existing_read_token() -> None:
    step = _step(DIFFERENCE_STEP)
    assert step["if"] == "${{ !cancelled() && inputs.compare-with-occ == 'true' }}"
    assert step["env"] == {
        "GH_TOKEN": "${{ github.token }}",
        "REPO": "${{ github.repository }}",
        "HEAD_SHA": "${{ github.event.pull_request.head.sha }}",
        "OCC_CONTEXT": "${{ inputs.occ-context }}",
        "WAIT_SECONDS": "${{ inputs.occ-wait-seconds }}",
        "NEGATIVE_CONTROL": "${{ contains(github.event.pull_request.labels.*.name, 'dod-negative-control') }}",
    }
    assert _job()["permissions"] == {"contents": "read", "pull-requests": "read"}
    script = step["run"]
    assert "set -euo pipefail" in script
    assert '[ -z "${DOD_VERIFY_PY:-}" ]' in script
    assert (
        "the pinned verifier was not installed; the difference was not computed"
        in script
    )
    assert '[ ! -f "$RUNNER_TEMP/dod/tickets.txt" ]' in script
    assert '[[ ! "$WAIT_SECONDS" =~ ^[0-9]+$ ]]' in script
    assert script.index('[[ ! "$WAIT_SECONDS"') < script.index("deadline=")
    assert script[: script.index("occ_file=")].count("exit 1") == 3


def test_occ_difference_polls_the_same_head_and_retries_cancelled_runs() -> None:
    script = _step(DIFFERENCE_STEP)["run"]
    assert 'occ_file="$RUNNER_TEMP/dod/occ-check-run.json"' in script
    assert script.index('rm -f "$occ_file"') < script.index("gh api")
    assert "deadline=$((SECONDS + 10#$WAIT_SECONDS))" in script
    assert 'while [ "$SECONDS" -lt "$deadline" ]; do' in script
    assert 'gh api -X GET "repos/$REPO/commits/$HEAD_SHA/check-runs"' in script
    assert '-f check_name="$OCC_CONTEXT" -f filter=latest -f per_page=1' in script
    assert '--jq \'.check_runs[0] // empty\' 2>/dev/null)" || check_run=""' in script
    assert '.status == "completed" and .conclusion != "cancelled"' in script
    assert "jq -r '.id'" in script
    assert (
        'gh api "repos/$REPO/check-runs/$check_id/annotations?per_page=100"' in script
    )
    assert "2>/dev/null)\" || annotations='[]'" in script
    assert (
        'jq -n --argjson check_run "$check_run" --argjson annotations "$annotations"'
        in script
    )
    assert "conclusion: $check_run.conclusion" in script
    assert 'html_url: ($check_run.html_url // "")' in script
    assert "annotations: [$annotations[] | {message: .message}]" in script
    assert '> "$occ_file"\n    break' in script
    assert "sleep_seconds=30" in script
    assert 'sleep "$sleep_seconds"' in script
    assert "remaining=$((deadline - SECONDS))" in script
    assert '[ "$remaining" -lt "$sleep_seconds" ]' in script
    assert '[ ! -f "$occ_file" ]' in script
    assert "::notice::OCC's verdict was not available within $WAIT_SECONDS" in script
    assert "not_compared" in script


def test_occ_difference_delegates_classification_to_the_pinned_node() -> None:
    script = _step(DIFFERENCE_STEP)["run"]
    assert (
        '"$DOD_VERIFY_PY" -m omnimarket.nodes.node_dod_verify occ-difference' in script
    )
    assert '--dod-dir "$RUNNER_TEMP/dod"' in script
    assert '--tickets-file "$RUNNER_TEMP/dod/tickets.txt"' in script
    assert '--occ-check-run "$occ_file"' in script
    assert (
        'if [ "$NEGATIVE_CONTROL" = true ]; then\n  difference_args+=(--negative-control)\nfi'
        in script
    )
    assert (
        '"${difference_args[@]}" | tee "$RUNNER_TEMP/dod/occ-difference.json"' in script
    )
    assert script.rstrip().endswith('| tee "$RUNNER_TEMP/dod/occ-difference.json"')


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
    assert '[ -f "$RUNNER_TEMP/dod/occ-difference.json" ]' in script
    assert (
        "jq -r '\"OCC difference: \\(.outcome) \\(.reason_code) — \\(.message)\"' "
        '"$RUNNER_TEMP/dod/occ-difference.json" || true'
    ) in script
    assert '"$GITHUB_STEP_SUMMARY" || true' in script
    assert script.rstrip().endswith("exit 0")
