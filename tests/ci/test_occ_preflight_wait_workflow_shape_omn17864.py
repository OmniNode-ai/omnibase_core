# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Workflow-shape pins for the occ-preflight bounded wait (OMN-17864).

These are the falsifiers: a future edit that lowers ``timeout-minutes`` below
the eligibility deadline, drops either new input, or reverts the live-body
read back to the event payload must turn this module red.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "occ-preflight.yml"


def _workflow() -> dict[Any, Any]:
    # PyYAML (YAML 1.1) parses the bare `on:` top-level key as the boolean
    # True, not the string "on" -- the return type reflects that the parsed
    # mapping can carry a non-str key, which `_workflow_call_inputs` below
    # relies on directly.
    data = yaml.safe_load(WORKFLOW_PATH.read_text())
    assert isinstance(data, dict)
    return data


def _workflow_call_inputs() -> dict[str, Any]:
    # PyYAML (YAML 1.1) parses the bare `on:` key as the boolean True, not the
    # string "on" -- a well-known GitHub Actions / PyYAML interaction.
    workflow = _workflow()
    on_block = workflow.get(True, workflow.get("on"))
    assert isinstance(on_block, dict), (
        f"no 'on:' block found; top-level keys: {sorted(map(str, workflow))}"
    )
    inputs = on_block["workflow_call"]["inputs"]
    assert isinstance(inputs, dict)
    return inputs


def _eligibility_job() -> dict[str, Any]:
    job = _workflow()["jobs"]["eligibility"]
    assert isinstance(job, dict)
    return job


def _resolve_evidence_source_step() -> dict[str, Any]:
    for step in _eligibility_job()["steps"]:
        if step.get("id") == "resolve_evidence_source":
            assert isinstance(step, dict)
            return step
    raise AssertionError(
        "occ-preflight.yml eligibility job has no 'resolve_evidence_source' step"
    )


def test_deadline_input_exists_with_the_omn15214_default() -> None:
    inputs = _workflow_call_inputs()
    assert "eligibility-deadline-seconds" in inputs, (
        "occ-preflight.yml must declare an 'eligibility-deadline-seconds' "
        f"workflow_call input; got {sorted(inputs)}"
    )
    deadline_input = inputs["eligibility-deadline-seconds"]
    assert deadline_input.get("type") == "number"
    assert int(deadline_input.get("default")) == 1500


def test_poll_interval_input_exists_with_the_omn15214_default() -> None:
    inputs = _workflow_call_inputs()
    assert "eligibility-poll-interval-seconds" in inputs, (
        "occ-preflight.yml must declare an 'eligibility-poll-interval-seconds' "
        f"workflow_call input; got {sorted(inputs)}"
    )
    interval_input = inputs["eligibility-poll-interval-seconds"]
    assert interval_input.get("type") == "number"
    assert int(interval_input.get("default")) == 30


def test_job_timeout_strictly_exceeds_the_deadline_in_seconds() -> None:
    """A future edit that lowers timeout-minutes below the deadline must be
    caught here -- a job killed mid-wait is stamped 'cancelled', which both
    CI Summary and GitHub's own required-check semantics fail closed on
    (the exact OMN-16322 failure shape), silently reintroducing the defect
    this module exists to fix."""
    inputs = _workflow_call_inputs()
    deadline_seconds = int(inputs["eligibility-deadline-seconds"]["default"])
    timeout_minutes = int(_eligibility_job()["timeout-minutes"])
    assert timeout_minutes * 60 > deadline_seconds, (
        f"timeout-minutes ({timeout_minutes}m = {timeout_minutes * 60}s) must "
        f"strictly exceed the eligibility deadline ({deadline_seconds}s), or the "
        "wait is killed mid-flight and the job is stamped 'cancelled'"
    )
    assert timeout_minutes == 30


def test_resolve_evidence_source_reads_the_live_pr_body_via_api() -> None:
    """occ-autobind PATCHes Evidence-Source onto the body AFTER the
    triggering event fires. Reading the event payload instead of the live API
    reintroduces the exact race this module closes."""
    run_block = str(_resolve_evidence_source_step().get("run", ""))
    assert "occ_preflight_wait" in run_block, (
        "the resolve_evidence_source step must drive scripts/ci/occ_preflight_wait.py"
    )
    assert "github.event.pull_request.body" not in run_block, (
        "resolve_evidence_source must never read the triggering event's body -- "
        "the live PR body (fetched inside occ_preflight_wait.py's GhCli) is the "
        "only surface that reflects a stamp PATCHed on after the event fired"
    )


def test_resolve_evidence_source_step_passes_the_workflow_call_inputs_through() -> None:
    """The step must actually thread the two new inputs to the driver, or a
    caller's override of either default is silently ignored."""
    step = _resolve_evidence_source_step()
    run_block = str(step.get("run", ""))
    env_block = step.get("env", {})
    assert isinstance(env_block, dict)
    rendered = run_block + " " + " ".join(f"{k}={v}" for k, v in env_block.items())
    assert "inputs.eligibility-deadline-seconds" in rendered, (
        "resolve_evidence_source must pass inputs.eligibility-deadline-seconds "
        "through to the driver (e.g. via a DEADLINE_SECONDS env binding)"
    )
    assert "inputs.eligibility-poll-interval-seconds" in rendered, (
        "resolve_evidence_source must pass inputs.eligibility-poll-interval-seconds "
        "through to the driver (e.g. via a POLL_INTERVAL_SECONDS env binding)"
    )


def _step_index(step_id: str) -> int:
    steps = _eligibility_job()["steps"]
    for idx, step in enumerate(steps):
        if step.get("id") == step_id:
            return idx
    raise AssertionError(f"eligibility job has no step with id {step_id!r}")


def test_resolve_evidence_source_invokes_occ_preflight_wait_by_absolute_path() -> None:
    """OMN-17864 follow-up: for every EXTERNAL caller of this reusable
    workflow, GITHUB_WORKSPACE is the CALLER's checkout, which has no
    scripts/ci/occ_preflight_wait.py. A workspace-relative invocation
    (``python3 scripts/ci/occ_preflight_wait.py``) resolves only by accident,
    for omnibase_core's own 41 local ``uses: ./...`` callers -- every other
    repo hard-fails with 'No such file or directory' (live evidence:
    omniclaude#2201, job 104912265991, exit code 2 in 8s). The invocation
    must resolve the module from an absolute path, never bare
    workspace-relative text."""
    run_block = str(_resolve_evidence_source_step().get("run", ""))
    assert "python3 scripts/ci/occ_preflight_wait.py" not in run_block, (
        "resolve_evidence_source must not invoke occ_preflight_wait.py by a "
        "bare workspace-relative path -- that only resolves inside "
        "omnibase_core's own checkout and hard-fails for every external "
        "caller of this reusable workflow"
    )
    assert (
        "RUNNER_TEMP" in run_block
        or "runner.temp" in run_block
        or "GITHUB_WORKSPACE" in run_block
    ), (
        "resolve_evidence_source must resolve occ_preflight_wait.py from an "
        "absolute path (rooted at RUNNER_TEMP or GITHUB_WORKSPACE), not a "
        "bare relative one"
    )


def test_omnibase_core_checkout_precedes_the_resolve_evidence_source_step() -> None:
    """A checkout of OmniNode-ai/omnibase_core (at the core-ref input) must
    happen BEFORE the step that invokes occ_preflight_wait.py, so an
    external caller's workspace has a copy of the module to run. The later
    'Check out omnibase_core (for eligibility validator)' step exists only
    to install the validator package and runs AFTER resolve_evidence_source
    -- it does not satisfy this requirement."""
    steps = _eligibility_job()["steps"]
    resolve_idx = _step_index("resolve_evidence_source")

    def _is_omnibase_core_checkout(step: dict[str, Any]) -> bool:
        uses = str(step.get("uses", ""))
        if not uses.startswith("actions/checkout@"):
            return False
        with_block = step.get("with", {})
        if not isinstance(with_block, dict):
            return False
        return with_block.get("repository") == "OmniNode-ai/omnibase_core"

    preceding_core_checkouts = [
        step for step in steps[:resolve_idx] if _is_omnibase_core_checkout(step)
    ]
    assert preceding_core_checkouts, (
        "no 'actions/checkout' step targeting OmniNode-ai/omnibase_core precedes "
        "'resolve_evidence_source' -- an external caller's workspace has no "
        "copy of scripts/ci/occ_preflight_wait.py to run without one"
    )
    for step in preceding_core_checkouts:
        with_block = step["with"]
        assert with_block.get("ref") == "${{ inputs.core-ref }}", (
            "the early omnibase_core checkout must honor the core-ref input, "
            f"got: {with_block.get('ref')!r}"
        )


def test_occ_preflight_wait_checkout_path_is_workspace_relative() -> None:
    """``actions/checkout`` refuses a ``path`` that resolves outside
    ``GITHUB_WORKSPACE`` ("Repository path ... is not under ..."), so an
    absolute root such as ``${{ runner.temp }}`` makes the step fail on the
    first EXTERNAL caller that reaches it -- the only callers it exists to
    serve, since omnibase_core's own local callers skip it on the
    ``hashFiles`` guard and therefore never exercise the path at all. The
    proven cross-repo checkouts further down this job
    (``.occ-preflight-deps/omnibase_compat`` and
    ``.occ-preflight-deps/omnibase_core``) are workspace-relative for the
    same reason; this one must be too."""
    steps = _eligibility_job()["steps"]
    resolve_idx = _step_index("resolve_evidence_source")
    core_checkouts = [
        step
        for step in steps[:resolve_idx]
        if str(step.get("uses", "")).startswith("actions/checkout@")
        and isinstance(step.get("with"), dict)
        and step["with"].get("repository") == "OmniNode-ai/omnibase_core"
    ]
    assert core_checkouts, "expected the pre-resolve omnibase_core checkout to exist"
    for step in core_checkouts:
        path_value = str(step["with"].get("path", ""))
        assert path_value, "the pre-resolve omnibase_core checkout must declare a path"
        assert not path_value.startswith("/"), (
            f"checkout path {path_value!r} is absolute; actions/checkout rejects "
            "any path outside GITHUB_WORKSPACE"
        )
        assert "runner.temp" not in path_value and "RUNNER_TEMP" not in path_value, (
            f"checkout path {path_value!r} resolves outside GITHUB_WORKSPACE; "
            "actions/checkout rejects it"
        )
